# Storage Operations

Orion/Lustre storage system operations, I/O patterns, and energy characteristics for Frontier.

## Orion Filesystem Architecture

Orion is Frontier's center-wide parallel filesystem based on **HPE ClusterStor** with **Lustre** as the underlying technology. The system provides a unified namespace for all Frontier users and is also accessible from data transfer nodes and the Andes cluster.

### Core Specifications

| Parameter | Value |
|-----------|-------|
| Total Usable Capacity | 679 PB |
| Peak Aggregate Bandwidth | 5 TB/s |
| Object Storage Targets (OSTs) | 5,400+ |
| Filesystem Type | Lustre (HPE ClusterStor) |
| Namespace | `/lustre/orion/` |

### Lustre Architecture Components

**Metadata Servers (MDS)**:
- Handle filesystem namespace operations (file creation, directory lookups, permissions)
- Store metadata in Metadata Targets (MDTs)
- Critical for file open/close performance at scale

**Object Storage Servers (OSS)**:
- Manage data storage across Object Storage Targets (OSTs)
- Each OSS manages multiple OSTs
- Responsible for data read/write operations

**Object Storage Targets (OSTs)**:
- Physical storage units (typically RAID groups)
- Orion has 5,400+ OSTs for capacity and bandwidth
- Files are striped across multiple OSTs for performance

### Progressive File Layout (PFL)

Orion uses **Progressive File Layout (PFL)** technology that dynamically adjusts file striping as files grow. This feature:
- Automatically optimizes small files (low overhead)
- Scales stripe count as files grow larger (higher bandwidth)
- Eliminates the need for manual striping adjustments in most cases

**Recommendation**: Users are advised not to manually adjust striping without consulting OLCF support. When manual striping is necessary, limit to **no more than 450 OSTs**.

### OST Pool Tiers

The system provides both **performance** and **capacity** OST pool tiers:
- Performance tier: Optimized for high-bandwidth workloads
- Capacity tier: Optimized for large-capacity storage needs

## Storage Hardware

### Physical Layout

Orion storage hardware is located in the **River zone** of the Frontier data center (Building E102). The layout includes:
- 42 River cabinets housing Orion Lustre storage
- River CDUs (Coolant Distribution Units) for storage cooling
- Rear-Door Heat Exchangers (RDHX) for supplemental cooling
- Industrial telemetry networking (BAS3) for facility monitoring

### Network Connectivity

Storage systems connect through:
- BAS3 industrial telemetry network for management
- High-speed fabric connections to compute nodes
- Three primary switches: SW-BV53, SW-BW40, SW-BW31 (ports p/1-p/29)

## Storage Areas

Frontier provides multiple storage tiers with different characteristics:

### Lustre Storage Areas (Orion)

| Area | Path | Quota | Purge Policy | Permissions |
|------|------|-------|--------------|-------------|
| Member Work | `/lustre/orion/[projid]/scratch/[userid]` | 50 TB | 90 days | 700 (user only) |
| Project Work | `/lustre/orion/[projid]/proj-shared` | 50 TB | 90 days | 770 (group) |
| World Work | `/lustre/orion/[projid]/world-shared` | 50 TB | 90 days | 775 (world readable) |

### NFS Storage (Home/Project)

| Area | Path | Quota | Retention |
|------|------|-------|-----------|
| User Home | `/ccs/home/[userid]` | 50 GB | 90 days |
| Project Home | `/ccs/proj/[projid]` | 50 GB | 90 days |

### NVMe Node-Local Storage

Each compute node contains **two 1.92 TB NVMe SSDs** (3.84 TB total per node, ~37 PB system-wide):

| Parameter | Value |
|-----------|-------|
| Capacity per Node | 3.84 TB (2 x 1.92 TB) |
| Read Bandwidth | 5,500 MB/s (peak sequential) |
| Write Bandwidth | 2,000 MB/s (peak sequential) |
| Mount Point | `/mnt/bb/<userid>` |
| Access Method | Requires `-C nvme` allocation flag |

Node-local storage is ephemeral; users must manage data movement before and after jobs.

### Archival Storage (Kronos)

| Area | Combined Quota | Retention | Access Method |
|------|----------------|-----------|---------------|
| Shared Archival | 200 TB per project | 90 days | Globus or CLI |

Note: Kronos is not directly mounted on compute nodes.

## Quotas and Policies

### Quota Summary

| Storage Type | Default Quota | Notes |
|--------------|---------------|-------|
| Lustre scratch areas | 50 TB | Per user or project |
| NFS home | 50 GB | Per user |
| NFS project | 50 GB | Per project |
| Archival (Kronos) | 200 TB | Shared across 3 archival areas |

### Data Purge Policies

All scratch areas on Orion are subject to a **90-day purge policy**:
- Files not accessed within 90 days are automatically deleted
- Both access time (atime) and modification time (mtime) are considered
- No warning is provided before purge
- Critical data should be moved to archival storage

