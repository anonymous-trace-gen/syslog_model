#!/bin/bash
#SBATCH --job-name=pcmci_agg
#SBATCH --account=
#SBATCH --partition=batch
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=00:30:00
#SBATCH --output=./alz/aggregation-only/logs/pcmci_agg_%j.out
#SBATCH --error=./alz/aggregation-only/logs/pcmci_agg_%j.err

PARQUET=./alz/node-wise/pcmciplus-full-dataset
OUTPUT=./alz/aggregation-only/pcmciplus-results
CONDA_ENV=./alz/andes_conda_env
SCRIPT=./alz/aggregation-only/pcmci_single_mpi.py

source activate "$CONDA_ENV" 2>/dev/null \
    || conda activate "$CONDA_ENV" 2>/dev/null \
    || source "$CONDA_ENV/bin/activate"

echo "Aggregating from $OUTPUT"
echo "Date: $(date)"

python3 "$SCRIPT"                  \
    --parquet_dir  "$PARQUET"      \
    --output_dir   "$OUTPUT"       \
    --aggregate_only               \
    --pc_alpha        0.01         \
    --min_t_data      200          \
    --min_group_votes 2            \
    --no_vote_weighted

echo "Aggregation done: $(date)"