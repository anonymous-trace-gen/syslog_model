"""
Event count distribution — MPI across 15 nodes, 32 workers per node.
"""
import argparse
import time
import datetime
import json
from pathlib import Path
from multiprocessing import Pool
import numpy as np
import pyarrow.parquet as pq

_TAG_WORK   = 1
_TAG_RESULT = 2

EVENT_COLS = [
    "GPU_MEM_FAULT", "GPU_SOFT_LOCK",  "GPU_RAS_FAIL",  "GPU_DRIVER_ERR",
    "GPU_FIRMWARE",  "GPU_HARD_FAULT", "GPU_TIMEOUT",   "HW_IF_GPU_LINK",
    "HW_MCE_GENERIC","HW_MCE_FATAL",   "HW_MCE_CORRECTED","HW_MCE_CPU",
    "HW_MCE_DUMP",   "HW_MCE_UNK",     "HW_MEM_DIMM",   "HW_MEM_CORRUPT",
    "HW_EDAC_ERR",   "HW_CPU_CORE",    "HW_PCIE_ERR",   "HW_PCIE_HUB",
    "HW_IOMMU_ERR",  "HW_BMC_WARN",    "HW_ACPI_WARN",  "HW_THERMAL_CRIT",
    "HW_USB_FAIL",   "HW_FABRIC_RTR",  "HW_FABRIC_INT", "NET_CXI_RAW_DATA",
    "NET_CXI_TIMEOUT","NET_CXI_LINK",  "NET_CXI_WARN",  "NET_CXI_INT_ERR",
    "NET_CXI_HW_ECC","NET_CXI_SVC",    "NET_CXI_FIRMWARE","NET_CXI_PHY_ERR",
    "NET_CXI_MGMT_ERR","NET_TCP_FAIL", "NET_CONFIG_ERR","NET_RPC_ERR",
    "NET_LNET_ERR",  "NET_LNET_WARN",  "FS_DISK_FULL",  "FS_DVS_WARN",
    "FS_CLUSTER_EVICT","FS_LUSTRE_SLOW","FS_LUSTRE_OST_ERR","FS_LUSTRE_ERR",
    "FS_XFS_ERR",    "FS_IO_ERR",      "FS_GPFS_ERR",   "FS_LUSTRE_MDS_ERR",
    "STO_NVME_STALL","SYS_KERNEL_CTX","SYS_OOM_KILL",  "SYS_SEGFAULT",
    "SYS_WATCHDOG",  "SYS_CONFIG_ERR", "SYS_RCU_STALL", "SYS_KERNEL_PANIC",
    "SYS_COREDUMP",  "SYS_PROCESS_LIM","SYS_X11_NOISE", "SYS_CLOCK_SKEW",
    "SVC_RSYSLOG_ERR","SVC_SYSTEMD_START","SVC_CONFIG_ERR","SVC_SYSTEMD_SPEC",
    "SVC_SYSTEMD_TIME","SVC_SYSTEMD_EXIT","SVC_SYSTEMD_KILL","SVC_SYSTEMD_PAM",
    "APP_INFRA_FAIL","APP_JOB_CANCEL", "APP_CFG_ERR",   "APP_JOB_LATENCY",
    "APP_JOB_CGROUP","APP_FILE_MISSING","APP_JOB_ERR",  "APP_GITLAB_FAIL",
    "INFO_NOISE",    "SEC_AUTH_FAIL",  "CTX_LUSTRE",    "CTX_AMDGPU",
    "CTX_SCHEDULER", "CTX_MEMORY",    "CTX_SLINGSHOT",
]

RARITY_BANDS = [
    ("ULTRA_RARE",  0,         500),
    ("RARE",        500,       5_000),
    ("MODERATE",    5_000,     50_000),
    ("COMMON",      50_000,    500_000),
    ("VERY_COMMON", 500_000,   10**12),
]


# ════════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════════

def now_str() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def status(stage: str, msg: str, t0: float = None, rank: int = 0):
    elapsed = f"  (+{time.time() - t0:.1f}s)" if t0 is not None else ""
    print(f"[{now_str()}] [R{rank:03d}] [{stage}] {msg}{elapsed}", flush=True)

def eta_str(done: int, total: int, elapsed_s: float) -> str:
    if done == 0:
        return "ETA: unknown"
    rate   = done / elapsed_s
    eta_s  = (total - done) / rate
    eta_dt = datetime.datetime.now() + datetime.timedelta(seconds=eta_s)
    return (f"ETA {eta_dt.strftime('%H:%M:%S')}  "
            f"(~{eta_s:.0f}s)  "
            f"rate={rate:.1f} nodes/s")

