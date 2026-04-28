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

### Killable Partition

The **killable** partition enables preemptible jobs that can be interrupted during system maintenance.

**Policies:**
- Scheduler stops scheduling killable jobs 1 hour before scheduled outages
- Job limits are shared with the batch queue
- Killed jobs are automatically re-queued after system outage completes

## Time Limits and Job Size Bins

Frontier organizes jobs into **five bins** based on requested node count. Each bin has specific maximum walltime limits and aging parameters that affect priority.

### Job Priority Bins

| Bin | Node Range | Max Walltime | Aging Boost |
|-----|------------|--------------|-------------|
| 1 | 5,645 - 9,472 | 12 hours | +8 days |
| 2 | 1,882 - 5,644 | 12 hours | +4 days |
| 3 | 184 - 1,881 | 12 hours | 0 days |
| 4 | 92 - 183 | 6 hours | 0 days |
| 5 | 1 - 91 | 2 hours | 0 days |

### Bin Interpretation

- **Bins 1-2 (Leadership class)**: Jobs requiring 20%+ of the system receive priority boosts through the aging mechanism
- **Bin 3 (Capability)**: Standard capability jobs with moderate node counts
- **Bins 4-5 (Capacity)**: Smaller jobs with reduced walltime limits

### Leadership Computing Context

In 2024, **54% of cycles** on Frontier consumed 20% or more of the total node count (1,882+ nodes), demonstrating the system's focus on leadership-class computing.

## Scheduling Behavior

### DOE Leadership-Class Job Mandate

Frontier implements scheduling policies that prioritize large-scale computations appropriate for leadership-class systems. The DOE mandate ensures that exascale resources serve their intended purpose of enabling transformational science.

### Priority Mechanism

The basic priority mechanism is **time in queue** (age), with adjustments for:

1. **Job size bin**: Larger jobs receive aging boosts (up to +8 days for largest bin)
2. **Allocation status**: Projects within allocation limits receive priority over those that have overrun
3. **Quality of Service**: Debug QOS jobs receive elevated priority within their size bin

### Backfill Scheduling

Strict FIFO ordering can leave resources idle while waiting for large job resources to accumulate. Frontier uses **backfill scheduling** to:

- Allow smaller, shorter jobs to utilize otherwise idle resources
- Ensure backfilled jobs do not delay the start time of larger queued jobs
- Maximize overall system utilization

### Fair-Share Considerations

Projects that exceed their allocations receive reduced priority:

- Overuse jobs appear "younger" than jobs from projects within allocation limits
- Overuse jobs may face additional walltime restrictions
- Projects remain able to run but at reduced scheduling priority

## Job Submission

### Common sbatch Options

| Option | Purpose | Example |
|--------|---------|---------|
| `-A` | Project to charge | `-A PRJ123` |
| `-N` | Number of nodes | `-N 64` |
| `-t` | Walltime | `-t 02:00:00` |
| `-p` | Partition | `-p batch` (default) |
| `-q` | Quality of Service | `-q debug` |
| `-J` | Job name | `-J my_simulation` |
| `-o` | Stdout file | `-o output_%j.txt` |
| `-e` | Stderr file | `-e error_%j.txt` |
| `-C` | Constraint (NVMe) | `-C nvme` |
| `--threads-per-core` | Hardware threads | `--threads-per-core=2` |
| `--reservation` | Use reserved nodes | `--reservation=my_reservation` |

### Example Batch Script

```bash
#!/bin/bash
#SBATCH -A PRJ123
#SBATCH -J simulation
#SBATCH -N 64
#SBATCH -t 02:00:00
#SBATCH -p batch
#SBATCH -o %x-%j.out
#SBATCH -e %x-%j.err

# 64 nodes, 8 GPUs per node = 512 total GPUs
# 8 tasks per node, 1 GPU per task
srun -n 512 --ntasks-per-node=8 --gpus-per-task=1 ./my_application
```

### NVMe Access

To request node-local NVMe storage (burst buffer):

```bash
#SBATCH -C nvme

# NVMe mounted at /mnt/bb/$USER
cp $SLURM_SUBMIT_DIR/input.dat /mnt/bb/$USER/
```

### Job Monitoring

```bash
# View your jobs
squeue --me

# Estimate start time
squeue --me --start

# Detailed job information
scontrol show job $SLURM_JOBID
```

## Allocation Programs

OLCF provides compute time through three primary allocation programs.

### INCITE (Innovative and Novel Computational Impact on Theory and Experiment)

- **Purpose**: Large-scale, computationally intensive research requiring leadership-class resources
- **Allocation sizes**: Millions to hundreds of millions of node-hours
- **Award periods**: 1-3 years
- **Selection**: Peer-reviewed proposal process (annual call, typically spring)
- **Requirements**: Demonstrated readiness and scalability

### ALCC (ASCR Leadership Computing Challenge)

- **Purpose**: High-risk, high-payoff simulations in DOE mission areas
- **Focus areas**: Energy science, climate, materials, nuclear physics, fusion energy
- **Allocation cycle**: Annual
- **Allocation sizes**: Medium to large

### Director's Discretionary (DD)

- **Purpose**: Small allocations for startup projects, code development, benchmarking
- **Turnaround**: Rapid approval process
- **Use cases**:
  - New users exploring system capabilities
  - Application porting and testing
  - Preliminary scaling studies
  - Preparing INCITE/ALCC proposals

## Accounting

### Node-Hour Charging

Frontier charges allocations based on **node-hours**:

```
Node-hours = Nodes_requested x Walltime_used (hours)
```

All nodes in a job allocation are charged regardless of actual utilization. GPU and CPU resources are not charged separately.

### Usage Monitoring

Projects can monitor allocation consumption through:

1. **myOLCF web interface**: https://my.olcf.ornl.gov
2. **Command line**: Project usage commands (contact OLCF for current utilities)

### Allocation Overuse Policy

Projects that exceed their allocation are still allowed to run, but at reduced priority:

- Overuse jobs appear "younger" in the queue than within-allocation jobs
- Additional walltime restrictions may apply
- Projects should request allocation increases or manage usage proactively

## Special Requests

For exemptions to standard policies, contact **help@olcf.ornl.gov** with details about:

- **Relaxed queue limits**: Longer walltime or higher priority for specific jobs
- **System reservations**: Dedicated nodes at specific date/time

## Related Notes

- [[overview/overview]] - System specifications and performance
- [[operations/applications]] - Workloads and science domains running on Frontier
- [[operations/power]] - Power delivery, monitoring, and operational impacts
- [[operations/cooling]] - Thermal management and cooling system behavior
- [[operations/compute]] - Compute node architecture and operations
