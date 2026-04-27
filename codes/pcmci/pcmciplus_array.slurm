#!/bin/bash
#SBATCH --job-name=pcmci_mpi
#SBATCH --account=gen150
#SBATCH --partition=batch
#SBATCH --nodes=128                 # 1 coordinator + 127 workers
#SBATCH --ntasks-per-node=1         # 1 MPI rank per node
#SBATCH --cpus-per-task=32          # 32 threads per rank for BLAS/OMP
#SBATCH --mem=220G                  # per-node memory
#SBATCH --time=6:00:00             # 127 workers → ~8-9× faster than 32 nodes
#SBATCH --output=/lustre/orion/gen150/proj-shared/alz/more-nodes-128/logs/pcmci_%j.out
#SBATCH --error=/lustre/orion/gen150/proj-shared/alz/more-nodes-128/logs/pcmci_%j.err

PARQUET=/lustre/orion/gen150/proj-shared/alz/node-wise/pcmciplus-full-dataset
OUTPUT=/lustre/orion/gen150/proj-shared/alz/more-nodes-128/pcmciplus-results
CONDA_ENV=/lustre/orion/gen150/proj-shared/alz/andes_conda_env
SCRIPT=/lustre/orion/gen150/proj-shared/alz/more-nodes-128/pcmciplus_slurm.py

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
    /lustre/orion/gen150/proj-shared/alz/more-nodes-128/logs

# mpirun reads $SLURM_JOB_NODELIST automatically and distributes
# one rank per node.  --bind-to none lets each rank use all 32 CPUs.
# Do NOT use srun here — conda-forge OpenMPI does not integrate with
# SLURM's PMI and will silently fall back to singleton (size=1).
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