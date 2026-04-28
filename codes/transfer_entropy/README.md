# transfer_entropy

Pairwise transfer entropy (TE) between all 87 event types across three temporal scales, using `pyinform` with permutation significance testing.

## Temporal scales

| Window | Captures |
|--------|----------|
| 5s | Hardware cascades (MCE, fabric errors) |
| 1min | Service propagation (rsyslog, network) |
| 10min | Application effects (job cancel, infra fail) |

## Run

```bash
sbatch transfer_entropy_parallel_5sec.slurm
```

Each SLURM rank handles one cause event across all three windows (round-robin assignment). Rank 0 builds the binned time-series cache; other ranks wait on a lock file. Results are written per-cause to `te_cause_{idx:03d}.csv` with checkpointing for resume.

Significance uses Bonferroni-corrected permutation tests (1000 shuffles, α=0.05 / n_pairs).
