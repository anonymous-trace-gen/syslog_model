# data_processing

Preprocessing pipelines that convert raw Frontier syslogs into numpy caches consumed by the transformer and causal analysis pipelines.

## Subdirectories

### `preprocess_dataset_event_generation/`
PySpark job that reads raw syslog parquet files, sorts globally by `[node_name, timestamp]`, tokenizes events using `LABEL_MAPPING` (87 event types), and writes:
- `{split}_node_ts_sorted_tokens.npy`
- `{split}_node_ts_sorted_timestamps.npy`

```bash
sbatch build_cache_with_checkpoint_node_time_parallel_nosplit.slurm
```

### `pcmci_te_dataset_generation/`
Generates node-wise parquet files formatted for PCMCI+ and transfer entropy nalysis ( separator rows between non-consecutive windows).

```bash
sbatch tes-nodewise-optimized-1-phase2.slurm
```
