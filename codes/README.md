# Frontier Syslog Causal Analysis

Research codebase for root cause analysis of the Frontier supercomputer (OLCF) using 18.3 billion system log events.

## Pipelines

**data_processing** — converts raw syslog parquet files into numpy token/timestamp caches using PySpark, sorted by node and timestamp.

**transformer_model** — trains a causal transformer for next-event prediction over HPC event sequences. Runs with PyTorch DDP across 256 AMD MI250X GPUs on Frontier.

**causal_intervention** — uses the trained transformer to measure the Average Treatment Effect (ATE) of each event type, producing a data-driven causal graph.

**transfer_entropy** — computes pairwise transfer entropy between all 87 event types at three temporal scales (5s, 1min, 10min) with permutation significance testing.

**pcmci** — runs PCMCI+ causal discovery over groups of Frontier nodes using Tigramite, distributed via MPI.

**frontier_agent** — Claude Agent SDK CLI that uses the causal results and a structured knowledge base to assess and diagnose Frontier failures interactively.

## Vocabulary

87 HPC event types covering GPU, Slingshot CXI network, Lustre filesystem, hardware (MCE, thermal), system, and application events. Special tokens: PAD=87, UNK=88, MASK=89.
