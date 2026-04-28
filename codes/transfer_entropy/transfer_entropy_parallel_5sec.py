#!/usr/bin/env python3
"""
Transfer Entropy for HPC Causal Discovery — Frontier Supercomputer
===================================================================
Multi-scale temporal analysis with three window sizes:
  - 5 seconds:  hardware cascades (MCE, fabric errors)
  - 1 minute:   service propagation (rsyslog, network)
  - 10 minutes: application effects (job cancel, infra fail)

Each SLURM rank handles one cause event across all three windows.
Results saved separately per window for triangulation.

Usage:
  sbatch submit_te.sh
  python3 merge_te_results.py

Author: SC2026 paper
"""

import numpy as np
import pandas as pd
import pickle
import os
import sys
import time
from pathlib import Path
from joblib import Parallel, delayed
import warnings
warnings.filterwarnings('ignore')

try:
    from pyinform import transfer_entropy
except ImportError:
    print("ERROR: pyinform not found.")
    print("Install: pip install pyinform")
    sys.exit(1)

# ── PATHS ─────────────────────────────────────────────────────────────────────
DATA_DIR = Path('/lustre/orion/scratch/25amk/stf218/gnn_project/'
                'cached_data_global_sorted_v2_nosplit')

TOKENS_PATH     = DATA_DIR / 'train_node_ts_sorted_tokens.npy'
TIMESTAMPS_PATH = DATA_DIR / 'train_node_ts_sorted_timestamps.npy'

RESULTS_BASE = Path('/lustre/orion/scratch/25amk/stf218/logs_llm/'
                    'backup_vllm_inference/git/syslog_rca/causal/code/te/tau_10min/'
                    'te_cap10')


# ── WINDOW CONFIGURATIONS ─────────────────────────────────────────────────────
# Three temporal scales capturing different cascade dynamics
WINDOWS = {
    '5s': {
        'ns':         5_000_000_000,          # 5 seconds in nanoseconds
        'label':      '5s',
        'tau_min':    1,                       # 5s
        'tau_max':    120,                     # 30 minutes
        'description': 'Hardware cascades (MCE, fabric errors)',
    },
    '1min': {
        'ns':         60_000_000_000,          # 1 minute in nanoseconds
        'label':      '1min',
        'tau_min':    1,                       # 1 minute
        'tau_max':    10,                    # 2 days
        'description': 'Service propagation (rsyslog, network)',
    },
    '10min': {
        'ns':         600_000_000_000,         # 10 minutes in nanoseconds
        'label':      '10min',
        'tau_min':    1,                       # 10 minutes
        'tau_max':    6,                     # 2 days
        'description': 'Application effects (job cancel, infra fail)',
    },
}

# ── PARAMETERS ────────────────────────────────────────────────────────────────
K_HISTORY     = 3      # embedding history
N_SHUFFLES    = 1000   # permutation test shuffles
ALPHA         = 0.05   # significance (Bonferroni applied per window)
CAP           = 10     # same cap as Transformer
N_EVENTS      = 87
CHUNK         = 50_000_000
VALID_TS_MIN  = np.int64(1_737_331_200_000_000_000)  # Jan 20 2025

