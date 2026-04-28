#!/bin/bash
#SBATCH --job-name=te_causal
#SBATCH --account=stf218
#SBATCH --partition=batch
#SBATCH --nodes=64
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=32
#SBATCH --mem=64G
#SBATCH --time=24:00:00
# 64 nodes × 1 task each
# 87 cause events / 64 nodes = 2 rounds
# Each rank handles ceil(87/64) cause events
#SBATCH --requeue
#SBATCH --open-mode=append
#SBATCH --output=logs_tau_10min/te_%j.out
#SBATCH --error=logs_tau_10min/te_%j.err
 
# ── Environment ───────────────────────────────────────────────────────────────
source /lustre/orion/stf218/scratch/25amk/logs_llm/backup_vllm_inference/venv_rca_andes/bin/activate
PYTHON_EXEC=$(which python3)


# ── Paths ─────────────────────────────────────────────────────────────────────
SCRIPT=/lustre/orion/scratch/25amk/stf218/logs_llm/backup_vllm_inference/git/syslog_rca/causal/code/te/tau_10min/transfer_entropy_parallel_5sec.py

LOG_DIR=/lustre/orion/scratch/25amk/stf218/logs_llm/backup_vllm_inference/git/syslog_rca/causal/code/te/tau_10min/logs_5sec
# # ── Paths ─────────────────────────────────────────────────────────────────────
# SCRIPT=/lustre/orion/scratch/25amk/stf218/logs_llm/backup_vllm_inference/git/syslog_rca/causal/code/te/transfer_entropy_parallel_5sec.py
 
# LOG_DIR=/lustre/orion/scratch/25amk/stf218/logs_llm/backup_vllm_inference/git/syslog_rca/causal/code/te/te_causal_analysis_results_nodewise_balanced_cap10/logs
 
mkdir -p ${LOG_DIR}
 
echo "Job ${SLURM_JOB_ID} starting on $(date)"
echo "Nodes: ${SLURM_JOB_NUM_NODES}"
echo "Tasks: ${SLURM_NTASKS}"
echo "CPUs per task: ${SLURM_CPUS_PER_TASK}"
 
# ── Parallelism settings ──────────────────────────────────────────────────────
# Each node uses all 32 CPUs for joblib inner parallelism
export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK}
export OPENBLAS_NUM_THREADS=${SLURM_CPUS_PER_TASK}
export MKL_NUM_THREADS=${SLURM_CPUS_PER_TASK}
export NUMEXPR_NUM_THREADS=${SLURM_CPUS_PER_TASK}
 
# ── Launch ────────────────────────────────────────────────────────────────────
# srun distributes one task per node
# SLURM_PROCID = 0,1,...,63 on each node
# Each rank handles ceil(87/64) = 2 cause events
# Rank 0 → cause events 0, 64
# Rank 1 → cause events 1, 65
# ...
# Rank 22 → cause events 22, 86
# Rank 23-63 → cause events 23-63 only
srun --ntasks=64 \
     --ntasks-per-node=1 \
     --cpus-per-task=${SLURM_CPUS_PER_TASK} \
     python3 ${SCRIPT}
 
echo "Job ${SLURM_JOB_ID} finished on $(date)"