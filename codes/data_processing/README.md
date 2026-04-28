# data_processing

Three sequential preprocessing stages that convert raw Frontier syslog parquet files into the caches used by the transformer, transfer entropy, and PCMCI+ pipelines.

---

## Stage 1 — `preprocess_dataset_event_generation/`

**Log parsing: raw syslogs → tokenized parquet**

Reads raw syslog parquet files and classifies each log line into one of 87 event types using a regex pattern database with two priority tiers:

- **Priority 1** — architecture-aware MCE bank decoding and critical hardware patterns (Slingshot CXI, AMD GPU, MCE/PCIe, storage, OS/kernel)
- **Priority 2** — broader catch-all patterns for service, application, and context events

MCE events are further decoded by hardware bank number to distinguish CPU core, fabric, memory DIMM, PCIe hub, fabric router, and GPU link errors.

Runs on a Spark standalone cluster across 64 nodes (128 executors, 80GB each). Processes all 4 batches sequentially in a single job.

```bash
sbatch log_parsing_regex_patterns_based_2.slurm
```

**Output:** per-batch parsed parquet files with `event_token` column added.

---

## Stage 2 — `transformer_model_data_generation/`

**Cache builder: parsed data → input arrays for the transformer**

Reads the Stage 1 parsed parquet files, tokenizes `event_token` strings to integer indices using the 87-event vocabulary, sorts all events globally by `[node_name, timestamp]`, verifies sort correctness, then writes memory-mapped numpy arrays:

- `{split}_node_ts_sorted_tokens.npy` — int64 token IDs
- `{split}_node_ts_sorted_timestamps.npy` — datetime64[ns] timestamps
- `{split}_node_ts_sorted_nodes.npy` — int32 encoded node IDs
- `{split}_node_name_map.pkl` — node integer ↔ name mapping
- `{split}_node_ts_metadata.pkl` — event count, time range, node count



```bash
sbatch build_cache_with_checkpoint_node_time_parallel_nosplit.slurm
```

---

## Stage 3 — `pcmci_te_dataset_generation/`

**Node-wise binning: parsed parquet → node-partitioned parquet for PCMCI+ and TE**

Bins events into 5-second windows per node and writes `node={name}/data.parquet` with float32 event counts for all 87 types. Uses a synthetic monotonic timeline (seconds) to avoid int64 overflow on nanosecond timestamps. Inserts a separator row (`is_separator=True`, counts=NaN) after each node's data so downstream tools (Tigramite, transfer entropy) treat consecutive rows from different nodes as non-adjacent.



```bash
sbatch tes-nodewise-optimized-1-phase2.slurm
```
