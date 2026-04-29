# Event Taxonomy

87 HPC event types from 18.4 billion classified Frontier log events, spanning 12 subsystems and categories.


## Taxonomy (12 subsystems)

### Slingshot Network (10)

| Index | Event | Description |
|-------|-------|-------------|
| 0 | NET_CXI_RAW_DATA | CXI raw data event  |
| 3 | NET_CXI_TIMEOUT | CXI operation timeout |
| 5 | NET_CXI_LINK | CXI link event |
| 7 | NET_CXI_WARN | CXI warning |
| 11 | NET_CXI_INT_ERR | CXI internal error |
| 13 | NET_CXI_HW_ECC | CXI hardware ECC error |
| 15 | NET_CXI_SVC | CXI service event |
| 42 | NET_CXI_FIRMWARE | CXI firmware event |
| 44 | NET_CXI_PHY_ERR | CXI physical layer error |
| 54 | NET_CXI_MGMT_ERR | CXI management error |

### AMD MI250X GPU (7)

| Index | Event | Description |
|-------|-------|-------------|
| 16 | GPU_MEM_FAULT | GPU memory access fault |
| 23 | GPU_SOFT_LOCK | GPU soft lockup detected |
| 28 | GPU_RAS_FAIL | GPU RAS (Reliability, Availability, Serviceability) error |
| 34 | GPU_DRIVER_ERR | GPU driver error |
| 36 | GPU_FIRMWARE | GPU firmware issue |
| 50 | GPU_HARD_FAULT | GPU hard fault |
| 61 | GPU_TIMEOUT | GPU operation timeout |

### Hardware — MCE / PCIe (20)

| Index | Event | Description |
|-------|-------|-------------|
| 10 | HW_MCE_GENERIC | Generic machine check exception |
| 12 | HW_MCE_FATAL | Fatal machine check exception |
| 17 | HW_MCE_CORRECTED | Corrected (recoverable) machine check exception |
| 52 | HW_MCE_CPU | CPU-originated machine check exception |
| 66 | HW_MCE_DUMP | Machine check exception dump |
| 86 | HW_MCE_UNK | Unknown machine check exception |
| 26 | HW_MEM_DIMM | DIMM memory error |
| 67 | HW_MEM_CORRUPT | Memory corruption detected |
| 18 | HW_EDAC_ERR | EDAC (Error Detection and Correction) error |
| 75 | HW_CPU_CORE | CPU core error |
| 9  | HW_PCIE_ERR | PCIe error |
| 81 | HW_PCIE_HUB | PCIe hub error |
| 29 | HW_IOMMU_ERR | IOMMU error |
| 37 | HW_BMC_WARN | Baseboard Management Controller warning |
| 40 | HW_ACPI_WARN | ACPI warning |
| 64 | HW_THERMAL_CRIT | Critical thermal event |
| 51 | HW_USB_FAIL | USB device failure |
| 24 | HW_FABRIC_RTR | Fabric router error |
| 85 | HW_FABRIC_INT | Fabric interconnect error |
| 48 | HW_IF_GPU_LINK | GPU interconnect link failure |

### Storage — Lustre / GPFS (10)

| Index | Event | Description |
|-------|-------|-------------|
| 1  | FS_DISK_FULL | Disk full event |
| 6  | FS_DVS_WARN | DVS (Data Virtualization Service) warning |
| 19 | FS_CLUSTER_EVICT | Cluster eviction event |
| 20 | FS_LUSTRE_SLOW | Lustre slow I/O |
| 30 | FS_LUSTRE_OST_ERR | Lustre OST (Object Storage Target) error |
| 33 | FS_LUSTRE_ERR | General Lustre error |
| 35 | FS_XFS_ERR | XFS filesystem error |
| 43 | FS_IO_ERR | Generic I/O error |
| 49 | FS_GPFS_ERR | GPFS filesystem error |
| 55 | FS_LUSTRE_MDS_ERR | Lustre MDS (Metadata Server) error |

### OS / Kernel (10)

| Index | Event | Description |
|-------|-------|-------------|
| 32 | SYS_KERNEL_CTX | Kernel context switch issue |
| 46 | SYS_OOM_KILL | Out-of-memory kill |
| 62 | SYS_SEGFAULT | Segmentation fault |
| 53 | SYS_WATCHDOG | Watchdog timeout |
| 56 | SYS_CONFIG_ERR | System configuration error |
| 57 | SYS_RCU_STALL | RCU (Read-Copy-Update) stall |
| 72 | SYS_KERNEL_PANIC | Kernel panic |
| 74 | SYS_COREDUMP | Core dump generated |
| 76 | SYS_PROCESS_LIM | Process limit reached |
| 77 | SYS_X11_NOISE | X11 display subsystem noise |
| 78 | SYS_CLOCK_SKEW | Clock skew detected |

