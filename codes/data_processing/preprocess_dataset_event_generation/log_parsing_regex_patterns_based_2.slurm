#!/bin/bash
#SBATCH -A 
#SBATCH -p batch
#SBATCH -J parse_5b
#SBATCH -N 64 
#SBATCH -t 24:00:00
#SBATCH --output=log_parse_%j.out
#SBATCH --error=log_parse_%j.err
#SBATCH --exclude=andes405,andes65


source ./logs_llm/backup_vllm_inference/venv_rca_andes/bin/activate
PYTHON_EXEC=$(which python3)

# Spark Setup
export SPARK_HOME=./logs_llm/spark-3.5.7-bin-hadoop3
export PATH=$SPARK_HOME/bin:$PATH
export SPARK_LOCAL_DIRS=./andes_spark_scratch/$SLURM_JOB_ID
mkdir -p $SPARK_LOCAL_DIRS

# Start Cluster
NODES=($(scontrol show hostnames $SLURM_JOB_NODELIST))
MASTER_NODE=${NODES[0]}

ssh $MASTER_NODE "$SPARK_HOME/sbin/start-master.sh" &
sleep 10  
MASTER_URL="spark://$MASTER_NODE:7077"

# Start Workers 
for NODE in "${NODES[@]}"; do
    ssh $NODE "$SPARK_HOME/sbin/start-worker.sh $MASTER_URL" &
done
wait
sleep 15 # Wait for all 64 workers to register

echo "Submitting to $MASTER_URL..."

# we data in 4 batch
for ARG in 1 2 3 4; do
    echo "Starting job with argument: $ARG"
    
    spark-submit \
    --master $MASTER_URL \
    --executor-memory 80G \
    --driver-memory 64G \
    --executor-cores 15 \
    --num-executors 128 \
    --conf spark.task.cpus=1 \
    --conf spark.default.parallelism=50000 \
    --conf spark.sql.shuffle.partitions=8000 \
    --conf spark.executor.memoryOverhead=16G \
    --conf spark.pyspark.python=$PYTHON_EXEC \
    --conf spark.pyspark.driver.python=$PYTHON_EXEC \
    --conf "spark.speculation=true" \
    --conf "spark.network.timeout=300s" \
    log_parsing_regex_patterns_based_2_for_2_slurm.py "$ARG"

    echo "Finished job with argument: $ARG"
done

# Cleanup
ssh $MASTER_NODE "$SPARK_HOME/sbin/stop-all.sh"
rm -rf $SPARK_LOCAL_DIRS
