# pcmci

PCMCI+ causal discovery over Frontier node groups using Tigramite with partial correlation (ParCorr) independence tests.

## Run

```bash
bash submit.sh           # array job submission
sbatch aggregate.slurm   # aggregate group results → causal_graph.json
```

## How it works

1. Nodes are grouped (default 8 per group) and optionally cross-group pairs are added
2. Each group's parquet data is count-capped and downsampled via contiguous-window sampling (preserves rare events)
3. PCMCI+ runs per group; rank 0 (MPI coordinator) dispatches groups to worker ranks
4. Results are aggregated across groups — best (lowest p-value) link per (cause, effect, lag) triple

## aggregation-only/

Standalone scripts for post-hoc aggregation and filtering:
- `causal_summary_to_csv.py` — convert `causal_graph.json` to CSV
- `filter_top_using_event_count_dist.py` — filter edges by event frequency
- `event_count_dist.py` — compute event count distributions
- `pcmci_single_mpi.py` — single-node MPI run for testing
