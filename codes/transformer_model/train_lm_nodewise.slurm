#!/bin/bash
#SBATCH -A stf218
#SBATCH -J train_lm_nodewise_cap50
#SBATCH -o logs/seq_lm_node%j.out
#SBATCH -e logs/seq_lm_node%j.err
#SBATCH -N 5645
#SBATCH -t 12:00:00
#SBATCH --exclude=frontier09211
# #SBATCH -q debug


CACHE_DIR="/lustre/orion/scratch/25amk/stf218/gnn_project/cached_data_global_sorted_v2"
OUTPUT_DIR="/lustre/orion/scratch/25amk/stf218/logs_llm/backup_vllm_inference/git/syslog_rca/causal/code/gnn/outputs_sequential_lm_184n_node_v4_cap10_fixedmask"
CODE_DIR="/lustre/orion/stf218/scratch/25amk/logs_llm/backup_vllm_inference/git/syslog_rca/causal/code/gnn/train_lm"

BATCH_SIZE=16
EPOCHS=50
D_MODEL=512
NUM_LAYERS=6
NUM_HEADS=8
SEQ_LEN=2048
STRIDE=1024
LR=0.0004
WARMUP_STEPS=3000

mkdir -p $OUTPUT_DIR
mkdir -p logs

module load rocm/6.4.2
module load craype-accel-amd-gfx90a
source /lustre/orion/stf218/scratch/25amk/logs_llm/backup_vllm_inference/venv_rca/bin/activate

# export ROCR_VISIBLE_DEVICES=$SLURM_LOCALID

export MIOPEN_USER_DB_PATH=/tmp/${USER}-miopen-cache-${SLURM_JOB_ID}
export MIOPEN_CUSTOM_CACHE_DIR=${MIOPEN_USER_DB_PATH}
rm -rf ${MIOPEN_USER_DB_PATH}
mkdir -p ${MIOPEN_USER_DB_PATH}

export NCCL_DEBUG=INFO
export NCCL_NET_GDR_LEVEL=3
export NCCL_CROSS_NIC=1
export NCCL_IB_TIMEOUT=50
export NCCL_SOCKET_IFNAME=hsn
export NCCL_BUFFSIZE=8388608
export TORCH_NCCL_ASYNC_ERROR_HANDLING=1

cd $CODE_DIR

MASK_0="0x00000000000000fe"
MASK_1="0x000000000000fe00"
MASK_2="0x0000000000fe0000"
MASK_3="0x00000000fe000000"
MASK_4="0x000000fe00000000"
MASK_5="0x0000fe0000000000"
MASK_6="0x00fe000000000000"
MASK_7="0xfe00000000000000"

echo "========================================"
echo " 184 NODES RUN"
echo "========================================"
echo "Job ID: $SLURM_JOB_ID"
echo "Nodes: $SLURM_NNODES"
echo "GPUs: $((SLURM_NNODES * 8))"
echo "========================================"

# Verify caches
for split in train val; do
    if [ ! -f "$CACHE_DIR/${split}_node_ts_sorted_tokens.npy" ]; then
        echo "ERROR: ${split} cache not found!"
        exit 1
    fi
done
echo "✓ Caches OK"

# Set distributed variables
export MASTER_ADDR=$(scontrol show hostnames $SLURM_JOB_NODELIST | head -n 1)
export MASTER_PORT=29500

echo "Distributed:"
echo "  MASTER_ADDR: $MASTER_ADDR"
echo "  MASTER_PORT: $MASTER_PORT"
echo ""

echo "Starting training..."
echo ""

# ✅ FIXED GPU BINDING
srun -N ${SLURM_NNODES} \
     -n $((SLURM_NNODES * 8)) \
     --ntasks-per-node=8 \
     --gpus-per-node=8 \
     --gpu-bind=map_gpu:0,1,2,3,4,5,6,7 \
     --cpus-per-task=7 \
     --cpu-bind=mask_cpu:${MASK_0},${MASK_1},${MASK_2},${MASK_3},${MASK_4},${MASK_5},${MASK_6},${MASK_7} \
     python train_lm_nodewise.py \
       --cache_dir $CACHE_DIR \
       --output_dir $OUTPUT_DIR \
       --batch_size $BATCH_SIZE \
       --epochs $EPOCHS \
       --d_model $D_MODEL \
       --num_layers $NUM_LAYERS \
       --num_heads $NUM_HEADS \
       --seq_len $SEQ_LEN \
       --stride $STRIDE \
       --lr $LR \
       --warmup_steps $WARMUP_STEPS \
       --sort_type node \
       --max_per_event 10 \
       --event_weights /lustre/orion/stf218/scratch/25amk/logs_llm/backup_vllm_inference/git/syslog_rca/causal/code/gnn/train_lm/event_weights.npy \
       --auto_resume
    
EXIT_CODE=$?

echo ""
echo "========================================"
if [ $EXIT_CODE -eq 0 ]; then
    echo "✓✓✓ TEST PASSED! ✓✓✓"
else
    echo "✗ FAILED: $EXIT_CODE"
fi
echo "========================================"

rm -rf ${MIOPEN_USER_DB_PATH}