def rarity_label(count: int) -> str:
    return next(lbl for lbl, lo, hi in RARITY_BANDS if lo <= count < hi)


# ════════════════════════════════════════════════════════════════════════
# Per-file worker
# ════════════════════════════════════════════════════════════════════════

def process_node(path_str: str) -> dict:
    t_node = time.time()
    path   = Path(path_str)
    try:
        tbl    = pq.ParquetFile(path).read(columns=["is_separator"] + EVENT_COLS)
        is_sep = tbl["is_separator"].to_numpy(zero_copy_only=False).astype(bool)
        mask   = ~is_sep

        total_counts = {}
        node_counts  = {}
        for col in EVENT_COLS:
            col_data          = tbl[col].to_numpy(zero_copy_only=False)
            col_sum           = int(col_data[mask].sum())
            total_counts[col] = col_sum
            node_counts[col]  = 1 if col_sum > 0 else 0

        return {
            "total_counts": total_counts,
            "node_counts":  node_counts,
            "total_rows":   int(mask.sum()),
            "node_name":    path.parent.name.replace("node=", ""),
            "read_s":       round(time.time() - t_node, 2),
            "error":        None,
        }
    except Exception as e:
        return {
            "total_counts": {col: 0 for col in EVENT_COLS},
            "node_counts":  {col: 0 for col in EVENT_COLS},
            "total_rows":   0,
            "node_name":    path.parent.name.replace("node=", ""),
            "read_s":       round(time.time() - t_node, 2),
            "error":        str(e),
        }


# ════════════════════════════════════════════════════════════════════════
# Shared output logic  (used by both MPI coordinator and local fallback)
# ════════════════════════════════════════════════════════════════════════

