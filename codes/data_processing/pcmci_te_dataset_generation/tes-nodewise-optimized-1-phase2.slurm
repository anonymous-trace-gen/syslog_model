#!/bin/bash
#SBATCH -A 
#SBATCH -p batch
#SBATCH -J pcmci_parallel
#SBATCH -N 32
#SBATCH -t 02:00:00
#SBATCH --output=pcmci_parallel.%j.out
#SBATCH --error=pcmci_parallel.%j.err


module load miniforge3/23.11.0-0
conda activate ../conda_env
PYTHON_EXEC=$(which python3)
python3 --version

export SPARK_HOME=./python_venv/spark-3.5.7-bin-hadoop3
export PATH=$SPARK_HOME/bin:$PATH
export PYTHONPATH=$SPARK_HOME/python:$SPARK_HOME/python/lib/py4j-*.zip:$PYTHONPATH
export PYSPARK_DRIVER_PYTHON=$PYTHON_EXEC
export PYSPARK_PYTHON=$PYTHON_EXEC

export SPARK_LOCAL_DIRS=./alz/node-wise/spark-local-dir/$SLURM_JOB_ID
mkdir -p $SPARK_LOCAL_DIRS
export SPARK_LOG_DIR=$SPARK_LOCAL_DIRS/spark-logs
mkdir -p $SPARK_LOG_DIR

NODES=($(scontrol show hostnames $SLURM_JOB_NODELIST))
MASTER_NODE=${NODES[0]}
MASTER_URL="spark://$MASTER_NODE:7077"
NUM_NODES=${#NODES[@]}
echo "Nodes: $NUM_NODES  Master: $MASTER_NODE"

cleanup() {
  ssh $MASTER_NODE "$SPARK_HOME/sbin/stop-all.sh" 2>/dev/null || true
  rm -rf $SPARK_LOCAL_DIRS
}
trap cleanup EXIT


CORES_PER_EXEC=56
MEM_PER_EXEC="480G"
EXEC_PER_NODE=1
TOTAL_EXEC=$(( (NUM_NODES - 1) * EXEC_PER_NODE ))

PARALLELISM=$(( TOTAL_EXEC * CORES_PER_EXEC ))
echo "Total executors : $TOTAL_EXEC"
echo "Parallelism     : $PARALLELISM"

ssh $MASTER_NODE \
  "export SPARK_HOME=$SPARK_HOME; export SPARK_LOCAL_DIRS=$SPARK_LOCAL_DIRS; \
   $SPARK_HOME/sbin/start-master.sh" &
sleep 10

for NODE in "${NODES[@]:1}"; do
  ssh $NODE \
    "export SPARK_HOME=$SPARK_HOME; export SPARK_LOCAL_DIRS=$SPARK_LOCAL_DIRS; \
     $SPARK_HOME/sbin/start-worker.sh \
       --cores $CORES_PER_EXEC --memory $MEM_PER_EXEC \
       $MASTER_URL" &
done
wait; sleep 15

PHASE1_PARQUET=./alz/node-wise/scratch/4301404/filtered_parquet
OUTPUT_DIR=./alz/node-wise/pcmciplus-full-dataset
MANIFEST=$OUTPUT_DIR/node_manifest.json
LEDGER=$OUTPUT_DIR/progress.json

echo "Input   : $PHASE1_PARQUET"
echo "Output  : $OUTPUT_DIR"
echo "Manifest: $MANIFEST"
echo "Ledger  : $LEDGER"

SKIP_PASS1=""
if [ -f "$MANIFEST" ]; then
  SKIP_PASS1="--skip_pass1"
  echo "Manifest exists – skipping Pass 1"
fi

spark-submit \
  --master $MASTER_URL \
  --driver-memory 32G \
  --num-executors $TOTAL_EXEC \
  --executor-cores $CORES_PER_EXEC \
  --executor-memory $MEM_PER_EXEC \
  --conf spark.executor.memoryOverhead=16g \
  --conf spark.network.timeout=800s \
  --conf spark.executor.heartbeatInterval=60s \
  --conf spark.sql.adaptive.enabled=true \
  tep-nodewise-optimized-1-phase2.py \
    --phase1_parquet  "$PHASE1_PARQUET" \
    --output          "$OUTPUT_DIR" \
    --manifest_path   "$MANIFEST" \
    --ledger_path     "$LEDGER" \
    --interval_sec    5 \
    --parallelism     "$PARALLELISM" \
    $SKIP_PASS1

echo "Done."