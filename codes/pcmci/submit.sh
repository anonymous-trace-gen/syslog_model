#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR=./alz/more-nodes-128/logs
OUTPUT_DIR=./alz/more-nodes-128/pcmciplus-results

mkdir -p "$LOG_DIR" "$OUTPUT_DIR"

NODES=${1:-128}   # override: ./submit.sh 64

echo "===="
echo "  PCMCIplus"
echo "  Nodes requested : $NODES"

MPI_JOB_ID=$(sbatch --parsable \
    --nodes="$NODES" \
    "$SCRIPT_DIR/pcmciplus_array.slurm")
[ -z "$MPI_JOB_ID" ] && echo "ERROR: job submission failed." && exit 1
echo "  MPI job : $MPI_JOB_ID  ($NODES nodes, aggregation inline on rank 0)"

# Safety-net aggregation only if the main job fails
AGG_JOB_ID=$(sbatch --parsable \
    --dependency=afternotok:${MPI_JOB_ID} \
    "$SCRIPT_DIR/aggregate.slurm")
echo "  Agg job : $AGG_JOB_ID  (runs if MPI job fails)"