def _write_output(total_counts: dict, node_counts: dict, total_rows: int,
                  all_errors: list, paths: list, output_dir: Path, t0: float):
    """Print stats table and write CSV. No MPI dependency."""

    n_nodes      = len(paths)
    sorted_events = sorted(total_counts.items(), key=lambda x: x[1])
    total_events  = sum(total_counts.values())
    median_count  = sorted(total_counts.values())[len(EVENT_COLS) // 2]

    if all_errors:
        status("WARN", f"{len(all_errors)} node(s) failed:", t0, rank=0)
        for name, err in all_errors:
            status("WARN", f"  {name}: {err}", t0, rank=0)

    status("STATS", "=" * 60, t0, rank=0)
    status("STATS", f"  Total event occurrences : {total_events:,}",  t0, rank=0)
    status("STATS", f"  Total data rows         : {total_rows:,}",    t0, rank=0)
    status("STATS", f"  Variables               : {len(EVENT_COLS)}", t0, rank=0)
    status("STATS", f"  Rarest  event           : {sorted_events[0][1]:,}  ({sorted_events[0][0]})",   t0, rank=0)
    status("STATS", f"  Most common event       : {sorted_events[-1][1]:,}  ({sorted_events[-1][0]})", t0, rank=0)
    status("STATS", f"  Median event count      : {median_count:,}",  t0, rank=0)

    status("STATS", "Rarity bands:", t0, rank=0)
    for label, lo, hi in RARITY_BANDS:
        names = [col for col, c in sorted_events if lo <= c < hi]
        status("STATS",
               f"  {label:<12}  count [{lo:>8,} – "
               f"{'∞' if hi > 10**11 else f'{hi:,}':>10}]  "
               f"n={len(names):>3}  {names}",
               t0, rank=0)

    status("TABLE", "Full distribution (rarest → most common):", t0, rank=0)
    print(f"\n  {'EVENT':<28} {'TOTAL_COUNT':>12} {'PCT_OF_ALL':>11} "
          f"{'NODES_WITH':>11} {'PCT_NODES':>10}  RARITY")
    print("  " + "-" * 87)
    for col, count in sorted_events:
        pct_e = 100.0 * count            / max(total_events, 1)
        pct_n = 100.0 * node_counts[col] / max(n_nodes,      1)
        print(f"  {col:<28} {count:>12,} {pct_e:>10.4f}% "
              f"{node_counts[col]:>11,} {pct_n:>9.1f}%  {rarity_label(count)}")
    print("  " + "-" * 87)
    print(f"  {'TOTAL':<28} {total_events:>12,} {'100.0000%':>11}\n")

    csv_path = output_dir / "event_count_distribution.csv"
    status("WRITE", f"Writing CSV → {csv_path}", t0, rank=0)
    with open(csv_path, "w") as fh:
        fh.write("event,total_count,pct_of_all_events,"
                 "nodes_with_event,pct_nodes,rarity\n")
        for col, count in sorted_events:
            fh.write(f"{col},{count},"
                     f"{100.0 * count / max(total_events, 1):.4f},"
                     f"{node_counts[col]},"
                     f"{100.0 * node_counts[col] / max(n_nodes, 1):.1f},"
                     f"{rarity_label(count)}\n")

    status("DONE", f"CSV → {csv_path}", t0, rank=0)
    status("DONE", f"Wall = {time.time() - t0:.1f}s  "
           f"({(time.time() - t0)/60:.1f} min)", t0, rank=0)


# ════════════════════════════════════════════════════════════════════════
# MPI rank worker
# ════════════════════════════════════════════════════════════════════════

def run_worker(comm, n_workers: int, t0: float, rank: int):
    from mpi4py import MPI

    paths = comm.recv(source=0, tag=_TAG_WORK)
    if paths is None:
        status("WORKER", "No files assigned — idle", t0, rank)
        comm.send(None, dest=0, tag=_TAG_RESULT)
        return

    status("WORKER",
           f"Received {len(paths)} files  local_pool_workers={n_workers}",
           t0, rank)

    total_counts = {col: 0 for col in EVENT_COLS}
    node_counts  = {col: 0 for col in EVENT_COLS}
    total_rows   = 0
    errors       = []
    done         = 0
    t_read       = time.time()

    with Pool(processes=n_workers) as pool:
        for result in pool.imap_unordered(process_node, paths, chunksize=4):
            done += 1
            if result["error"]:
                errors.append((result["node_name"], result["error"]))
                status("ERROR",
                       f"  node={result['node_name']}  "
                       f"err={result['error']}", t0, rank)
            else:
                for col in EVENT_COLS:
                    total_counts[col] += result["total_counts"][col]
                    node_counts[col]  += result["node_counts"][col]
                total_rows += result["total_rows"]

            flag = "ERROR" if result["error"] else "OK"
            status("NODE",
                   f"  [{done:>5}/{len(paths)}]  {flag:<5}  "
                   f"node={result['node_name']:<20}  "
                   f"rows={result['total_rows']:>10,}  "
                   f"read={result['read_s']:.2f}s",
                   t0, rank)

            if done % 50 == 0 or done == len(paths):
                status("PROGRESS",
                       f"  {done}/{len(paths)}  "
                       f"({100*done/len(paths):.1f}%)  "
                       + eta_str(done, len(paths), time.time() - t_read),
                       t0, rank)

    read_elapsed = time.time() - t_read
    status("WORKER",
           f"Done  files={done}  errors={len(errors)}  "
           f"rows={total_rows:,}  elapsed={read_elapsed:.1f}s",
           t0, rank)

    comm.send({
        "total_counts": total_counts,
        "node_counts":  node_counts,
        "total_rows":   total_rows,
        "errors":       errors,
        "rank":         rank,
    }, dest=0, tag=_TAG_RESULT)


# ════════════════════════════════════════════════════════════════════════
# MPI coordinator  (rank 0)
# ════════════════════════════════════════════════════════════════════════

def run_coordinator(comm, paths: list, output_dir: Path,
                    n_workers: int, t0: float):
    from mpi4py import MPI

    size    = comm.Get_size()
    n_ranks = size - 1
    n_files = len(paths)

    status("COORD",
           f"files={n_files}  worker_ranks={n_ranks}  "
           f"workers_per_rank={n_workers}  "
           f"total_parallel_workers={n_ranks * n_workers}",
           t0, rank=0)

    chunk_size = max(1, n_files // n_ranks)
    for i in range(1, size):
        lo    = (i - 1) * chunk_size
        hi    = lo + chunk_size if i < size - 1 else n_files
        chunk = [str(p) for p in paths[lo:hi]]
        comm.send(chunk, dest=i, tag=_TAG_WORK)
        status("COORD",
               f"  Sent {len(chunk)} files to rank {i}  "
               f"(files {lo}–{hi-1})",
               t0, rank=0)

    total_counts = {col: 0 for col in EVENT_COLS}
    node_counts  = {col: 0 for col in EVENT_COLS}
    total_rows   = 0
    all_errors   = []
    received     = 0

    status("COORD", f"Waiting for {n_ranks} worker ranks to finish …", t0, rank=0)

    for _ in range(n_ranks):
        result = comm.recv(source=MPI.ANY_SOURCE, tag=_TAG_RESULT)
        if result is None:
            continue
        received += 1
        r = result["rank"]
        status("COORD",
               f"  [{received}/{n_ranks}] Result from rank {r}  "
               f"rows={result['total_rows']:,}  "
               f"errors={len(result['errors'])}",
               t0, rank=0)
        for col in EVENT_COLS:
            total_counts[col] += result["total_counts"][col]
            node_counts[col]  += result["node_counts"][col]
        total_rows  += result["total_rows"]
        all_errors  += result["errors"]

    status("COORD",
           f"All ranks done  total_rows={total_rows:,}  "
           f"total_errors={len(all_errors)}",
           t0, rank=0)

    # ── Delegate all output to shared helper ──────────────────────────────
    _write_output(total_counts, node_counts, total_rows,
                  all_errors, paths, output_dir, t0)


# ════════════════════════════════════════════════════════════════════════
# Single-node fallback (no MPI)
# ════════════════════════════════════════════════════════════════════════

def run_worker_local(paths, output_dir, n_workers, t0):
    """Single-node fallback — no MPI dependency anywhere in this function."""
    status("WORKER",
           f"Single-node mode  files={len(paths)}  workers={n_workers}",
           t0, rank=0)
    total_counts = {col: 0 for col in EVENT_COLS}
    node_counts  = {col: 0 for col in EVENT_COLS}
    total_rows   = 0
    errors       = []
    done         = 0
    t_read       = time.time()

    with Pool(processes=n_workers) as pool:
        for result in pool.imap_unordered(
                process_node, [str(p) for p in paths], chunksize=4):
            done += 1
            if result["error"]:
                errors.append((result["node_name"], result["error"]))
            else:
                for col in EVENT_COLS:
                    total_counts[col] += result["total_counts"][col]
                    node_counts[col]  += result["node_counts"][col]
                total_rows += result["total_rows"]

            flag = "ERROR" if result["error"] else "OK"
            status("NODE",
                   f"  [{done:>5}/{len(paths)}]  {flag:<5}  "
                   f"node={result['node_name']:<20}  "
                   f"rows={result['total_rows']:>10,}  "
                   f"read={result['read_s']:.2f}s",
                   t0, rank=0)

            if done % 50 == 0 or done == len(paths):
                status("PROGRESS",
                       f"  {done}/{len(paths)}  ({100*done/len(paths):.1f}%)  "
                       + eta_str(done, len(paths), time.time() - t_read),
                       t0, rank=0)

    status("WORKER",
           f"Done  files={done}  errors={len(errors)}  "
           f"rows={total_rows:,}  elapsed={time.time()-t_read:.1f}s",
           t0, rank=0)

    # ── Call shared output helper directly — no comm=None hack ───────────
    _write_output(total_counts, node_counts, total_rows,
                  errors, paths, output_dir, t0)


# ════════════════════════════════════════════════════════════════════════
# Entry point
# ════════════════════════════════════════════════════════════════════════

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parquet_dir", required=True)
    ap.add_argument("--output_dir",  required=True)
    ap.add_argument("--n_workers",   type=int, default=32)
    args = ap.parse_args()

    t0          = time.time()
    parquet_dir = Path(args.parquet_dir)
    output_dir  = Path(args.output_dir)

    try:
        from mpi4py import MPI
        comm          = MPI.COMM_WORLD
        rank          = comm.Get_rank()
        size          = comm.Get_size()
        mpi_available = size > 1
    except ImportError:
        rank = 0; size = 1; mpi_available = False; comm = None

    if rank == 0:
        output_dir.mkdir(parents=True, exist_ok=True)
        status("INIT", "=" * 60, t0, rank)
        status("INIT", f"MPI ranks      : {size}", t0, rank)
        status("INIT", f"Workers/rank   : {args.n_workers}", t0, rank)
        status("INIT", f"Total workers  : {(size-1) * args.n_workers}", t0, rank)
        status("INIT", f"Parquet dir    : {parquet_dir}", t0, rank)
        status("INIT", f"Output dir     : {output_dir}", t0, rank)
        status("INIT", "=" * 60, t0, rank)

    if mpi_available:
        comm.Barrier()

    node_dirs = sorted(parquet_dir.glob("node=frontier*"))
    paths     = [nd / "data.parquet" for nd in node_dirs
                 if (nd / "data.parquet").exists()]

    if rank == 0:
        status("INIT", f"Node parquet files found: {len(paths):,}", t0, rank)

    if not paths:
        raise FileNotFoundError(f"No data.parquet files under {parquet_dir}")

    if mpi_available:
        if rank == 0:
            run_coordinator(comm, paths, output_dir, args.n_workers, t0)
        else:
            run_worker(comm, args.n_workers, t0, rank)
    else:
        status("INIT", "MPI not available — running single-node fallback", t0, rank)
        run_worker_local(paths, output_dir, args.n_workers, t0)


if __name__ == "__main__":
    main()