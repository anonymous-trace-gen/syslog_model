# transformer_model

Causal  transformer for next-event prediction over Frontier HPC syslog sequences.The output is used by causal intervention to build causal links. Trained with DDP across 32 nodes (256 AMD MI250X GPUs).

## Files

- `model.py` — `SequentialFailureTransformer`: token + position + `HybridTimeEncoder` embeddings, pre-norm TransformerEncoder with causal mask
- `time_encoding.py` — `HybridTimeEncoder`: 1510 fine-grained time baskets (1ms → 365+ days) combined with a log-scaled continuous encoder
- `dataset_nodewise_cap.py` — `GloballySortedSequentialDataset`: memory-mapped numpy arrays, sliding window (seq_len=2048, stride=1024), per-window event cap to suppress bursty events
- `train_lm_nodewise.py` — training script with checkpointing and `--auto_resume`
- `train_lm_nodewise.slurm` — SLURM job script (ROCm, NCCL, CPU-binding masks)

## Run training

```bash
sbatch train_lm_nodewise.slurm
```

Expects numpy caches at `CACHE_DIR` (`{split}_node_ts_sorted_tokens.npy`, `{split}_node_ts_sorted_timestamps.npy`). The slurm script verifies these before launching.
