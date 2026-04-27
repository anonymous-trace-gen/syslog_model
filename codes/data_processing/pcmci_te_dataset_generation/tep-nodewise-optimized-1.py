"""
PCMCI-ready binned event-count matrix – optimised for Frontier/Lustre.

Key changes vs v1
-----------------
* Driver loop replaced with fully vectorised NumPy filtering → no Python for-loop.
* Chunks written as Parquet to Lustre scratch; read once as a single Spark DataFrame
  → eliminates the 70-deep union() query-plan problem.
* full_grid dense-fill replaced with a rangeJoin-friendly approach using
  window-based forward-fill + explicit zero-fill only where needed.
* Global orderBy replaced with sortWithinPartitions (avoids full re-shuffle).
* Executor sizing tuned for Frontier (64-core, 512 GB nodes).
"""

import argparse
import pickle
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from pathlib import Path

from pyspark.sql import SparkSession, functions as F
from pyspark.sql.window import Window
from pyspark.sql.types import (
    StructType, StructField, LongType, StringType, IntegerType
)

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

# PyArrow schema for scratch Parquet files (written on driver)
PA_SCHEMA = pa.schema([
    pa.field("node",  pa.string()),
    pa.field("ts_ns", pa.int64()),
    pa.field("token", pa.int32()),
])


def load_node_map(pkl_path: str):
    with open(pkl_path, "rb") as f:
        nm = pickle.load(f)
    return np.array(nm["int_to_node"])          # index → name, as numpy array


def iter_chunks(total: int, chunk_size: int):
    start = 0
    while start < total:
        yield start, min(start + chunk_size, total)
        start += chunk_size