### Kernel Context (5)

| Index | Event | Description |
|-------|-------|-------------|
| 65 | CTX_LUSTRE | Lustre context event |
| 73 | CTX_AMDGPU | AMD GPU context event |
| 79 | CTX_SCHEDULER | Job scheduler context event |
| 83 | CTX_MEMORY | Memory context event |
| 84 | CTX_SLINGSHOT | Slingshot network context event |

### Services (8)

| Index | Event | Description |
|-------|-------|-------------|
| 4  | SVC_RSYSLOG_ERR | rsyslog service error |
| 21 | SVC_SYSTEMD_START | systemd unit start event |
| 22 | SVC_CONFIG_ERR | Service configuration error |
| 45 | SVC_SYSTEMD_SPEC | systemd unit spec issue |
| 63 | SVC_SYSTEMD_TIME | systemd unit timeout |
| 69 | SVC_SYSTEMD_EXIT | systemd unit unexpected exit |
| 71 | SVC_SYSTEMD_KILL | systemd unit killed |
| 82 | SVC_SYSTEMD_PAM | systemd PAM authentication event |

### Applications (8)

| Index | Event | Description |
|-------|-------|-------------|
| 14 | APP_INFRA_FAIL | Application infrastructure failure |
| 38 | APP_JOB_CANCEL | Job cancelled |
| 39 | APP_CFG_ERR | Application configuration error |
| 41 | APP_JOB_LATENCY | Job latency event |
| 47 | APP_JOB_CGROUP | Job cgroup issue |
| 31 | APP_FILE_MISSING | Required file missing |
| 58 | APP_JOB_ERR | Job error |
| 70 | APP_GITLAB_FAIL | GitLab CI/CD failure |

### Network — non-CXI (5)

| Index | Event | Description |
|-------|-------|-------------|
| 8  | NET_TCP_FAIL | TCP connection failure |
| 25 | NET_CONFIG_ERR | Network configuration error |
| 59 | NET_RPC_ERR | RPC error |
| 60 | NET_LNET_ERR | LNet (Lustre network) error |
| 80 | NET_LNET_WARN | LNet warning |

### Security (1)

| Index | Event | Description |
|-------|-------|-------------|
| 27 | SEC_AUTH_FAIL | Authentication failure |

### NVMe Storage (1)

| Index | Event | Description |
|-------|-------|-------------|
| 68 | STO_NVME_STALL | NVMe storage stall |

### Informational (1)

| Index | Event | Description |
|-------|-------|-------------|
| 2 | INFO_NOISE | High-volume informational noise |

---

## Special Tokens

| Index | Token | Description |
|-------|-------|-------------|
| 87 | PAD | Padding token |
| 88 | UNK | Unknown event |
| 89 | MASK | Masked token (used during training) |

---

## Event Frequency Distribution

### Dominant events

| Event | Count | % |
|-------|-------|---|
| NET_CXI_RAW_DATA | 11,899,498,645 | 64.84 |
| FS_DISK_FULL | 2,483,668,470 | 13.53 |
| INFO_NOISE | 2,378,954,930 | 12.96 |
| NET_CXI_TIMEOUT | 608,310,833 | 3.31 |
| SVC_RSYSLOG_ERR | 267,987,611 | 1.46 |

### Operationally critical events

| Event | Count | % |
|-------|-------|---|
| GPU_MEM_FAULT | 13,643,033 | 0.074 |
| HW_MCE_CORRECTED | 8,599,882 | 0.047 |
| HW_EDAC_ERR | 8,484,582 | 0.046 |
| GPU_SOFT_LOCK | 5,421,374 | 0.030 |
| GPU_RAS_FAIL | 2,257,964 | 0.012 |
| GPU_DRIVER_ERR | 1,348,563 | 0.007 |
| GPU_HARD_FAULT | 109,204 | 0.0006 |

### Rare critical events

| Event | Count | % |
|-------|-------|---|
| HW_MEM_CORRUPT | 6,719 | 0.00004 |
| SYS_KERNEL_PANIC | 1,971 | 0.00001 |
| CTX_AMDGPU | 1,899 | 0.00001 |
| HW_CPU_CORE | 1,463 | 0.000008 |
| CTX_MEMORY | 41 | 0.0000002 |
