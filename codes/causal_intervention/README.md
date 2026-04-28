# causal_intervention

Intervention-based causal analysis using the trained transformer. Measures the Average Treatment Effect (ATE) of each event type by intervening on the model's input sequences and observing changes in predicted probabilities.

## Files

- `nodewise_parallel_run_causal_analysis.py` — main script; each SLURM rank processes a subset of nodes, writes `ate_partial_rank{N}.pkl`, rank 0 merges results
- `nodewise_parallel_run_causal.slurm` — SLURM job script
- `common.py` — shared `LABEL_MAPPING`, `IDX_TO_LABEL`, loss functions, metrics, and distributed setup utilities

## Run

```bash
sbatch nodewise_parallel_run_causal.slurm
```

Expects the trained model checkpoint and numpy caches from `data_processing/`. Checkpointing is Lustre-safe (atomic `.tmp` → rename). On resubmit, each rank resumes from its own partial checkpoint.