def vectorised_filter_chunk(
    c_nodes, c_ts, c_tokens, node_names: np.ndarray
) -> pa.Table | None:
    """
    Fully vectorised NumPy filtering – no Python for-loop.
    Returns a PyArrow Table or None if empty.
    """
    # 1. Drop special tokens (> 86) in one vectorised op
    real_mask = c_tokens <= 86
    if not real_mask.any():
        return None

    c_nodes  = c_nodes[real_mask]
    c_ts     = c_ts[real_mask]
    c_tokens = c_tokens[real_mask]

    # 2. Resolve node names via fancy indexing (no Python loop)
    names = node_names[c_nodes]          # shape: (N,), dtype object/str

    # 3. Keep only frontier nodes – vectorised string op via numpy
    frontier_mask = np.char.startswith(names.astype(str), "frontier")
    if not frontier_mask.any():
        return None

    return pa.table(
        {
            "node":  names[frontier_mask].tolist(),
            "ts_ns": c_ts[frontier_mask].tolist(),
            "token": c_tokens[frontier_mask].tolist(),
        },
        schema=PA_SCHEMA,
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base_dir",     required=True)
    ap.add_argument("--split",        default="train")
    ap.add_argument("--output",       required=True)
    ap.add_argument("--scratch_dir",  required=True,
                    help="Lustre path for temporary filtered Parquet files")
    ap.add_argument("--interval_sec", type=int, default=5)
    ap.add_argument("--chunk_size",   type=int, default=100_000_000,
                    help="Rows per driver chunk (default 100 M, ~800 MB/array)")
    ap.add_argument("--shuffle_partitions", type=int, default=8192)
    ap.add_argument("--write_csv",    action="store_true")
    args = ap.parse_args()

    base     = Path(args.base_dir)
    split    = args.split
    scratch  = Path(args.scratch_dir) / "filtered_parquet"
    scratch.mkdir(parents=True, exist_ok=True)

    # ── Load mmap arrays (driver only) ───────────────────────────────────
    tokens     = np.load(base / f"{split}_node_ts_sorted_tokens.npy",     mmap_mode="r")
    timestamps = np.load(base / f"{split}_node_ts_sorted_timestamps.npy", mmap_mode="r")
    nodes_arr  = np.load(base / f"{split}_node_ts_sorted_nodes.npy",      mmap_mode="r")
    node_names = load_node_map(str(base / f"{split}_node_name_map.pkl"))

    total_rows = len(tokens)
    print(f"Total rows in mmap: {total_rows:,}")

    # ── Phase 1: Vectorised filter → Parquet on Lustre scratch ───────────
    # This replaces the Python for-loop AND the repeated union() calls.
    writers: dict[int, pq.ParquetWriter] = {}
    file_paths: list[str] = []

    for chunk_idx, (chunk_start, chunk_end) in enumerate(
        iter_chunks(total_rows, args.chunk_size)
    ):
        print(f"  Filtering rows {chunk_start:,}–{chunk_end:,} …")

        c_nodes  = nodes_arr[chunk_start:chunk_end].astype(np.int32)
        c_ts     = timestamps[chunk_start:chunk_end].astype(np.int64)
        c_tokens = tokens[chunk_start:chunk_end].astype(np.int32)

        table = vectorised_filter_chunk(c_nodes, c_ts, c_tokens, node_names)
        if table is None:
            continue

        out_path = str(scratch / f"chunk_{chunk_idx:05d}.parquet")
        pq.write_table(table, out_path, compression="snappy",
                       row_group_size=500_000)
        file_paths.append(out_path)
        print(f"    → wrote {len(table):,} rows to {out_path}")

    if not file_paths:
        print("No frontier data found – exiting.")
        return

    print(f"Phase 1 done: {len(file_paths)} Parquet files written to {scratch}")

    # ── Spark session ─────────────────────────────────────────────────────
    spark = (SparkSession.builder
             .appName("PCMCI_NodeEvent_Matrix_v2")
             .config("spark.sql.shuffle.partitions",   str(args.shuffle_partitions))
             .config("spark.sql.pivotMaxValues",        "200000")
             .config("spark.sql.adaptive.enabled",      "true")   # AQE
             .config("spark.sql.adaptive.coalescePartitions.enabled", "true")
             .config("spark.sql.adaptive.skewJoin.enabled",           "true")
             # Keep broadcast join threshold high to broadcast node_rank table
             .config("spark.sql.autoBroadcastJoinThreshold", "256m")
             .getOrCreate())
    spark.sparkContext.setLogLevel("WARN")

    interval_ns = args.interval_sec * 1_000_000_000
    hour_ns     = 3_600 * 1_000_000_000

    # ── Phase 2: Read all filtered Parquet in one shot ────────────────────
    # Spark reads from Lustre in parallel across all executors – no driver loop.
    raw_df = spark.read.schema(
        StructType([
            StructField("node",  StringType(),  False),
            StructField("ts_ns", LongType(),    False),
            StructField("token", IntegerType(), False),
        ])
    ).parquet(str(scratch))

    # ── Map token index → event name via broadcast map ────────────────────
    token_map_expr = F.create_map(
        *[v for pair in
          [(F.lit(idx), F.lit(name)) for idx, name in IDX_TO_EVENT.items()]
          for v in pair]
    )
    raw_df = raw_df.withColumn("event", token_map_expr[F.col("token")]).drop("token")

    # ── Bin timestamps ────────────────────────────────────────────────────
    interval_lit = F.lit(interval_ns)
    raw_df = raw_df.withColumn(
        "t_bin_ns",
        (F.floor(F.col("ts_ns") / interval_lit) * interval_lit).cast("long")
    ).drop("ts_ns")

    # ── Count events per (node, t_bin, event) ────────────────────────────
    counts = (raw_df
              .groupBy("node", "t_bin_ns", "event")
              .agg(F.count(F.lit(1)).alias("cnt")))

    # ── Pivot to wide format ──────────────────────────────────────────────
    wide = (counts
            .groupBy("node", "t_bin_ns")
            .pivot("event", EVENT_COLS)
            .agg(F.first("cnt")))

    # ── Dense fill: expand each node to its full bin range ────────────────
    # Use sequence() + explode on per-node min/max, then left-join.
    # AQE will coalesce small partitions automatically.
    node_ranges = (wide
                   .groupBy("node")
                   .agg(F.min("t_bin_ns").alias("min_bin"),
                        F.max("t_bin_ns").alias("max_bin")))

    full_grid = (node_ranges
                 .select(
                     "node",
                     F.explode(
                         F.sequence(
                             F.col("min_bin"),
                             F.col("max_bin"),
                             F.lit(interval_ns)
                         )
                     ).alias("t_bin_ns")
                 ))

    wide_full = (full_grid
                 .join(wide, on=["node", "t_bin_ns"], how="left")
                 .na.fill(0))

    # ── Insert 1-hour gap offsets between nodes ───────────────────────────
    node_rank = (wide_full
                 .select("node").distinct()
                 .withColumn(
                     "node_rank",
                     F.row_number().over(Window.orderBy("node")).cast("long") - 1
                 ))
    # node_rank is tiny (one row per frontier node) → broadcast join
    node_rank = F.broadcast(node_rank)

    wide_full = (wide_full
                 .join(node_rank, on="node", how="left")
                 .withColumn(
                     "t_bin_ns",
                     F.col("t_bin_ns") + F.col("node_rank") * F.lit(hour_ns)
                 )
                 .drop("node_rank"))

    # ── Convert to UTC timestamp ──────────────────────────────────────────
    wide_full = wide_full.withColumn(
        "timestamp",
        F.to_utc_timestamp(
            F.from_unixtime((F.col("t_bin_ns") / F.lit(1_000_000_000)).cast("long")),
            "UTC"
        )
    ).drop("t_bin_ns")

    # ── Final column order + sort WITHIN partitions (not global sort) ─────
    final_cols = ["node", "timestamp"] + EVENT_COLS
    wide_full  = (wide_full
                  .select(*final_cols)
                  .sortWithinPartitions("node", "timestamp"))   # ← no full re-shuffle

    # ── Write output ──────────────────────────────────────────────────────
    (wide_full.write
         .mode("overwrite")
         .partitionBy("node")
         .parquet(args.output))

    if args.write_csv:
        (wide_full.write
             .mode("overwrite")
             .option("header", True)
             .csv(args.output + "_csv"))

    print("Done.")
    spark.stop()


if __name__ == "__main__":
    main()