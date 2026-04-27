"""
PCMCIplus causal discovery – single MPI job, one rank per node.
Fix: separator rows use mask=True + data=0.0 (not NaN).
Sampling: contiguous-window sampling with rare-event guarantee.
          Windows preserve 5-second temporal spacing within each window.
          Separator rows inserted between windows to tell Tigramite
          they are not consecutive.
Heartbeat: background thread prints every 30s during PCMCIplus run.
Variable grouping: GPU / HW_MCE / HW_OTHER / NET_CXI / NET_OTHER /
                   FS / SYS / SVC_APP / CTX_SEC
Parallelism: one MPI rank per node; rank 0 = coordinator (work queue),
             ranks 1..N-1 = workers.  Dynamic work stealing ensures no
             rank idles while others are still busy.
Launcher: mpirun (conda-forge OpenMPI does not integrate with srun).
"""

import argparse
import json
import time
import os
import sys
import datetime
import threading
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq

# ════════════════════════════════════════════════════════════════════════
# Variable catalogue
# ═════════════════════════���══════════════════════════════════════════════

VARIABLE_GROUPS = {
    "GPU": [
        "GPU_MEM_FAULT", "GPU_SOFT_LOCK",  "GPU_RAS_FAIL",  "GPU_DRIVER_ERR",
        "GPU_FIRMWARE",  "GPU_HARD_FAULT", "GPU_TIMEOUT",   "HW_IF_GPU_LINK",
    ],
    "HW_MCE": [
        "HW_MCE_GENERIC", "HW_MCE_FATAL",     "HW_MCE_CORRECTED", "HW_MCE_CPU",
        "HW_MCE_DUMP",    "HW_MCE_UNK",       "HW_MEM_DIMM",      "HW_MEM_CORRUPT",
        "HW_EDAC_ERR",    "HW_CPU_CORE",
    ],
    "HW_OTHER": [
        "HW_PCIE_ERR",  "HW_PCIE_HUB",     "HW_IOMMU_ERR",    "HW_BMC_WARN",
        "HW_ACPI_WARN", "HW_THERMAL_CRIT", "HW_USB_FAIL",     "HW_FABRIC_RTR",
        "HW_FABRIC_INT",
    ],
    "NET_CXI": [
        "NET_CXI_RAW_DATA", "NET_CXI_TIMEOUT", "NET_CXI_LINK",     "NET_CXI_WARN",
        "NET_CXI_INT_ERR",  "NET_CXI_HW_ECC",  "NET_CXI_SVC",      "NET_CXI_FIRMWARE",
        "NET_CXI_PHY_ERR",  "NET_CXI_MGMT_ERR",
    ],
    "NET_OTHER": [
        "NET_TCP_FAIL", "NET_CONFIG_ERR", "NET_RPC_ERR",
        "NET_LNET_ERR", "NET_LNET_WARN",
    ],
    "FS": [
        "FS_DISK_FULL",      "FS_DVS_WARN",       "FS_CLUSTER_EVICT",  "FS_LUSTRE_SLOW",
        "FS_LUSTRE_OST_ERR", "FS_LUSTRE_ERR",     "FS_XFS_ERR",        "FS_IO_ERR",
        "FS_GPFS_ERR",       "FS_LUSTRE_MDS_ERR", "STO_NVME_STALL",
    ],
    "SYS": [
        "SYS_KERNEL_CTX",  "SYS_OOM_KILL",  "SYS_SEGFAULT",     "SYS_WATCHDOG",
        "SYS_CONFIG_ERR",  "SYS_RCU_STALL", "SYS_KERNEL_PANIC", "SYS_COREDUMP",
        "SYS_PROCESS_LIM", "SYS_X11_NOISE", "SYS_CLOCK_SKEW",
    ],
    "SVC_APP": [
        "SVC_RSYSLOG_ERR",  "SVC_SYSTEMD_START", "SVC_CONFIG_ERR",   "SVC_SYSTEMD_SPEC",
        "SVC_SYSTEMD_TIME", "SVC_SYSTEMD_EXIT",  "SVC_SYSTEMD_KILL", "SVC_SYSTEMD_PAM",
        "APP_INFRA_FAIL",   "APP_JOB_CANCEL",    "APP_CFG_ERR",      "APP_JOB_LATENCY",
        "APP_JOB_CGROUP",   "APP_FILE_MISSING",  "APP_JOB_ERR",      "APP_GITLAB_FAIL",
    ],
    "CTX_SEC": [
        "INFO_NOISE",     "SEC_AUTH_FAIL", "CTX_LUSTRE",    "CTX_AMDGPU",
        "CTX_SCHEDULER",  "CTX_MEMORY",   "CTX_SLINGSHOT",
    ],
}

