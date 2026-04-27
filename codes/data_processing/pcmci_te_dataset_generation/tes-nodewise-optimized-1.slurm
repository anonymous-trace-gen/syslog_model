#!/bin/bash
#SBATCH -A stf008
#SBATCH -p batch
#SBATCH -J pcmci_bins_v2
#SBATCH -N 128
#SBATCH -t 02:30:00
#SBATCH --output=pcmci_spark.%j.out
#SBATCH --error=pcmci_spark.%j.err

echo "=========================================="
echo "FRONTIER SPARK STANDALONE - PCMCI v2"
echo "=========================================="

module load miniforge3/23.11.0-0
conda activate ../conda_env
PYTHON_EXEC=$(which python3)
python3 --version

export SPARK_HOME=/lustre/orion/proj-shared/gen150/gen150_sys/python_venv/spark-3.5.7-bin-hadoop3
export PATH=$SPARK_HOME/bin:$PATH
export PYTHONPATH=$SPARK_HOME/python:$SPARK_HOME/python/lib/py4j-*.zip:$PYTHONPATH
export PYSPARK_DRIVER_PYTHON=$PYTHON_EXEC
export PYSPARK_PYTHON=$PYTHON_EXEC

export SPARK_LOCAL_DIRS=/lustre/orion/gen150/proj-shared/alz/node-wise/spark-local-dir/$SLURM_JOB_ID
mkdir -p $SPARK_LOCAL_DIRS
export SPARK_LOG_DIR=$SPARK_LOCAL_DIRS/spark-logs
mkdir -p $SPARK_LOG_DIR

# Scratch dir for Phase 1 filtered Parquet (on Lustre so all nodes can read it)
SCRATCH_DIR=/lustre/orion/gen150/proj-shared/alz/node-wise/scratch/$SLURM_JOB_ID
mkdir -p $SCRATCH_DIR

NODES=($(scontrol show hostnames $SLURM_JOB_NODELIST))
MASTER_NODE=${NODES[0]}
MASTER_URL="spark://$MASTER_NODE:7077"
NUM_NODES=${#NODES[@]}
WORKER_NODES=${NODES[@]:1}   # all except master

echo "Allocated nodes: $NUM_NODES"
echo "Master: $MASTER_NODE"

cleanup() {
  echo "Cleaning up Spark..."
  ssh $MASTER_NODE "$SPARK_HOME/sbin/stop-all.sh" 2>/dev/null || true
  rm -rf $SPARK_LOCAL_DIRS $SCRATCH_DIR
}
trap cleanup EXIT

# ── Frontier node sizing ──────────────────────────────────────────────────
# Each Frontier node: 64 AMD EPYC cores, 512 GB RAM
# Leave 1 core + 8 GB for the OS / Spark daemon overhead.
# 3 executors × (20 cores + 150 GB) = 60 cores, 450 GB used per node.
# This gives each core ~7.5 GB — good for shuffle-heavy pivot workloads.
CORES_PER_EXEC=20
MEM_PER_EXEC="150G"
EXEC_PER_NODE=3
# Total executors across workers (255 workers × 3)
TOTAL_EXEC=$(( (NUM_NODES - 1) * EXEC_PER_NODE ))
echo "Total executors: $TOTAL_EXEC  (${CORES_PER_EXEC} cores × ${MEM_PER_EXEC} each)"

# ── Start Spark master ────────────────────────────────────────────────────
ssh $MASTER_NODE \
  "export SPARK_HOME=$SPARK_HOME; export SPARK_LOCAL_DIRS=$SPARK_LOCAL_DIRS; \
   $SPARK_HOME/sbin/start-master.sh" &
sleep 10

# ── Start workers on every non-master node ────────────────────────────────
for NODE in "${NODES[@]:1}"; do
  ssh $NODE \
    "export SPARK_HOME=$SPARK_HOME; export SPARK_LOCAL_DIRS=$SPARK_LOCAL_DIRS; \
     $SPARK_HOME/sbin/start-worker.sh \
       --cores $(( CORES_PER_EXEC * EXEC_PER_NODE )) \
       --memory $(( 150 * EXEC_PER_NODE ))G \
       $MASTER_URL" &
done
wait
sleep 15

# ── Inputs ────────────────────────────────────────────────────────────────
BASE_DIR=/lustre/orion/proj-shared/gen150/gen150_sys/data/sorted_data_nodewise
SPLIT=train
OUTPUT_DIR=/lustre/orion/gen150/proj-shared/alz/node-wise/pcmciplus-full-dataset
INTERVAL=5
SHUFFLE_PARTS=12288      # ~2× total executor cores for large shuffles
CHUNK_SIZE=100000000     # 100 M rows/chunk on driver (3 arrays × 100M × 8B = 2.4 GB)

spark-submit \
  --master $MASTER_URL \
  --driver-memory 256G \
  --num-executors $TOTAL_EXEC \
  --executor-cores $CORES_PER_EXEC \
  --executor-memory $MEM_PER_EXEC \
  --conf spark.sql.shuffle.partitions=$SHUFFLE_PARTS \
  --conf spark.sql.adaptive.enabled=true \
  --conf spark.sql.adaptive.coalescePartitions.enabled=true \
  --conf spark.sql.adaptive.skewJoin.enabled=true \
  --conf spark.sql.autoBroadcastJoinThreshold=268435456 \
  --conf spark.executor.memoryOverhead=8g \
  --conf spark.network.timeout=800s \
  --conf spark.executor.heartbeatInterval=60s \
  --conf spark.storage.memoryFraction=0.3 \
  --conf spark.shuffle.memoryFraction=0.5 \
  tep-nodewise-optimized-1.py \
    --base_dir    "$BASE_DIR" \
    --split       "$SPLIT" \
    --output      "$OUTPUT_DIR" \
    --scratch_dir "$SCRATCH_DIR" \
    --interval_sec    "$INTERVAL" \
    --chunk_size      "$CHUNK_SIZE" \
    --shuffle_partitions "$SHUFFLE_PARTS"

echo "Done."