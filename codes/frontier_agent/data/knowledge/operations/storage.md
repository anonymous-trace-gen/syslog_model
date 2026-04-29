# Storage Operations

Orion/Lustre storage system operations, I/O patterns, and energy characteristics for Frontier.

## Orion Filesystem Architecture

Orion is Frontier's center-wide parallel filesystem based on **HPE ClusterStor** with **Lustre** as the underlying technology. The system provides a unified namespace for all Frontier users and is also accessible from data transfer nodes and the Andes cluster.

### Core Specifications

| Parameter | Value |
|-----------|-------|
| Total Usable Capacity | 679 PB |
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

