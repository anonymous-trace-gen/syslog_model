#!/bin/bash
#SBATCH -A 
#SBATCH -J causal_nw_analysis
#SBATCH -o logs/causal_nw_%j.out
#SBATCH -e logs/causal_nw_%j.err
#SBATCH -N 16
#SBATCH --ntasks-per-node=8
#SBATCH --gpus-per-node=8
#SBATCH -t 12:00:00

#  Multi-node Parallelized Causal Analysis 


MODEL_PATH="./logs_llm/backup_vllm_inference/git/syslog_rca/causal/code/gnn/outputs_sequential_lm_184n_node_v4_cap10_fixedmask/best_model.pt"

CACHE_DIR="./gnn_project/cached_data_global_sorted_v2"
OUTPUT_DIR="./logs_llm/backup_vllm_inference/git/syslog_rca/causal/code/gnn/causal_analysis_results_nodewise_balanced_cap10_fixedmask"
CODE_DIR="./logs_llm/backup_vllm_inference/git/syslog_rca/causal/code/gnn/causal_intervention"

# Analysis hyperparameters
N_BOOTSTRAP=500          
SIG_THRESHOLD=0.02       
MIN_OCCURRENCES=10       
MAX_CASCADE_DEPTH=5     
CHECKPOINT_EVERY=1      
BATCH_SIZE=64           
SEQ_LEN=204
STRIDE=102
VAL_MAX_SEQ=10000        
MAX_PER_EVENT=10        

# Setup 
mkdir -p "$OUTPUT_DIR"
mkdir -p logs

module load rocm/6.4.2
module load craype-accel-amd-gfx90a
source /lustre/orion/stf218/scratch/25amk/logs_llm/backup_vllm_inference/venv_rca/bin/activate

# Per-job MIOpen cache (per-node, avoids conflicts across nodes)
export MIOPEN_USER_DB_PATH=/tmp/${USER}-miopen-causal-${SLURM_JOB_ID}
export MIOPEN_CUSTOM_CACHE_DIR=${MIOPEN_USER_DB_PATH}
rm -rf "${MIOPEN_USER_DB_PATH}"
mkdir -p "${MIOPEN_USER_DB_PATH}"

# Network settings for Frontier (Slingshot HSN)
export NCCL_NET_GDR_LEVEL=3
export NCCL_SOCKET_IFNAME=hsn
export FI_CXI_ATS=0

echo "  CAUSAL ANALYSIS (SC2026)  —  Multi-node"


if [ ! -f "$MODEL_PATH" ]; then
    echo "ERROR: Model checkpoint not found: $MODEL_PATH"
    exit 1
fi
echo "✓ Model checkpoint found"

for split in train val; do
    if [ ! -f "$CACHE_DIR/${split}_node_ts_sorted_tokens.npy" ]; then
        echo "ERROR: ${split} cache not found in $CACHE_DIR"
        exit 1
    fi
done
echo " Data caches found"

# Check if merge already completed (rank0_done.flag exists)
if [ -f "$OUTPUT_DIR/rank0_done.flag" ]; then
    echo ""
    echo "INFO: rank0_done.flag exists — merge already completed."
    echo "  Delete $OUTPUT_DIR/rank0_done.flag to force a rerun."
    echo "  Or delete all ate_partial_rank*.pkl to start fresh."
    exit 0
fi

cd "$CODE_DIR"
echo ""
echo "Launching $((SLURM_NNODES * 8)) parallel GPU workers..."
echo ""

srun \
    --ntasks-per-node=8 \
    --gpus-per-node=8 \
    --gpu-bind=map_gpu:0,1,2,3,4,5,6,7 \
    --cpus-per-task=7 \
    python nodewise_parallel_run_causal_analysis.py \
        --model_path              "$MODEL_PATH"    \
        --cache_dir               "$CACHE_DIR"     \
        --output_dir              "$OUTPUT_DIR"    \
        --seq_len                 $SEQ_LEN         \
        --stride                  $STRIDE          \
        --batch_size              $BATCH_SIZE       \
        --split                   val              \
        --n_bootstrap             $N_BOOTSTRAP     \
        --significance_threshold  $SIG_THRESHOLD   \
        --min_occurrences         $MIN_OCCURRENCES \
        --max_cascade_depth       $MAX_CASCADE_DEPTH \
        --checkpoint_every        $CHECKPOINT_EVERY  \
        --max_analysis_sequences  $VAL_MAX_SEQ \
        --max_per_event           $MAX_PER_EVENT   \
        
        
# --require_temporal_order

EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    ls -lh "$OUTPUT_DIR"/causal_edges.csv \
           "$OUTPUT_DIR"/transformer_edges_for_triangulation.csv \
           "$OUTPUT_DIR"/cascades.csv \
           "$OUTPUT_DIR"/ate_heatmap.png \
           "$OUTPUT_DIR"/causal_graph.png \
           "$OUTPUT_DIR"/category_summary.png \
           2>/dev/null
    echo ""
    echo "Partial checkpoints:"
    ls -lh "$OUTPUT_DIR"/ate_partial_rank*.pkl 2>/dev/null | wc -l
    echo "  files"
else
    echo "✗ FAILED with exit code: $EXIT_CODE"
    echo ""
    echo "Check per-rank logs:"
    ls "$OUTPUT_DIR"/causal_rank*.log 2>/dev/null | head -5
    echo ""
    echo "Checkpoint progress:"
    for pkl in "$OUTPUT_DIR"/ate_partial_rank*.pkl; do
        [ -f "$pkl" ] || continue
        python3 -c "
import pickle, sys
with open('$pkl','rb') as f: d=pickle.load(f)
pct = d['completed_local_rows']/d['total_local_rows']*100
print(f'  {sys.argv[0].split(\"/\")[-1]}: {d[\"completed_local_rows\"]}/{d[\"total_local_rows\"]} ({pct:.0f}%)')
" "$pkl" 2>/dev/null
    done
fi
echo "==========="

rm -rf "${MIOPEN_USER_DB_PATH}"