IDX_TO_LABEL = {
    0: "NET_CXI_RAW_DATA",  1: "FS_DISK_FULL",       2: "INFO_NOISE",
    3: "NET_CXI_TIMEOUT",   4: "SVC_RSYSLOG_ERR",    5: "NET_CXI_LINK",
    6: "FS_DVS_WARN",       7: "NET_CXI_WARN",       8: "NET_TCP_FAIL",
    9: "HW_PCIE_ERR",      10: "HW_MCE_GENERIC",    11: "NET_CXI_INT_ERR",
   12: "HW_MCE_FATAL",     13: "NET_CXI_HW_ECC",    14: "APP_INFRA_FAIL",
   15: "NET_CXI_SVC",      16: "GPU_MEM_FAULT",     17: "HW_MCE_CORRECTED",
   18: "HW_EDAC_ERR",      19: "FS_CLUSTER_EVICT",  20: "FS_LUSTRE_SLOW",
   21: "SVC_SYSTEMD_START",22: "SVC_CONFIG_ERR",    23: "GPU_SOFT_LOCK",
   24: "HW_FABRIC_RTR",    25: "NET_CONFIG_ERR",    26: "HW_MEM_DIMM",
   27: "SEC_AUTH_FAIL",    28: "GPU_RAS_FAIL",       29: "HW_IOMMU_ERR",
   30: "FS_LUSTRE_OST_ERR",31: "APP_FILE_MISSING",  32: "SYS_KERNEL_CTX",
   33: "FS_LUSTRE_ERR",    34: "GPU_DRIVER_ERR",    35: "FS_XFS_ERR",
   36: "GPU_FIRMWARE",     37: "HW_BMC_WARN",       38: "APP_JOB_CANCEL",
   39: "APP_CFG_ERR",      40: "HW_ACPI_WARN",      41: "APP_JOB_LATENCY",
   42: "NET_CXI_FIRMWARE", 43: "FS_IO_ERR",         44: "NET_CXI_PHY_ERR",
   45: "SVC_SYSTEMD_SPEC", 46: "SYS_OOM_KILL",      47: "APP_JOB_CGROUP",
   48: "HW_IF_GPU_LINK",   49: "FS_GPFS_ERR",       50: "GPU_HARD_FAULT",
   51: "HW_USB_FAIL",      52: "HW_MCE_CPU",        53: "SYS_WATCHDOG",
   54: "NET_CXI_MGMT_ERR", 55: "FS_LUSTRE_MDS_ERR", 56: "SYS_CONFIG_ERR",
   57: "SYS_RCU_STALL",    58: "APP_JOB_ERR",       59: "NET_RPC_ERR",
   60: "NET_LNET_ERR",     61: "GPU_TIMEOUT",        62: "SYS_SEGFAULT",
   63: "SVC_SYSTEMD_TIME", 64: "HW_THERMAL_CRIT",   65: "CTX_LUSTRE",
   66: "HW_MCE_DUMP",      67: "HW_MEM_CORRUPT",    68: "STO_NVME_STALL",
   69: "SVC_SYSTEMD_EXIT", 70: "APP_GITLAB_FAIL",   71: "SVC_SYSTEMD_KILL",
   72: "SYS_KERNEL_PANIC", 73: "CTX_AMDGPU",        74: "SYS_COREDUMP",
   75: "HW_CPU_CORE",      76: "SYS_PROCESS_LIM",   77: "SYS_X11_NOISE",
   78: "SYS_CLOCK_SKEW",   79: "CTX_SCHEDULER",     80: "NET_LNET_WARN",
   81: "HW_PCIE_HUB",      82: "SVC_SYSTEMD_PAM",   83: "CTX_MEMORY",
   84: "CTX_SLINGSHOT",    85: "HW_FABRIC_INT",     86: "HW_MCE_UNK",
}


# ── DATA LOADING ──────────────────────────────────────────────────────────────

