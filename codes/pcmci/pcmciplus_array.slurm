#!/bin/bash
#SBATCH --job-name=pcmci_mpi
#SBATCH --account=
#SBATCH --partition=batch
#SBATCH --nodes=32           
#SBATCH --ntasks-per-node=1   
#SBATCH --cpus-per-task=32    
#SBATCH --mem=220G            
#SBATCH --time=6:00:00        
#SBATCH --output=./alz/mnodes/logs/pcmci_%j.out
#SBATCH --error=./alz/mnodes/logs/pcmci_%j.err

PARQUET=./alz/node-wise/pcmciplus-full-dataset
OUTPUT=./alz/mnodes/pcmciplus-results
CONDA_ENV=./alz/andes_conda_env
SCRIPT=./alz/mnodes/pcmciplus_slurm.py

echo "================================================"
echo "SLURM_JOB_ID   : $SLURM_JOB_ID"
echo "Nodes          : $SLURM_JOB_NUM_NODES"
echo "Tasks          : $SLURM_NTASKS"
echo "Host (rank 0)  : $(hostname)"
echo "Date           : $(date)"
echo "================================================"

source activate "$CONDA_ENV" 2>/dev/null \
    || conda activate "$CONDA_ENV" 2>/dev/null \
    || source "$CONDA_ENV/bin/activate"

mkdir -p "$OUTPUT" \
    ./alz/mnodes/logs


mpirun -np "$SLURM_NTASKS" \
       --map-by node \
       --bind-to none \
       python3 "$SCRIPT"               \
           --parquet_dir    "$PARQUET" \
           --output_dir     "$OUTPUT"  \
           --group_size     8          \
           --tau_max        3          \
           --pc_alpha       0.01       \
           --count_cap      10         \
           --cpus_per_task  32         \
           --target_rows    1000       \
           --window_size    500        \
           --rare_threshold 0.00001    \
           --max_conds_dim  3          \
           --heartbeat_interval 30

echo "Job done: $(date)"