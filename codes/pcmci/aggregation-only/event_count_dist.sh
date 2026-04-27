#!/bin/bash
#SBATCH --job-name=event_count
#SBATCH --account=gen150
#SBATCH --partition=batch
#SBATCH --nodes=32
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=32
#SBATCH --mem=220G
#SBATCH --time=00:30:00
#SBATCH --output=/lustre/orion/gen150/proj-shared/alz/aggregation-only/logs/event_count_%j.out
#SBATCH --error=/lustre/orion/gen150/proj-shared/alz/aggregation-only/logs/event_count_%j.err

PARQUET=/lustre/orion/gen150/proj-shared/alz/node-wise/pcmciplus-full-dataset
OUTPUT=/lustre/orion/gen150/proj-shared/alz/aggregation-only/pcmciplus-results
CONDA_ENV=/lustre/orion/gen150/proj-shared/alz/andes_conda_env
SCRIPT=/lustre/orion/gen150/proj-shared/alz/aggregation-only/event_count_dist.py

echo "================================================"
echo "SLURM_JOB_ID   : $SLURM_JOB_ID"
echo "Nodes          : $SLURM_JOB_NUM_NODES"
echo "Tasks          : $SLURM_NTASKS"
echo "Date           : $(date)"
echo "================================================"

source activate "$CONDA_ENV" 2>/dev/null \
    || conda activate "$CONDA_ENV" 2>/dev/null \
    || source "$CONDA_ENV/bin/activate"

mkdir -p "$OUTPUT" \
    /lustre/orion/gen150/proj-shared/alz/aggregation-only/logs

# Launch one MPI rank per node, each rank uses 32 CPUs internally
srun --ntasks="$SLURM_NTASKS" \
     --ntasks-per-node=1      \
     --cpus-per-task=32       \
     python3 "$SCRIPT"        \
         --parquet_dir "$PARQUET" \
         --output_dir  "$OUTPUT"  \
         --n_workers   32

echo "Done: $(date)"