def _build_window_ts(window_ns, cache_ts, cache_meta):
    """
    Build event count matrix for a specific window size.
    Aggregates raw events into bins of window_ns nanoseconds.
    Applies cap=10 per bin.
    """
    print(f"  Building time series for window={window_ns//1_000_000_000}s "
          f"({window_ns//1_000_000_000/60:.1f}min)...")

    tokens     = np.load(TOKENS_PATH,     mmap_mode='r')
    timestamps = np.load(TIMESTAMPS_PATH, mmap_mode='r')
    total      = len(tokens)

    # Pass 1: find global time range (filter zero timestamps)
    ts_min = np.iinfo(np.int64).max
    ts_max = np.iinfo(np.int64).min

    for start in range(0, total, CHUNK):
        end   = min(start + CHUNK, total)
        chunk = timestamps[start:end]
        chunk_int = (chunk.view(np.int64)
                     if np.issubdtype(chunk.dtype, np.datetime64)
                     else chunk.astype(np.int64))
        valid_mask = chunk_int > VALID_TS_MIN
        if valid_mask.any():
            ts_min = min(ts_min, int(chunk_int[valid_mask].min()))
            ts_max = max(ts_max, int(chunk_int[valid_mask].max()))

    bin_min = ts_min  // window_ns
    bin_max = ts_max  // window_ns
    n_bins  = int(bin_max - bin_min + 1)
    print(f"  Bins: {n_bins:,} "
          f"({n_bins * window_ns / 1e9 / 86400:.1f} days)")

    # Pass 2: accumulate counts
    ts_counts = np.zeros((n_bins, N_EVENTS), dtype=np.int32)

    for start in range(0, total, CHUNK):
        end   = min(start + CHUNK, total)
        tok   = tokens[start:end].astype(np.int32)
        chunk = timestamps[start:end]
        chunk_int = (chunk.view(np.int64)
                     if np.issubdtype(chunk.dtype, np.datetime64)
                     else chunk.astype(np.int64))

        valid = (
            (chunk_int > VALID_TS_MIN) &
            (tok >= 0) & (tok < N_EVENTS)
        )
        b_idx = ((chunk_int[valid] // window_ns) - bin_min).astype(np.int32)
        tok_v = tok[valid]
        in_range = (b_idx >= 0) & (b_idx < n_bins)
        np.add.at(ts_counts, (b_idx[in_range], tok_v[in_range]), 1)

    # Apply cap=10
    ts_counts = np.clip(ts_counts, 0, CAP).astype(np.int32)
    print(f"  Max after cap={CAP}: {ts_counts.max()} ✓")

    np.save(cache_ts, ts_counts)
    with open(cache_meta, 'wb') as f:
        pickle.dump({
            'n_bins':  n_bins,
            'bin_min': int(bin_min),
            'bin_max': int(bin_max),
            'window_ns': int(window_ns),
        }, f)
    print(f"  Cached → {cache_ts}")
    return ts_counts


def load_window_ts(window_label, window_ns, results_dir, rank):
    """
    Load or build time series for a given window size.
    Rank 0 builds cache, others wait.
    """
    cache_ts   = results_dir / f'ts_cap10_{window_label}.npy'
    cache_meta = results_dir / f'ts_cap10_{window_label}_meta.pkl'
    lock_path  = results_dir / f'ts_cap10_{window_label}.lock'

    if rank == 0:
        if not (cache_ts.exists() and cache_meta.exists()):
            _build_window_ts(window_ns, cache_ts, cache_meta)
        lock_path.touch()
        print(f"Rank 0: {window_label} cache ready")
    else:
        print(f"Rank {rank}: waiting for {window_label} cache...")
        waited = 0
        while not lock_path.exists():
            time.sleep(10)
            waited += 10
            if waited % 60 == 0:
                print(f"Rank {rank}: still waiting for "
                      f"{window_label}... ({waited}s)")

    ts = np.load(cache_ts)
    with open(cache_meta, 'rb') as f:
        meta = pickle.load(f)
    return ts, meta


# ── TRANSFER ENTROPY ──────────────────────────────────────────────────────────

def compute_te_at_lag(x_int, y_int, tau, k=K_HISTORY):
    """TE(X->Y) at lag tau using pyinform."""
    if tau >= len(x_int) - k:
        return 0.0
    x_shifted = x_int[:-tau]
    y_target  = y_int[tau:]
    n = min(len(x_shifted), len(y_target))
    if n <= k:
        return 0.0
    try:
        te = transfer_entropy(
            x_shifted[:n].tolist(),
            y_target[:n].tolist(),
            k=k
        )
        return max(float(te), 0.0)
    except Exception:
        return 0.0


def permutation_test(x_int, y_int, tau, te_obs,
                     n_shuffles=N_SHUFFLES,
                     k=K_HISTORY, seed=42):
    """Permutation test for TE significance."""
    rng  = np.random.default_rng(seed)
    n    = min(len(x_int) - tau, len(y_int) - tau)
    x_sh = x_int[:-tau][:n]
    y_tg = y_int[tau:][:n]

    surrogates = np.zeros(n_shuffles)
    for i in range(n_shuffles):
        x_perm = rng.permutation(x_sh)
        try:
            surrogates[i] = max(float(
                transfer_entropy(
                    x_perm.tolist(), y_tg.tolist(), k=k
                )
            ), 0.0)
        except Exception:
            surrogates[i] = 0.0
    return float(np.mean(surrogates >= te_obs))


def compute_one_pair(cause_idx, effect_idx, x_int,
                     ts, alpha_corrected,
                     tau_min, tau_max):
    """Single (cause, effect) pair — runs in parallel via joblib."""
    y_raw = ts[:, effect_idx]
    if y_raw.max() == 0:
        return None

    y_int = y_raw.astype(np.int32)

    # Find optimal lag within window-specific range
    te_by_lag = {
        tau: compute_te_at_lag(x_int, y_int, tau)
        for tau in range(tau_min, tau_max + 1)
    }
    tau_star = max(te_by_lag, key=te_by_lag.get)
    te_star  = te_by_lag[tau_star]

    if te_star < 1e-8:
        return None

    p_val = permutation_test(
        x_int, y_int, tau_star, te_star,
        n_shuffles=N_SHUFFLES, k=K_HISTORY,
        seed=cause_idx * 1000 + effect_idx
    )

    return {
        'cause_idx':   cause_idx,
        'effect_idx':  effect_idx,
        'cause':       IDX_TO_LABEL[cause_idx],
        'effect':      IDX_TO_LABEL[effect_idx],
        'te':          te_star,
        'p_value':     p_val,
        'tau_star':    tau_star,
        'significant': p_val < alpha_corrected,
    }


def compute_te_for_cause(cause_idx, ts, alpha_corrected,
                          ckpt_path, n_cpus,
                          tau_min, tau_max):
    """
    Compute TE from one cause to all effect events.
    Uses joblib for within-node parallelism.
    Checkpoints after each batch.
    """
    cause_label = IDX_TO_LABEL[cause_idx]
    x_raw = ts[:, cause_idx]

    if x_raw.max() == 0:
        print(f"  Skipping {cause_label} — all zeros")
        return []

    x_int = x_raw.astype(np.int32)

    cols = ['cause_idx','effect_idx','cause','effect',
            'te','p_value','tau_star','significant']

    # Load checkpoint
    if ckpt_path.exists():
        ckpt_df = pd.read_csv(ckpt_path)
        done    = set(ckpt_df['effect_idx'].tolist())
        print(f"  Resuming: {len(done)} pairs done")
    else:
        done = set()

    remaining = [
        idx for idx in range(N_EVENTS)
        if idx != cause_idx and idx not in done
    ]
    print(f"  {cause_label}: {len(remaining)} pairs "
          f"({n_cpus} CPUs, tau={tau_min}-{tau_max})")

    if not remaining:
        return pd.read_csv(ckpt_path).to_dict('records')

    # Parallel computation
    raw = Parallel(n_jobs=n_cpus, verbose=0)(
        delayed(compute_one_pair)(
            cause_idx, effect_idx, x_int,
            ts, alpha_corrected, tau_min, tau_max
        )
        for effect_idx in remaining
    )

    new_results = [r for r in raw if r is not None]

    if new_results:
        new_df = pd.DataFrame(new_results)[cols]
        new_df.to_csv(
            ckpt_path,
            mode='a',
            header=not ckpt_path.exists(),
            index=False
        )

    if ckpt_path.exists():
        all_df = pd.read_csv(ckpt_path)
        n_sig  = all_df['significant'].sum()
        print(f"  {cause_label}: {len(all_df)} pairs, "
              f"{n_sig} significant")
        return all_df.to_dict('records')
    return []


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    rank   = int(os.environ.get(
        'SLURM_PROCID',
        os.environ.get('SLURM_ARRAY_TASK_ID', 0)
    ))
    n_cpus  = int(os.environ.get('SLURM_CPUS_PER_TASK', 32))
    n_nodes = int(os.environ.get('SLURM_NTASKS', 64))

    # All 87 event types
    all_cause_indices = list(range(N_EVENTS))
    n_total           = len(all_cause_indices)

    # Round-robin assignment
    my_causes = [
        all_cause_indices[i]
        for i in range(rank, n_total, n_nodes)
    ]

    if not my_causes:
        print(f"Rank {rank}: no causes assigned, exiting.")
        return

    node_name = os.uname().nodename
    print(f"{'='*60}")
    print(f"Rank {rank} on {node_name}")
    print(f"Causes: {[IDX_TO_LABEL[i] for i in my_causes]}")
    print(f"CPUs: {n_cpus} | k={K_HISTORY} | Shuffles={N_SHUFFLES}")
    print(f"Windows: {list(WINDOWS.keys())}")
    print(f"{'='*60}")

    # Bonferroni per window (same n_pairs for all windows)
    n_pairs         = n_total * (n_total - 1)
    alpha_corrected = ALPHA / n_pairs
    print(f"Bonferroni alpha: {alpha_corrected:.2e} ({n_pairs} pairs)")

    RESULTS_BASE.mkdir(parents=True, exist_ok=True)

    # ── Process each window size ───────────────────────────────────────────
    for win_label, win_cfg in WINDOWS.items():
        print(f"\n{'─'*60}")
        print(f"Window: {win_label} — {win_cfg['description']}")
        print(f"{'─'*60}")

        # Results directory per window
        win_dir = RESULTS_BASE / f'window_{win_label}'
        win_dir.mkdir(parents=True, exist_ok=True)

        # Load time series for this window
        ts, meta = load_window_ts(
            win_label, win_cfg['ns'], RESULTS_BASE, rank
        )
        print(f"  Time series: {ts.shape}")

        # Process each assigned cause event
        for cause_idx in my_causes:
            cause_label = IDX_TO_LABEL[cause_idx]
            print(f"\n  Rank {rank} [{win_label}]: "
                  f"{cause_label} (idx={cause_idx})")

            ckpt_path = win_dir / f'te_cause_{cause_idx:03d}.csv'

            compute_te_for_cause(
                cause_idx, ts, alpha_corrected,
                ckpt_path, n_cpus,
                win_cfg['tau_min'],
                win_cfg['tau_max']
            )

    print(f"\nRank {rank} ALL WINDOWS DONE.")


if __name__ == '__main__':
    main()