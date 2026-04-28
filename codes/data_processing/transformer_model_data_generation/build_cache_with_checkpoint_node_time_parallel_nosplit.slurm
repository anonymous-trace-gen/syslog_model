#!/bin/bash
#SBATCH -A 
#SBATCH -p batch
#SBATCH -J build_all_caches
#SBATCH -N 32
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=32
#SBATCH --mem=0
#SBATCH -t 08:00:00
#SBATCH --output=logs/build_all_caches_node_%j.out
#SBATCH --error=logs/build_all_caches_node_%j.err
#SBATCH --exclude=andes405

# Build train, val, and test caches automatically
# No interactive prompts!

DATA_PATH="./data/data_dir"
CACHE_DIR="./cached_data_global_sorted_v2_nosplit"
CODE_DIR="./logs_llm/backup_vllm_inference/git/syslog_rca/causal/code/gnn/revised_code"

cd "$CODE_DIR"
source ./logs_llm/backup_vllm_inference/venv_rca_andes/bin/activate

PYTHON_EXEC=$(which python3)

# Spark Setup
export SPARK_HOME=./logs_llm/spark-3.5.7-bin-hadoop3
export PATH=$SPARK_HOME/bin:$PATH
export SPARK_LOCAL_DIRS=./logs_llm/andes_spark_scratch/$SLURM_JOB_ID
mkdir -p $SPARK_LOCAL_DIRS



# Start Spark Cluster
NODES=($(scontrol show hostnames $SLURM_JOB_NODELIST))
MASTER_NODE=${NODES[0]}

echo "Starting Spark master on $MASTER_NODE..."
ssh $MASTER_NODE "$SPARK_HOME/sbin/start-master.sh" &
sleep 10

MASTER_URL="spark://$MASTER_NODE:7077"
echo "Master URL: $MASTER_URL"

echo "Starting workers on ${#NODES[@]} nodes..."
for NODE in "${NODES[@]}"; do
    ssh $NODE "$SPARK_HOME/sbin/start-worker.sh $MASTER_URL" &
done
wait
sleep 15



# Function to build cache for a split
build_split() {
    local SPLIT=$1
    
    
    spark-submit \
        --master $MASTER_URL \
        --executor-memory 200G \
        --driver-memory 50G \
        --executor-cores 32 \
        --num-executors 32 \
        --conf spark.task.cpus=1 \
        --conf spark.default.parallelism=4096 \
        --conf spark.sql.shuffle.partitions=4096 \
        --conf spark.executor.memoryOverhead=16G \
        --conf spark.pyspark.python=$PYTHON_EXEC \
        --conf spark.pyspark.driver.python=$PYTHON_EXEC \
        --conf spark.network.timeout=600s \
        --conf spark.executor.heartbeatInterval=60s \
        --conf spark.sql.adaptive.enabled=true \
        build_cache_with_checkpoint_node_time_parallel_nosplit.py \
            --data_path "$DATA_PATH" \
            --cache_dir "$CACHE_DIR" \
            --split $SPLIT
    
    local EXIT_CODE=$?
    
    
    if [ $EXIT_CODE -eq 0 ]; then
        echo "$SPLIT split complete!"
        
        ls -lh "$CACHE_DIR"/${SPLIT}_*.npy 2>/dev/null || echo "  (No files found - check errors)"
        
    else
        return $EXIT_CODE
    fi
    
    return $EXIT_CODE
}

# Build all three splits
OVERALL_SUCCESS=0

# Check if train already exists 
if [ -f "$CACHE_DIR/train_node_ts_sorted_tokens.npy" ]; then
    echo "TRAIN cache already exists"
    ls -lh "$CACHE_DIR"/train_*.npy
else
    build_split "train"
    if [ $? -ne 0 ]; then
        OVERALL_SUCCESS=1
    fi
fi


# Summary
echo "Cache files in $CACHE_DIR:"
ls -lh "$CACHE_DIR"/*.npy 2>/dev/null | grep -E "(train|val|test)_global_sorted"
echo ""

# Verify all splits exist
echo "Verification:"
for split in train; do
    TOKEN_FILE="$CACHE_DIR/${split}_global_sorted_tokens.npy"
    TS_FILE="$CACHE_DIR/${split}_global_sorted_timestamps.npy"
    
    if [ -f "$TOKEN_FILE" ] && [ -f "$TS_FILE" ]; then
        echo "  ✓ $split: COMPLETE"
    else
        echo "  ✗ $split: MISSING"
        OVERALL_SUCCESS=1
    fi
done


# Cleanup
echo ""
echo "Stopping Spark cluster..."
ssh $MASTER_NODE "$SPARK_HOME/sbin/stop-all.sh" 2>/dev/null
rm -rf $SPARK_LOCAL_DIRS


exit $OVERALL_SUCCESS