EVENT_COLS: list[str] = []
for _grp_cols in VARIABLE_GROUPS.values():
    for _col in _grp_cols:
        if _col not in EVENT_COLS:
            EVENT_COLS.append(_col)

N_VARS = len(EVENT_COLS)

GROUP_COL_INDICES: dict[str, np.ndarray] = {
    grp: np.array([EVENT_COLS.index(c) for c in cols], dtype=np.intp)
    for grp, cols in VARIABLE_GROUPS.items()
}

# MPI tags
_TAG_WORK   = 1   # coordinator → worker: {"group_idx": int} or None (poison)
_TAG_RESULT = 2   # worker → coordinator: {"group_id": str, "status": str, ...}


# ════════════════════════════════════════════════════════════════════════
# Logging
# ════════════════════════════════════════════════════════════════════════

def now_str() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def log(tag: str, msg: str, t0: float = None, rank: int = 0) -> float:
    now = time.time()
    e   = f"  (+{now - t0:.1f}s)" if t0 is not None else ""
    print(f"[{now_str()}] [R{rank:03d}] [{tag}] {msg}{e}", flush=True)
    return now

def eta_str(done: int, total: int, elapsed_s: float) -> str:
    if done == 0:
        return "ETA: unknown"
    eta_s  = (total - done) / (done / elapsed_s)
    eta_dt = datetime.datetime.now() + datetime.timedelta(seconds=eta_s)
    return (f"ETA: {eta_dt.strftime('%Y-%m-%d %H:%M:%S')}  "
            f"(~{eta_s / 3600:.1f}h remaining)")


# ════════════════════════════════════════════════════════════════════════
# Heartbeat thread
# ════════════════════════════════════════════════════════════════════════

class Heartbeat:
    def __init__(self, label: str, rank: int, interval: int = 30,
                 job_start: float = None):
        self.label     = label
        self.rank      = rank
        self.interval  = interval
        self.job_start = job_start or time.time()
        self.t_start   = time.time()
        self._stop     = threading.Event()
        self._thread   = threading.Thread(target=self._run, daemon=True)

    def start(self): self._thread.start()

    def stop(self):
        self._stop.set()
        self._thread.join()

    def _run(self):
        tick = 0
        while not self._stop.wait(timeout=self.interval):
            tick += 1
            elapsed = time.time() - self.t_start
            log("HEARTBEAT",
                f"{self.label}  pcmci_elapsed={elapsed / 60:.1f}min  "
                f"tick={tick}  rss={self._rss_gb():.2f}GB",
                self.job_start, self.rank)

    @staticmethod
    def _rss_gb() -> float:
        try:
            with open("/proc/self/status") as fh:
                for line in fh:
                    if line.startswith("VmRSS:"):
                        return int(line.split()[1]) / 1_048_576
        except Exception:
            pass
        return 0.0


# ════════════════════════════════════════════════════════════════════════
# Tigramite stdout wrapper
# ════════════════════════════════════════════════════════════════════════

class TimestampedStdout:
    def __init__(self, original, rank: int = 0):
        self._orig = original
        self._buf  = ""
        self.rank  = rank

    def write(self, text):
        self._buf += text
        while "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            if line.strip():
                self._orig.write(
                    f"[{now_str()}] [R{self.rank:03d}] [TIGRAMITE] {line}\n")
                self._orig.flush()

    def flush(self):
        if self._buf.strip():
            self._orig.write(
                f"[{now_str()}] [R{self.rank:03d}] [TIGRAMITE] {self._buf}\n")
            self._orig.flush()
        self._buf = ""

    def fileno(self): return self._orig.fileno()


# ════════════════════════════════════════════════════════════════════════
# Sampling — contiguous-window sampling with rare-event guarantee
# ════════════════════════════════════════════════════════════════════════

