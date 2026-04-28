"""
PCMCI-ready binned event-count matrix  parallelised node-complete Phase 2.

"""

import argparse
import json
import time
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from pyspark.sql import SparkSession, functions as F
from pyspark.sql.types import StructType, StructField, StringType, LongType

# ── Label mapping ────────────────────────────────────────────────────────
LABEL_MAPPING = {
    "NET_CXI_RAW_DATA":  0,  "FS_DISK_FULL":       1,  "INFO_NOISE":         2,
    "NET_CXI_TIMEOUT":   3,  "SVC_RSYSLOG_ERR":    4,  "NET_CXI_LINK":       5,
    "FS_DVS_WARN":       6,  "NET_CXI_WARN":       7,  "NET_TCP_FAIL":       8,
    "HW_PCIE_ERR":       9,  "HW_MCE_GENERIC":    10,  "NET_CXI_INT_ERR":   11,
    "HW_MCE_FATAL":     12,  "NET_CXI_HW_ECC":    13,  "APP_INFRA_FAIL":    14,
    "NET_CXI_SVC":      15,  "GPU_MEM_FAULT":     16,  "HW_MCE_CORRECTED":  17,
    "HW_EDAC_ERR":      18,  "FS_CLUSTER_EVICT":  19,  "FS_LUSTRE_SLOW":    20,
    "SVC_SYSTEMD_START":21,  "SVC_CONFIG_ERR":    22,  "GPU_SOFT_LOCK":     23,
    "HW_FABRIC_RTR":    24,  "NET_CONFIG_ERR":    25,  "HW_MEM_DIMM":       26,
    "SEC_AUTH_FAIL":    27,  "GPU_RAS_FAIL":       28,  "HW_IOMMU_ERR":     29,
    "FS_LUSTRE_OST_ERR":30,  "APP_FILE_MISSING":  31,  "SYS_KERNEL_CTX":    32,
    "FS_LUSTRE_ERR":    33,  "GPU_DRIVER_ERR":     34,  "FS_XFS_ERR":        35,
    "GPU_FIRMWARE":     36,  "HW_BMC_WARN":       37,  "APP_JOB_CANCEL":    38,
    "APP_CFG_ERR":      39,  "HW_ACPI_WARN":      40,  "APP_JOB_LATENCY":   41,
    "NET_CXI_FIRMWARE": 42,  "FS_IO_ERR":         43,  "NET_CXI_PHY_ERR":   44,
    "SVC_SYSTEMD_SPEC": 45,  "SYS_OOM_KILL":      46,  "APP_JOB_CGROUP":    47,
    "HW_IF_GPU_LINK":   48,  "FS_GPFS_ERR":       49,  "GPU_HARD_FAULT":    50,
    "HW_USB_FAIL":      51,  "HW_MCE_CPU":        52,  "SYS_WATCHDOG":      53,
    "NET_CXI_MGMT_ERR": 54,  "FS_LUSTRE_MDS_ERR": 55,  "SYS_CONFIG_ERR":   56,
    "SYS_RCU_STALL":    57,  "APP_JOB_ERR":       58,  "NET_RPC_ERR":       59,
    "NET_LNET_ERR":     60,  "GPU_TIMEOUT":       61,  "SYS_SEGFAULT":      62,
    "SVC_SYSTEMD_TIME": 63,  "HW_THERMAL_CRIT":   64,  "CTX_LUSTRE":        65,
    "HW_MCE_DUMP":      66,  "HW_MEM_CORRUPT":    67,  "STO_NVME_STALL":    68,
    "SVC_SYSTEMD_EXIT": 69,  "APP_GITLAB_FAIL":   70,  "SVC_SYSTEMD_KILL":  71,
    "SYS_KERNEL_PANIC": 72,  "CTX_AMDGPU":        73,  "SYS_COREDUMP":      74,
    "HW_CPU_CORE":      75,  "SYS_PROCESS_LIM":   76,  "SYS_X11_NOISE":     77,
    "SYS_CLOCK_SKEW":   78,  "CTX_SCHEDULER":     79,  "NET_LNET_WARN":     80,
    "HW_PCIE_HUB":      81,  "SVC_SYSTEMD_PAM":   82,  "CTX_MEMORY":        83,
    "CTX_SLINGSHOT":    84,  "HW_FABRIC_INT":      85,  "HW_MCE_UNK":        86,
    "<PAD>": 87, "<UNK>": 88, "<MASK>": 89,
}
REAL_EVENTS  = {k: v for k, v in LABEL_MAPPING.items() if v <= 86}
IDX_TO_EVENT = {v: k for k, v in REAL_EVENTS.items()}
EVENT_COLS   = [IDX_TO_EVENT[i] for i in range(87)]
N_EVENTS     = 87