**Purge Mitigation Strategies**:
1. Regular access of important files (touch or read)
2. Migration to archival storage for long-term retention
3. Use project home (`/ccs/proj/`) for persistent but small datasets

## I/O Patterns

### Typical Workloads at OLCF

Based on operational data at OLCF:
- **30-40%** of applications use shared files (N:1 or N:M I/O patterns)
- **60-70%** of applications use file-per-process (N:N I/O patterns)

### Bulk-Synchronous I/O

HPC applications on Frontier frequently generate bulk-synchronous outputs:
- **Checkpointing**: Periodic writes of application state (10-50% of system memory)
- **Output files**: Scientific data, visualization dumps, restart files
- **Checkpoint requirement**: Write 20% of memory within 5 minutes to PFS

### I/O Performance Factors

**Metadata bottlenecks**:
- File open/close operations require metadata server coordination
- Creating files in shared directories requires directory locking
- Metadata overhead can exceed data transfer time at scale (1000+ nodes)

**Data striping effects**:
- Large sequential writes benefit from wide striping
- Small random I/O can suffer from stripe lock contention
- PFL automatically balances these concerns

**POSIX consistency overhead**:
- Lustre implements strict POSIX semantics
- Sequential consistency requires serialization of metadata operations
- Caching can improve performance but introduces consistency complexity

## Performance Characteristics

### Peak Bandwidth

| Metric | Value |
|--------|-------|
| Aggregate Read Bandwidth | 5 TB/s |
| Aggregate Write Bandwidth | 5 TB/s |
| Per-OST Bandwidth | ~1 GB/s (typical) |

### Latency Characteristics

Lustre operations involve multiple latency components:
- **Metadata operations**: Higher latency (network round-trip to MDS)
- **Data operations**: Lower latency (direct path to OSS)
- **Network latency**: Slingshot fabric provides low-latency connectivity

## Storage Telemetry

### Available Metrics

Storage telemetry is collected at multiple layers:

**Server-side (OSS/MDS)**:
- Power consumption
- Data capacity evolution
- Bandwidth behavior (read/write rates)
- Disk scrub activity

**Client-side**:
- Darshan I/O profiling (application-level)
- VFS-level statistics
- Lustre client statistics

### Measurement Points

Telemetry is collected at four layers: application view, VFS layer, Lustre client requests, and server-side filesystem hits. Caching effects significantly impact the relationship between application-level I/O and server-side activity.

## Energy Characteristics

### Power Consumption

Storage power on Orion is remarkably stable:

| Metric | Value |
|--------|-------|
| Average Power | ~850 kW |
| Variation | +/- 50 kW (typical) |
| Scrub Overhead | ~250 kW additional during scrubs |

### Why Power is Flat

Key insight from operational data: **dynamic power throttling is disabled** for performance consistency.
- Servers run at one power state continuously
- System is built for peak traffic capacity
- Scrubs simulate constant flood of disk activity (only significant power variation)

### Energy Efficiency Observations

Counterintuitive findings:
- **High bandwidth jobs do not necessarily increase power** (use efficient RDMA)
- **Bad I/O patterns waste more energy** than high-throughput jobs
- When storage is stressed by problematic workloads, energy is wasted on non-productive work

This suggests that I/O optimization benefits both performance and energy efficiency.

## Node-Local Storage Operations

### Burst Buffer Capability

Frontier's node-local NVMe provides burst buffer functionality:
- Write 20% of memory within 5 minutes target
- ~38 PB total node-local capacity (9,856 nodes x 3.84 TB)
- Enables checkpoint optimization by absorbing bursty I/O

### Access Patterns

Node-local storage requires explicit management:
1. Request allocation with `-C nvme` flag
2. Stage data in at job start (if needed)
3. Use `/mnt/bb/<userid>` during job
4. Stage data out before job completion
5. Data is deleted after job ends

### Performance Advantage

Node-local storage provides order-of-magnitude improvement for checkpoint workloads:
- Metadata operations scale with node count (no shared MDS)
- Data writes are purely local (no network latency)
- Enables overlap of computation with background PFS writes

## Spectral Library

ORNL developed **Spectral**, an interposition library for accelerating bulk-synchronous writes:
- Transparently redirects writes to node-local storage
- Uses two-phase consistency (local phase, then global phase)
- Requires no application modifications (LD_PRELOAD)
- Achieves >10x performance improvement over direct PFS writes at scale

## Related Notes

- [[layout/storage]] - Physical layout of Orion storage infrastructure
- [[layout/data-center]] - Data center layout including River zone storage area
- [[operations/compute]] - Compute operations that generate storage I/O
- [[operations/job-scheduling]] - Job scheduler integration with storage allocations
- [[operations/interconnect]] - Slingshot network fabric carrying I/O traffic
- [[operations/power]] - Facility power delivery including storage power draw