def contiguous_window_sample(
        block: np.ndarray,
        is_sep: np.ndarray,
        target_rows: int,
        window_size: int,
        rare_threshold: float,
        rng: np.random.Generator,
        job_start: float,
        node_name: str,
        rank: int = 0,
) -> tuple[np.ndarray, np.ndarray]:
    sep_idx  = np.where(is_sep)[0]
    data_idx = np.where(~is_sep)[0]
    T_data   = len(data_idx)

    if T_data == 0:
        return block, is_sep

    data_only = block[data_idx]
    row_sums  = data_only.sum(axis=1)

    col_means   = data_only.mean(axis=0)
    rare_mask   = col_means < rare_threshold
    n_rare_cols = int(rare_mask.sum())

    if n_rare_cols > 0:
        rare_row_local = np.where(
            (data_only[:, rare_mask] > 0).any(axis=1))[0]
    else:
        rare_row_local = np.array([], dtype=np.int64)

    half = window_size // 2

    def window_range(anchor: int) -> tuple[int, int]:
        lo = max(0, anchor - half)
        hi = min(T_data - 1, anchor + half)
        return lo, hi

    covered = np.zeros(T_data, dtype=bool)
    windows: list[tuple[int, int]] = []

    def add_window(anchor: int):
        lo, hi = window_range(anchor)
        windows.append((lo, hi))
        covered[lo:hi + 1] = True

    for r in rare_row_local:
        if not covered[r]:
            add_window(int(r))

    active_local     = np.where(row_sums > 0)[0]
    uncovered_active = active_local[~covered[active_local]]
    if len(uncovered_active) > 0:
        perm = rng.permutation(len(uncovered_active))
        for idx in perm:
            if covered.sum() >= target_rows:
                break
            a = int(uncovered_active[idx])
            if not covered[a]:
                add_window(a)

    if covered.sum() < target_rows:
        uncovered_all = np.where(~covered)[0]
        perm = rng.permutation(len(uncovered_all))
        for idx in perm:
            if covered.sum() >= target_rows:
                break
            a = int(uncovered_all[idx])
            if not covered[a]:
                add_window(a)

    windows.sort(key=lambda w: w[0])
    merged: list[tuple[int, int]] = []
    for lo, hi in windows:
        if merged and lo <= merged[-1][1] + 1:
            merged[-1] = (merged[-1][0], max(merged[-1][1], hi))
        else:
            merged.append((lo, hi))

    sep_row  = np.zeros((1, N_VARS), dtype=np.float64)
    sep_flag = np.array([True], dtype=bool)

    out_blocks: list[np.ndarray] = []
    out_flags:  list[np.ndarray] = []

    for win_idx, (lo, hi) in enumerate(merged):
        orig_indices = data_idx[lo:hi + 1]
        out_blocks.append(block[orig_indices])
        out_flags.append(is_sep[orig_indices])
        if win_idx < len(merged) - 1:
            out_blocks.append(sep_row)
            out_flags.append(sep_flag)

    if len(sep_idx) > 0:
        out_blocks.append(block[sep_idx])
        out_flags.append(is_sep[sep_idx])

    new_block  = np.concatenate(out_blocks, axis=0)
    new_is_sep = np.concatenate(out_flags,  axis=0)

    T_after        = int((~new_is_sep).sum())
    n_windows      = len(merged)
    n_sep_inserted = n_windows - 1

    log("SAMPLE",
        f"  {node_name:<20s}  T_before={T_data:>10,}  "
        f"T_after={T_after:>8,}  "
        f"kept={100 * T_after / max(T_data, 1):.2f}%  "
        f"windows={n_windows}  sep_inserted={n_sep_inserted}  "
        f"rare_cols={n_rare_cols}  "
        f"rare_rows_covered={len(rare_row_local):,}",
        job_start, rank)

    return new_block, new_is_sep


# ════════════════════════════════════════════════════════════════════════
# Per-group variable statistics
# ════════════════════════════════════════════════════════════════════════

def log_group_variable_stats(block, is_sep, node_name, job_start, rank=0):
    data_rows = ~is_sep
    if data_rows.sum() == 0:
        return
    data_only = block[data_rows]
    parts = [f"{grp}={data_only[:, idx].mean():.4f}"
             for grp, idx in GROUP_COL_INDICES.items()]
    log("STATS",
        f"  {node_name:<20s}  group_means: " + "  ".join(parts),
        job_start, rank)


# ════════════════════════════════════════════════════════════════════════
# Parquet reader
# ════════════════════════════════════════════════════════════════════════