TS_TYPE    = pa.timestamp("s", tz="UTC")   # seconds precision – no overflow
OUT_SCHEMA = pa.schema(
    [pa.field("node",         pa.string()),
     pa.field("timestamp",    TS_TYPE),
     pa.field("is_separator", pa.bool_())]
    + [pa.field(c, pa.float32()) for c in EVENT_COLS]
)


def log(tag, msg, t0=None):
    now = time.time()
    e   = f"  (+{now - t0:.1f}s)" if t0 else ""
    print(f"[{tag}] {msg}{e}", flush=True)
    return now



# Build manifest

def build_manifest(spark, all_files, manifest_path, interval_sec, job_start):
    """
    interval_sec : bin width in seconds (e.g. 5)
    All synthetic timeline fields in the manifest are in SECONDS.
    """
    log("PASS1", "Scanning node + ts_ns columns …", job_start)

    schema2 = StructType([
        StructField("node",  StringType(), False),
        StructField("ts_ns", LongType(),   False),
    ])
    df = (spark.read.schema(schema2)
          .parquet(*[str(f) for f in all_files])
          .withColumn("src_file", F.input_file_name()))

    rows = (df.groupBy("node")
              .agg(F.min("ts_ns").alias("min_ts_ns"),
                   F.max("ts_ns").alias("max_ts_ns"),
                   F.collect_set("src_file").alias("files"))
              .orderBy("node")
              .collect())

    log("PASS1", f"Distinct nodes: {len(rows):,}", job_start)

    manifest   = {}
    # cursor_s: current position on the synthetic time axis, in SECONDS
    cursor_s   = 0
    interval_ns = interval_sec * 1_000_000_000

    for rank, row in enumerate(rows):
        node_name     = row["node"]

        # Real binning still done in ns (raw timestamps are ns)
        min_bin_real_ns = (int(row["min_ts_ns"]) // interval_ns) * interval_ns
        max_bin_real_ns = (int(row["max_ts_ns"]) // interval_ns) * interval_ns
        n_bins          = int((max_bin_real_ns - min_bin_real_ns)
                              // interval_ns) + 1

        # Synthetic positions in SECONDS
        synthetic_start_s = cursor_s
        separator_s       = cursor_s + n_bins * interval_sec
        cursor_s          = separator_s + interval_sec   # next node starts here

        manifest[node_name] = {
            "rank":               rank,
            # Raw real ns values – used only for binning inside process_node
            "min_ts_ns":          int(row["min_ts_ns"]),
            "max_ts_ns":          int(row["max_ts_ns"]),
            "min_bin_real_ns":    min_bin_real_ns,
            "n_bins":             n_bins,
            # Synthetic timeline in SECONDS – safe from int64 overflow
            "synthetic_start_s":  synthetic_start_s,
            "separator_s":        separator_s,
            "files":              sorted(Path(f).name for f in row["files"]),
        }

        if rank < 5 or rank % 1000 == 0:
            from datetime import datetime, timezone as tz
            ts = datetime.fromtimestamp(synthetic_start_s, tz=tz.utc)
            te = datetime.fromtimestamp(separator_s,       tz=tz.utc)
            log("PASS1",
                f"  rank={rank:5d}  {node_name}  n_bins={n_bins:>8,}  "
                f"data_start={ts}  separator={te}",
                job_start)

    total_rows = sum(v["n_bins"] + 1 for v in manifest.values())
    log("PASS1",
        f"Manifest built.  nodes={len(manifest):,}  "
        f"total_rows={total_rows:,}  (data + 1 NaN separator each)",
        job_start)

    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    log("PASS1", f"Saved → {manifest_path}", job_start)
    return manifest


# Worker

def process_node(task: dict) -> dict:
    import time, numpy as np, pyarrow as pa, pyarrow.parquet as pq
    from pathlib import Path

    LABEL_MAP_L = {
        "NET_CXI_RAW_DATA":  0,  "FS_DISK_FULL":       1,  "INFO_NOISE":         2,
        "NET_CXI_TIMEOUT":   3,  "SVC_RSYSLOG_ERR":    4,  "NET_CXI_LINK":       5,
        "FS_DVS_WARN":       6,  "NET_CXI_WARN":       7,  "NET_TCP_FAIL":       8,
        "HW_PCIE_ERR":       9,  "HW_MCE_GENERIC":    10,  "NET_CXI_INT_ERR":   11,
        "HW_MCE_FATAL":     12,  "NET_CXI_HW_ECC":    13,  "APP_INFRA_FAIL":    14,
        "NET_CXI_SVC":      15,  "GPU_MEM_FAULT":     16,  "HW_MCE_CORRECTED":  17,
        "HW_EDAC_ERR":      18,  "FS_CLUSTER_EVICT":  19,  "FS_LUSTRE_SLOW":    20,
        "SVC_SYSTEMD_START":21,  "SVC_CONFIG_ERR":    22,  "GPU_SOFT_LOCK":     23,
        "HW_FABRIC_RTR":    24,  "NET_CONFIG_ERR":    25,  "HW_MEM_DIMM":       26,
        "SEC_AUTH_FAIL":    27,  "GPU_RAS_FAIL":       28,  "HW_IOMMU_ERR":     29,
        "FS_LUSTRE_OST_ERR":30,  "APP_FILE_MISSING":  31,  "SYS_KERNEL_CTX":    32,
        "FS_LUSTRE_ERR":    33,  "GPU_DRIVER_ERR":     34,  "FS_XFS_ERR":        35,
        "GPU_FIRMWARE":     36,  "HW_BMC_WARN":       37,  "APP_JOB_CANCEL":    38,
        "APP_CFG_ERR":      39,  "HW_ACPI_WARN":      40,  "APP_JOB_LATENCY":   41,
        "NET_CXI_FIRMWARE": 42,  "FS_IO_ERR":         43,  "NET_CXI_PHY_ERR":   44,
        "SVC_SYSTEMD_SPEC": 45,  "SYS_OOM_KILL":      46,  "APP_JOB_CGROUP":    47,
        "HW_IF_GPU_LINK":   48,  "FS_GPFS_ERR":       49,  "GPU_HARD_FAULT":    50,
        "HW_USB_FAIL":      51,  "HW_MCE_CPU":        52,  "SYS_WATCHDOG":      53,
        "NET_CXI_MGMT_ERR": 54,  "FS_LUSTRE_MDS_ERR": 55,  "SYS_CONFIG_ERR":   56,
        "SYS_RCU_STALL":    57,  "APP_JOB_ERR":       58,  "NET_RPC_ERR":       59,
        "NET_LNET_ERR":     60,  "GPU_TIMEOUT":       61,  "SYS_SEGFAULT":      62,
        "SVC_SYSTEMD_TIME": 63,  "HW_THERMAL_CRIT":   64,  "CTX_LUSTRE":        65,
        "HW_MCE_DUMP":      66,  "HW_MEM_CORRUPT":    67,  "STO_NVME_STALL":    68,
        "SVC_SYSTEMD_EXIT": 69,  "APP_GITLAB_FAIL":   70,  "SVC_SYSTEMD_KILL":  71,
        "SYS_KERNEL_PANIC": 72,  "CTX_AMDGPU":        73,  "SYS_COREDUMP":      74,
        "HW_CPU_CORE":      75,  "SYS_PROCESS_LIM":   76,  "SYS_X11_NOISE":     77,
        "SYS_CLOCK_SKEW":   78,  "CTX_SCHEDULER":     79,  "NET_LNET_WARN":     80,
        "HW_PCIE_HUB":      81,  "SVC_SYSTEMD_PAM":   82,  "CTX_MEMORY":        83,
        "CTX_SLINGSHOT":    84,  "HW_FABRIC_INT":      85,  "HW_MCE_UNK":        86,
    }
    N_EV       = 87
    EVENT_COLS = [{v: k for k, v in LABEL_MAP_L.items()}[i] for i in range(N_EV)]
    TS_TYPE    = pa.timestamp("s", tz="UTC")
    OUT_SCHEMA = pa.schema(
        [pa.field("node",         pa.string()),
         pa.field("timestamp",    TS_TYPE),
         pa.field("is_separator", pa.bool_())]
        + [pa.field(c, pa.float32()) for c in EVENT_COLS]
    )

    t0              = time.time()
    node_name       = task["node_name"]
    min_bin_real_ns = task["min_bin_real_ns"]   # ns, for raw binning only
    n_bins          = task["n_bins"]
    interval_sec    = task["interval_sec"]       # 5
    interval_ns     = interval_sec * 1_000_000_000
    # Synthetic positions in SECONDS – no overflow risk
    synth_start_s   = task["synthetic_start_s"]
    sep_s           = task["separator_s"]
    out_dir         = Path(task["output_dir"])

    try:
        # Read raw rows for this node
        node_filter = [("node", "=", node_name)]
        chunks_ts, chunks_tok = [], []
        for fp in task["file_paths"]:
            tbl  = pq.read_table(fp,
                                 columns=["node", "ts_ns", "token"],
                                 filters=node_filter)
            keep = pa.array([n == node_name for n in tbl["node"].to_pylist()])
            tbl  = tbl.filter(keep)
            if len(tbl):
                chunks_ts.append(tbl["ts_ns"].to_numpy(zero_copy_only=False)
                                 .astype(np.int64))
                chunks_tok.append(tbl["token"].to_numpy(zero_copy_only=False)
                                  .astype(np.int32))

        if not chunks_ts:
            return {"node": node_name, "status": "empty",
                    "rows": 0, "elapsed": time.time()-t0}

        ts_arr  = np.concatenate(chunks_ts)
        tok_arr = np.concatenate(chunks_tok)

        bin_idx = np.clip(
            ((ts_arr // interval_ns) * interval_ns - min_bin_real_ns)
            // interval_ns,
            0, n_bins - 1
        ).astype(np.int64)

        # Count events
        counts = np.zeros((n_bins, N_EV), dtype=np.float32)
        valid  = (tok_arr >= 0) & (tok_arr < N_EV)
        np.add.at(counts, (bin_idx[valid], tok_arr[valid]), 1.0)

        data_ts_s = (np.arange(n_bins, dtype=np.int64) * interval_sec
                     + synth_start_s)
        sep_ts_s  = np.array([sep_s], dtype=np.int64)

        # ── Assemble full output (data rows + NaN separator row) ──────────
        all_ts_s   = np.concatenate([data_ts_s, sep_ts_s])  # (n_bins+1,)
        nan_row    = np.full((1, N_EV), np.nan, dtype=np.float32)
        all_counts = np.concatenate([counts, nan_row], axis=0)

        node_col   = pa.array([node_name]*n_bins + ["NaN_BREAK"],
                               type=pa.string())
        is_sep_col = pa.array([False]*n_bins + [True], type=pa.bool_())

        arrays = (
            [node_col,
             pa.array(all_ts_s, type=pa.int64()).cast(TS_TYPE),
             is_sep_col]
            + [pa.array(all_counts[:, i], type=pa.float32())
               for i in range(N_EV)]
        )
        table = pa.table(
            {f.name: arr for f, arr in zip(OUT_SCHEMA, arrays)},
            schema=OUT_SCHEMA,
        )

        node_dir = out_dir / f"node={node_name}"
        node_dir.mkdir(parents=True, exist_ok=True)
        pq.write_table(table, node_dir / "data.parquet",
                       compression="snappy", row_group_size=200_000)

        from datetime import datetime, timezone as tz
        t_first = datetime.fromtimestamp(int(data_ts_s[0]),  tz=tz.utc)
        t_last  = datetime.fromtimestamp(int(data_ts_s[-1]), tz=tz.utc)
        t_sep   = datetime.fromtimestamp(int(sep_ts_s[0]),   tz=tz.utc)

        return {
            "node":        node_name,
            "status":      "ok",
            "rows":        n_bins + 1,
            "data_rows":   n_bins,
            "elapsed":     time.time() - t0,
            "t_first":     str(t_first),
            "t_last":      str(t_last),
            "t_sep":       str(t_sep),
            "synth_start": int(data_ts_s[0]),
            "synth_end":   int(data_ts_s[-1]),
            "sep_ts":      int(sep_ts_s[0]),
        }

    except Exception as exc:
        import traceback
        return {"node": node_name,
                "status": f"ERROR: {exc}\n{traceback.format_exc()}",
                "rows": 0, "elapsed": time.time()-t0}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase1_parquet", required=True)
    ap.add_argument("--output",         required=True)
    ap.add_argument("--manifest_path",  default="")
    ap.add_argument("--ledger_path",    default="")
    ap.add_argument("--interval_sec",   type=int, default=5)
    ap.add_argument("--parallelism",    type=int, default=0)
    ap.add_argument("--skip_pass1",     action="store_true")
    args = ap.parse_args()

    JOB_START     = time.time()
    phase1_dir    = Path(args.phase1_parquet)
    output_dir    = Path(args.output)
    manifest_path = (Path(args.manifest_path) if args.manifest_path
                     else output_dir / "node_manifest.json")
    ledger_path   = (Path(args.ledger_path) if args.ledger_path
                     else output_dir / "progress.json")

    output_dir.mkdir(parents=True, exist_ok=True)
    all_files = sorted(phase1_dir.glob("*.parquet"))
    if not all_files:
        raise FileNotFoundError(f"No Parquet files in {phase1_dir}")
    log("INIT", f"Found {len(all_files)} Phase-1 files", JOB_START)

    spark = (SparkSession.builder
             .appName("PCMCI_NaN_Separator_v2")
             .config("spark.sql.adaptive.enabled", "true")
             .getOrCreate())
    spark.sparkContext.setLogLevel("WARN")

    sc          = spark.sparkContext
    total_cores = int(sc._jsc.sc().defaultParallelism())
    parallelism = args.parallelism if args.parallelism > 0 else total_cores * 2
    log("INIT", f"cores={total_cores}  parallelism={parallelism}", JOB_START)

    # Pass 1 
    if args.skip_pass1 and manifest_path.exists():
        log("PASS1", f"Loading manifest from {manifest_path}", JOB_START)
        with open(manifest_path) as f:
            manifest = json.load(f)
        log("PASS1", f"Loaded {len(manifest):,} nodes", JOB_START)

        # Verify no overflow: print max synthetic_start_s
        max_s = max(v["separator_s"] for v in manifest.values())
        from datetime import datetime, timezone as tz
        log("PASS1",
            f"Max synthetic timestamp = "
            f"{datetime.fromtimestamp(max_s, tz=tz.utc)}  "
            f"(int64 max seconds ≈ year 292,000,000,000 – no overflow)",
            JOB_START)
    else:
        # Rebuild manifest
        if manifest_path.exists():
            with open(manifest_path) as f:
                old = json.load(f)
            first = next(iter(old.values()))
            if "synthetic_start_ns" in first:
                log("PASS1",
                    "Old manifest uses nanoseconds – rebuilding in seconds …",
                    JOB_START)
                manifest_path.unlink()
        manifest = build_manifest(spark, all_files, manifest_path,
                                  args.interval_sec, JOB_START)

    # Pass 2
    done_nodes = set()
    if ledger_path.exists():
        with open(ledger_path) as f:
            done_nodes = set(json.load(f).get("completed_nodes", []))
        log("RESUME", f"{len(done_nodes)} nodes already done", JOB_START)

    file_path_map = {f.name: str(f) for f in all_files}
    tasks = [
        {
            "node_name":          name,
            "min_bin_real_ns":    info["min_bin_real_ns"],
            "n_bins":             info["n_bins"],
            "synthetic_start_s":  info["synthetic_start_s"],
            "separator_s":        info["separator_s"],
            "interval_sec":       args.interval_sec,
            "output_dir":         str(output_dir),
            "file_paths":         [file_path_map[fn] for fn in info["files"]
                                    if fn in file_path_map],
        }
        for name, info in manifest.items()
        if name not in done_nodes
    ]

    log("PASS2",
        f"total={len(manifest)}  done={len(done_nodes)}  todo={len(tasks)}",
        JOB_START)

    if not tasks:
        log("DONE", "All nodes already complete.", JOB_START)
        spark.stop()
        return

    results = sc.parallelize(tasks, parallelism).map(process_node).collect()

    # save ledger
    newly_done, errors = [], []
    rank_map = {n: info["rank"] for n, info in manifest.items()}
    results.sort(key=lambda r: rank_map.get(r["node"], 999999))

    prev_sep_ts = None
    for r in results:
        if r["status"] == "ok":
            newly_done.append(r["node"])
            if prev_sep_ts is not None:
                gap_s = r["synth_start"] - prev_sep_ts
                ok    = gap_s == args.interval_sec
                log("VERIFY",
                    f"  {r['node']:20s}  start={r['t_first']}  "
                    f"gap_after_sep={gap_s}s  "
                    f"{'✓' if ok else f'✗ EXPECTED {args.interval_sec}s'}",
                    JOB_START)
            else:
                log("VERIFY",
                    f"  {r['node']:20s}  start={r['t_first']}  "
                    f"sep={r['t_sep']}  (first node)",
                    JOB_START)
            prev_sep_ts = r["sep_ts"]
        else:
            errors.append(r)
            log("ERROR", f"  {r['node']}: {r['status'][:200]}", JOB_START)

    all_done = done_nodes | set(newly_done)
    tmp = ledger_path.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump({"completed_nodes": sorted(all_done),
                   "total_completed":  len(all_done),
                   "total_nodes":      len(manifest)},
                  f, indent=2)
    tmp.rename(ledger_path)

    log("DONE",
        f"done_this_run={len(newly_done)}  "
        f"total={len(all_done)}/{len(manifest)}  "
        f"errors={len(errors)}  "
        f"wall={time.time()-JOB_START:.1f}s",
        JOB_START)
    spark.stop()


if __name__ == "__main__":
    main()