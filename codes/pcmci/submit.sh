#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR=/lustre/orion/gen150/proj-shared/alz/more-nodes-128/logs
OUTPUT_DIR=/lustre/orion/gen150/proj-shared/alz/more-nodes-128/pcmciplus-results

mkdir -p "$LOG_DIR" "$OUTPUT_DIR"

NODES=${1:-128}   # override: ./submit.sh 64

echo "========================================================"
echo "  PCMCIplus — MPI mode  (mpirun launcher)"
echo "  Nodes requested : $NODES"
echo "  Workers         : $((NODES - 1))  (rank 0 = coordinator)"
echo "  Groups          : 1080  (group_size=8)"
echo "  window_size     : 500 rows  (41.7 min per window at 5s/row)"
echo "  target_rows     : 1000 per node"
echo "========================================================"

MPI_JOB_ID=$(sbatch --parsable \
    --nodes="$NODES" \
    "$SCRIPT_DIR/pcmciplus_array.slurm")
[ -z "$MPI_JOB_ID" ] && echo "ERROR: job submission failed." && exit 1
echo "  MPI job : $MPI_JOB_ID  ($NODES nodes, aggregation inline on rank 0)"

# Safety-net aggregation only if the main job fails
AGG_JOB_ID=$(sbatch --parsable \
    --dependency=afternotok:${MPI_JOB_ID} \
    "$SCRIPT_DIR/aggregate.slurm")
echo "  Agg job : $AGG_JOB_ID  (runs ONLY if MPI job fails)"

echo ""
echo "========================================================"
echo "  Monitor:"
echo "    squeue -u \$USER"
echo "    watch -n 60 'squeue -u \$USER'"
echo ""
echo "  Progress (target 1080 files):"
echo "    watch -n 60 'ls $OUTPUT_DIR/group_*.json | wc -l'"
echo ""
echo "  Live log:"
echo "    tail -f $LOG_DIR/pcmci_${MPI_JOB_ID}.out"
echo ""
echo "  Results:"
echo "    $OUTPUT_DIR/causal_graph.json"
echo "    $OUTPUT_DIR/causal_summary.txt"
echo ""
echo "  Resubmit if interrupted (done groups auto-skipped):"
echo "    ./submit.sh $NODES"
echo "========================================================"