# Job Scheduling

Slurm configuration, allocation policies, and scheduling behavior for the Frontier supercomputer at OLCF.

## Slurm Configuration

Frontier uses the **Slurm Workload Manager** for job scheduling and resource allocation. OLCF updated to **Slurm 24.05** on August 20, 2024.

### Core Configuration

- **Total compute nodes**: 9,408 (with 9,472 maximum allocatable in scheduling system)
- **Allocatable cores per node**: 56 (out of 64 physical cores)
- **Core specialization**: Frontier reserves the first core in each L3 cache region using the `-S 8` flag by default
- **GPUs per node**: 8 GCDs (4 AMD MI250X with 2 GCDs each)
- **HBM per GCD**: 64 GB

Users can override core specialization with `-S 0` to access all 64 cores, though this is not recommended for most workloads.

### Slurm Environment Variables

Useful environment variables available within running jobs:

| Variable | Description |
|----------|-------------|
| `$SLURM_SUBMIT_DIR` | Directory from which the batch job was submitted |
| `$SLURM_JOBID` | Job's full identifier (useful for output file naming) |
| `$SLURM_JOB_NUM_NODES` | Number of nodes requested |
| `$SLURM_JOB_NAME` | Job name supplied by the user |
| `$SLURM_NODELIST` | List of nodes assigned to the job |

## Job Partitions

Frontier provides multiple partitions to accommodate different job types and priorities.

### Batch Partition (Default)

The **batch** partition is the default partition for production work on Frontier. Most work is handled through this partition.

**Policies:**
- Limit of **four eligible-to-run jobs** per user
- Maximum of **100 jobs queued** across all partitions per user (jobs in all states)
- Additional jobs beyond this limit are rejected at submit time

### Extended Partition

The **extended** partition allows longer-running jobs with smaller node counts.

**Policies:**
- **24-hour maximum walltime** for each queued job
- **64-node maximum** job size
- One running job plus one eligible-to-run job per user

### Debug QOS

The **debug** quality of service (QOS) provides higher priority access for short, non-production debug tasks.

**Policies:**
- Higher priority than jobs of the same size bin in production partitions
- **2-hour maximum walltime** (longer requests are rejected)
- **One job maximum** per user in any state
- Production work and job chaining prohibited

**Usage:**
```bash
#SBATCH -q debug
# or
sbatch -q debug script.slurm
```