def read_node_parquet(path: str, job_start: float, rank: int = 0):
    t0  = time.time()
    pf  = pq.ParquetFile(path)
    tbl = pf.read(columns=["is_separator"] + EVENT_COLS)

    is_sep = tbl["is_separator"].to_numpy(zero_copy_only=False).astype(bool)
    block  = np.column_stack([
        tbl[c].to_numpy(zero_copy_only=False).astype(np.float64)
        for c in EVENT_COLS
    ])
    block[is_sep] = 0.0

    nan_n = int(np.isnan(block).sum())
    if nan_n:
        raise ValueError(f"NaN in non-separator rows of {path} ({nan_n}).")

    node_name = Path(path).parent.name.replace("node=", "")
    log("READ",
        f"  {node_name:<20s}  rows={len(is_sep):>10,}  "
        f"sep={int(is_sep.sum()):>3}  read={time.time() - t0:.1f}s",
        job_start, rank)
    return block, is_sep, node_name


# ════════════════════════════════════════════════════════════════════════
# Group builder
# ════════════════════════════════════════════════════════════════════════

def build_groups(node_dirs: list, group_size: int,
                 cross_group_fraction: float) -> list[dict]:
    nodes_sorted = sorted(node_dirs, key=lambda p: p.name)
    node_names   = [p.name.replace("node=", "") for p in nodes_sorted]
    groups: list[dict] = []

    for start in range(0, len(node_names), group_size):
        chunk = node_names[start:start + group_size]
        groups.append({
            "group_id": f"nat_{start:05d}",
            "nodes":    chunk,
            "paths":    [str(nodes_sorted[start + i] / "data.parquet")
                         for i in range(len(chunk))],
        })

    if cross_group_fraction > 0:
        import random
        rng        = random.Random(42)
        n_cross    = int(len(groups) * cross_group_fraction)
        half       = group_size // 2
        nat_chunks = [g["nodes"] for g in groups]
        path_map   = {p.name.replace("node=", ""): str(p / "data.parquet")
                      for p in nodes_sorted}
        for ci in range(n_cross):
            a_idx   = rng.randint(0, len(nat_chunks) // 2 - 1)
            b_idx   = rng.randint(len(nat_chunks) // 2, len(nat_chunks) - 1)
            a_nodes = rng.sample(nat_chunks[a_idx],
                                 min(half, len(nat_chunks[a_idx])))
            b_nodes = rng.sample(nat_chunks[b_idx],
                                 min(half, len(nat_chunks[b_idx])))
            groups.append({
                "group_id": f"cross_{ci:05d}",
                "nodes":    a_nodes + b_nodes,
                "paths":    [path_map[nd] for nd in a_nodes + b_nodes],
            })
    return groups


# ════════════════════════════════════════════════════════════════════════
# Core worker  —  runs ONE group
# ════════════════════════════════════════════════════════════════════════

def run_pcmciplus_group(
        group: dict,
        count_cap: int,
        tau_max: int,
        pc_alpha: float,
        output_dir: Path,
        n_cpus: int,
        job_start: float,
        group_num: int,
        total_groups: int,
        target_rows: int,
        window_size: int,
        rare_threshold: float,
        max_conds_dim: int,
        heartbeat_interval: int = 30,
        rank: int = 0,
) -> dict:

    for var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS",
                "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        os.environ[var] = str(n_cpus)

    group_id   = group["group_id"]
    node_names = group["nodes"]
    paths      = group["paths"]
    t0         = time.time()

    out_path = output_dir / f"group_{group_id}.json"
    if out_path.exists():
        log("SKIP", f"[{group_num}/{total_groups}] {group_id} already done",
            job_start, rank)
        return {"group_id": group_id, "status": "skipped"}

    log("GROUP", "=" * 60, job_start, rank)
    log("GROUP",
        f"[{group_num}/{total_groups}] START  {group_id}  "
        f"nodes={len(node_names)}  target_rows/node={target_rows:,}  "
        f"window_size={window_size}  max_conds_dim={max_conds_dim}  "
        f"tau_max={tau_max}",
        job_start, rank)
    log("GROUP", f"  nodes: {node_names}", job_start, rank)

    data_blocks: list[np.ndarray] = []
    mask_blocks: list[np.ndarray] = []
    capped_per_node:  list[int]   = []
    capped_per_group: dict        = {g: 0 for g in VARIABLE_GROUPS}
    rng_global = np.random.default_rng(42)
    t_load = time.time()

    for path in paths:
        block, is_sep, node_name = read_node_parquet(path, job_start, rank)

        if count_cap > 0:
            data_mask  = ~is_sep
            data_slice = block[data_mask]
            for grp, idx_arr in GROUP_COL_INDICES.items():
                capped_per_group[grp] += int(
                    (data_slice[:, idx_arr] > count_cap).sum())
            n_capped = int((data_slice > count_cap).sum())
            np.clip(data_slice, 0.0, float(count_cap), out=data_slice)
            block[data_mask] = data_slice
            capped_per_node.append(n_capped)
        else:
            capped_per_node.append(0)

        log_group_variable_stats(block, is_sep, node_name, job_start, rank)

        block, is_sep = contiguous_window_sample(
            block, is_sep,
            target_rows    = target_rows,
            window_size    = window_size,
            rare_threshold = rare_threshold,
            rng            = rng_global,
            job_start      = job_start,
            node_name      = node_name,
            rank           = rank,
        )

        mask = np.repeat(is_sep[:, np.newaxis], N_VARS, axis=1)
        data_blocks.append(block)
        mask_blocks.append(mask)

    data_full    = np.concatenate(data_blocks, axis=0)
    mask_full    = np.concatenate(mask_blocks, axis=0)
    T_total      = data_full.shape[0]
    T_data_rows  = int((~mask_full[:, 0]).sum())
    T_sep_rows   = T_total - T_data_rows
    total_capped = sum(capped_per_node)

    if np.isnan(data_full).any():
        raise ValueError("BUG: NaN in data_full after assembly.")

    load_time = time.time() - t_load
    log("GROUP",
        f"  [{group_num}/{total_groups}] Data ready  "
        f"T_data={T_data_rows:>8,}  T_sep={T_sep_rows}  "
        f"T_total={T_total:>8,}  capped={total_capped:,}  "
        f"load+sample={load_time:.1f}s",
        job_start, rank)
    log("GROUP",
        f"  [{group_num}/{total_groups}] shape={data_full.shape}  "
        f"mask_frac={mask_full.mean():.4f}",
        job_start, rank)

    import tigramite.data_processing as pp
    from tigramite.pcmci import PCMCI
    from tigramite.independence_tests.parcorr import ParCorr

    dataframe = pp.DataFrame(data=data_full, mask=mask_full,
                             var_names=EVENT_COLS)
    pcmci = PCMCI(
        dataframe     = dataframe,
        cond_ind_test = ParCorr(significance="analytic", mask_type="y"),
        verbosity     = 1,
    )

    log("GROUP",
        f"  [{group_num}/{total_groups}] PCMCIplus START  "
        f"N={N_VARS}  T_eff={T_data_rows:,}  "
        f"max_conds_dim={max_conds_dim}  tau_max={tau_max}",
        job_start, rank)

    t_pcmci     = time.time()
    hb          = Heartbeat(group_id, rank=rank,
                            interval=heartbeat_interval,
                            job_start=job_start)
    hb.start()
    orig_stdout = sys.stdout
    sys.stdout  = TimestampedStdout(orig_stdout, rank=rank)
    try:
        results = pcmci.run_pcmciplus(
            tau_min       = 1,
            tau_max       = tau_max,
            pc_alpha      = pc_alpha,
            max_conds_dim = max_conds_dim,
        )
    finally:
        sys.stdout = orig_stdout
        hb.stop()

    pcmci_s = time.time() - t_pcmci
    log("GROUP",
        f"  [{group_num}/{total_groups}] PCMCIplus DONE  "
        f"{pcmci_s:.1f}s ({pcmci_s / 60:.1f}min)",
        job_start, rank)

    graph      = results["graph"]
    val_matrix = results["val_matrix"]
    p_matrix   = results["p_matrix"]
    sig_links  = []

    for i in range(N_VARS):
        for j in range(N_VARS):
            for tau in range(tau_max + 1):
                g = graph[i, j, tau]
                if g and g != "x-x":
                    sig_links.append({
                        "cause":    EVENT_COLS[j],
                        "effect":   EVENT_COLS[i],
                        "tau":      int(tau),
                        "val":      float(val_matrix[i, j, tau]),
                        "p_val":    float(p_matrix[i, j, tau]),
                        "edge":     g,
                        "group_id": group_id,
                        "nodes":    node_names,
                    })

    log("GROUP",
        f"  [{group_num}/{total_groups}] sig_links={len(sig_links)}",
        job_start, rank)

    tmp = out_path.with_suffix(".tmp")
    with open(tmp, "w") as fh:
        json.dump({
            "group_id":             group_id,
            "nodes":                node_names,
            "T_total":              T_total,
            "T_data_rows":          T_data_rows,
            "count_cap":            count_cap,
            "target_rows_per_node": target_rows,
            "window_size":          window_size,
            "max_conds_dim":        max_conds_dim,
            "tau_max":              tau_max,
            "total_cells_capped":   total_capped,
            "capped_per_node":      capped_per_node,
            "capped_per_var_group": capped_per_group,
            "n_sig_links":          len(sig_links),
            "pcmci_seconds":        round(pcmci_s, 1),
            "links":                sig_links,
        }, fh)
    tmp.rename(out_path)

    elapsed = time.time() - t0
    log("GROUP",
        f"  [{group_num}/{total_groups}] DONE  {group_id}  "
        f"links={len(sig_links)}  wall={elapsed:.0f}s ({elapsed/60:.1f}min)  "
        f"→ {out_path.name}",
        job_start, rank)

    return {"group_id": group_id, "status": "ok",
            "n_sig_links": len(sig_links), "elapsed": elapsed}


# ════════════════════════════════════════════════════════════════════════
# MPI coordinator  (rank 0)
# ════════════════════════════════════════════════════════════════════════

def run_coordinator(comm, groups: list, output_dir: Path,
                    job_start: float):
    from mpi4py import MPI

    size      = comm.Get_size()
    n_workers = size - 1
    total     = len(groups)

    pending = [i for i in range(total)
               if not (output_dir /
                       f"group_{groups[i]['group_id']}.json").exists()]
    already_done = total - len(pending)

    log("COORD",
        f"total_groups={total}  already_done={already_done}  "
        f"pending={len(pending)}  workers={n_workers}",
        job_start, rank=0)

    queue      = list(pending)
    sent       = 0
    done_count = already_done
    t_progress = time.time()

    # Seed each worker with its first item (or poison if queue is short)
    for worker in range(1, n_workers + 1):
        if sent < len(queue):
            comm.send({"group_idx": queue[sent]}, dest=worker, tag=_TAG_WORK)
            sent += 1
        else:
            comm.send(None, dest=worker, tag=_TAG_WORK)

    active_workers = min(n_workers, len(queue))

    while active_workers > 0:
        status = MPI.Status()
        result = comm.recv(source=MPI.ANY_SOURCE, tag=_TAG_RESULT,
                           status=status)
        src = status.Get_source()

        if result.get("status") == "ok":
            done_count += 1

        if time.time() - t_progress > 60 or done_count % 10 == 0:
            log("COORD",
                f"  done={done_count}/{total}  "
                f"({100 * done_count / total:.1f}%)  "
                + eta_str(done_count - already_done,
                          len(pending),
                          time.time() - job_start),
                job_start, rank=0)
            t_progress = time.time()

        if sent < len(queue):
            comm.send({"group_idx": queue[sent]}, dest=src, tag=_TAG_WORK)
            sent += 1
        else:
            comm.send(None, dest=src, tag=_TAG_WORK)
            active_workers -= 1

    log("COORD", f"All workers finished.  done={done_count}/{total}",
        job_start, rank=0)


# ════════════════════════════════════════════════════════════════════════
# MPI worker  (ranks 1 .. N-1)
# ════════════════════════════════════════════════════════════════════════

def run_worker(comm, groups: list, args, output_dir: Path,
               job_start: float, rank: int):
    done_local = 0
    while True:
        msg = comm.recv(source=0, tag=_TAG_WORK)
        if msg is None:
            break
        idx    = msg["group_idx"]
        group  = groups[idx]
        result = run_pcmciplus_group(
            group              = group,
            count_cap          = args.count_cap,
            tau_max            = args.tau_max,
            pc_alpha           = args.pc_alpha,
            output_dir         = output_dir,
            n_cpus             = args.cpus_per_task,
            job_start          = job_start,
            group_num          = idx + 1,
            total_groups       = len(groups),
            target_rows        = args.target_rows,
            window_size        = args.window_size,
            rare_threshold     = args.rare_threshold,
            max_conds_dim      = args.max_conds_dim,
            heartbeat_interval = args.heartbeat_interval,
            rank               = rank,
        )
        comm.send(result, dest=0, tag=_TAG_RESULT)
        if result["status"] == "ok":
            done_local += 1

    log("WORKER", f"rank={rank}  done_local={done_local}", job_start, rank)


# ════════════════════════════════════════════════════════════════════════
# Aggregation
# ════════════════════════════════════════════════════════════════════════

def aggregate_results(group_files: list, output_dir: Path,
                      pc_alpha: float, job_start: float, rank: int = 0):
    log("AGGREGATE", f"Reading {len(group_files)} group result files …",
        job_start, rank)
    best_links: dict = {}
    total_loaded     = 0
    total_capped     = 0
    total_cpvg       = {g: 0 for g in VARIABLE_GROUPS}

    for path in sorted(group_files):
        with open(path) as fh:
            gd = json.load(fh)
        total_loaded += 1
        total_capped += gd.get("total_cells_capped", 0)
        for g, v in gd.get("capped_per_var_group", {}).items():
            if g in total_cpvg:
                total_cpvg[g] += v
        for lk in gd.get("links", []):
            key = (lk["cause"], lk["effect"], lk["tau"])
            if key not in best_links or lk["p_val"] < best_links[key]["p_val"]:
                best_links[key] = lk
        if total_loaded % 100 == 0:
            log("AGGREGATE",
                f"  {total_loaded}/{len(group_files)}  "
                f"links so far: {len(best_links):,}", job_start, rank)

    sorted_links = sorted(best_links.values(), key=lambda x: x["p_val"])
    log("AGGREGATE",
        f"groups={total_loaded}  unique_links={len(sorted_links):,}  "
        f"cells_capped={total_capped:,}", job_start, rank)

    graph_path = output_dir / "causal_graph.json"
    with open(graph_path, "w") as fh:
        json.dump({
            "n_groups":             total_loaded,
            "n_unique_links":       len(sorted_links),
            "pc_alpha":             pc_alpha,
            "total_cells_capped":   total_capped,
            "capped_per_var_group": total_cpvg,
            "links":                sorted_links,
        }, fh, indent=2)
    log("AGGREGATE", f"Causal graph → {graph_path}", job_start, rank)

    summary_path = output_dir / "causal_summary.txt"
    with open(summary_path, "w") as fh:
        fh.write(f"PCMCIplus causal graph – {len(sorted_links)} links\n")
        fh.write(f"alpha={pc_alpha}  groups={total_loaded}  "
                 f"capped={total_capped:,}\n")
        fh.write("=" * 80 + "\n\n")
        fh.write(f"{'CAUSE':<30} {'LAG':>4}  {'EDGE':>5}  {'EFFECT':<30}"
                 f"  {'VAL':>8}  {'P-VAL':>10}\n")
        fh.write("-" * 80 + "\n")
        for lk in sorted_links:
            fh.write(
                f"{lk['cause']:<30} {lk['tau']:>4}  {lk['edge']:>5}  "
                f"{lk['effect']:<30}  {lk['val']:>8.4f}"
                f"  {lk['p_val']:>10.2e}\n")
    log("AGGREGATE", f"Summary → {summary_path}", job_start, rank)
    log("AGGREGATE", "── Top 20 links ──", job_start, rank)
    for lk in sorted_links[:20]:
        log("AGGREGATE",
            f"  {lk['cause']:<28} --lag{lk['tau']}--> "
            f"{lk['effect']:<28}  p={lk['p_val']:.2e}  val={lk['val']:.4f}",
            job_start, rank)
    return sorted_links


# ════════════════════════════════════════════════════════════════════════
# Entry point
# ════════════════════════════════════════════════════════════════════════

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parquet_dir",          required=True)
    ap.add_argument("--output_dir",           required=True)
    ap.add_argument("--tau_max",              type=int,   default=3)
    ap.add_argument("--pc_alpha",             type=float, default=0.01)
    ap.add_argument("--group_size",           type=int,   default=8)
    ap.add_argument("--cross_group_fraction", type=float, default=0.0)
    ap.add_argument("--count_cap",            type=int,   default=10)
    ap.add_argument("--cpus_per_task",        type=int,   default=32)
    ap.add_argument("--target_rows",          type=int,   default=1_000)
    ap.add_argument("--window_size",          type=int,   default=500)
    ap.add_argument("--rare_threshold",       type=float, default=0.001)
    ap.add_argument("--max_conds_dim",        type=int,   default=3)
    ap.add_argument("--heartbeat_interval",   type=int,   default=30)
    ap.add_argument("--aggregate_only",       action="store_true")
    ap.add_argument("--n_tasks",              type=int,   default=4)
    args = ap.parse_args()

    JOB_START   = time.time()
    parquet_dir = Path(args.parquet_dir)
    output_dir  = Path(args.output_dir)

    # ── Initialise MPI ────────────────────────────────────────────────────
    # Import at module level triggers MPI_Init via mpi4py.
    # We check size > 1 explicitly — conda-forge OpenMPI launched via srun
    # silently gives size=1 (singleton).  mpirun gives the correct size.
    try:
        from mpi4py import MPI
        comm          = MPI.COMM_WORLD
        rank          = comm.Get_rank()
        size          = comm.Get_size()
        mpi_available = size > 1          # False if singleton / srun mis-launch
    except ImportError:
        rank = 0; size = 1; mpi_available = False; comm = None

    # Only rank 0 creates the output directory to avoid races
    if rank == 0:
        output_dir.mkdir(parents=True, exist_ok=True)
    if mpi_available:
        comm.Barrier()   # all ranks wait until dir exists

    if rank == 0:
        log("INIT", "=" * 60, JOB_START, rank)
        if mpi_available:
            log("INIT",
                f"PCMCIplus — MPI mode  ranks={size}  workers={size - 1}",
                JOB_START, rank)
        else:
            log("INIT",
                "PCMCIplus — sequential mode (MPI not available or size=1)",
                JOB_START, rank)
        for k, v in vars(args).items():
            log("INIT", f"  {k:<25s}: {v}", JOB_START, rank)
        log("INIT", "=" * 60, JOB_START, rank)
        log("INIT",
            f"Variable groups: {len(VARIABLE_GROUPS)}  total vars: {N_VARS}",
            JOB_START, rank)

    node_dirs = sorted(parquet_dir.glob("node=frontier*"))
    if not node_dirs:
        raise FileNotFoundError(f"No node=frontier* in {parquet_dir}")

    groups       = build_groups(node_dirs, args.group_size,
                                args.cross_group_fraction)
    total_groups = len(groups)

    if rank == 0:
        log("INIT", f"Node dirs:     {len(node_dirs):,}", JOB_START, rank)
        log("INIT", f"Total groups:  {total_groups}", JOB_START, rank)

    # ── Aggregate-only mode ───────────────────────────────────────────────
    if args.aggregate_only:
        if rank == 0:
            group_jsons = sorted(output_dir.glob("group_*.json"))
            log("AGGREGATE",
                f"Found {len(group_jsons)} / {total_groups} result files",
                JOB_START, rank)
            if group_jsons:
                aggregate_results(group_jsons, output_dir, args.pc_alpha,
                                  JOB_START, rank)
            log("DONE", f"Wall={time.time() - JOB_START:.1f}s",
                JOB_START, rank)
        return

    # ── MPI parallel mode ─────────────────────────────────────────────────
    if mpi_available:
        if rank == 0:
            run_coordinator(comm, groups, output_dir, JOB_START)
            group_jsons = sorted(output_dir.glob("group_*.json"))
            log("AGGREGATE",
                f"Inline aggregation: {len(group_jsons)}/{total_groups} files",
                JOB_START, rank)
            if group_jsons:
                aggregate_results(group_jsons, output_dir, args.pc_alpha,
                                  JOB_START, rank)
        else:
            run_worker(comm, groups, args, output_dir, JOB_START, rank)

    # ── Sequential fallback ───────────────────────────────────────────────
    else:
        for idx, group in enumerate(groups):
            run_pcmciplus_group(
                group              = group,
                count_cap          = args.count_cap,
                tau_max            = args.tau_max,
                pc_alpha           = args.pc_alpha,
                output_dir         = output_dir,
                n_cpus             = args.cpus_per_task,
                job_start          = JOB_START,
                group_num          = idx + 1,
                total_groups       = total_groups,
                target_rows        = args.target_rows,
                window_size        = args.window_size,
                rare_threshold     = args.rare_threshold,
                max_conds_dim      = args.max_conds_dim,
                heartbeat_interval = args.heartbeat_interval,
                rank               = 0,
            )

    if rank == 0:
        log("DONE", "=" * 60, JOB_START, rank)
        log("DONE", f"Wall={time.time() - JOB_START:.1f}s", JOB_START, rank)
        log("DONE", "=" * 60, JOB_START, rank)


if __name__ == "__main__":
    main()