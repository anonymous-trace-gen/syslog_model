# Compute Operations

Node-level operations and component behavior for Frontier's AMD-based compute infrastructure.

## Node Architecture

### AMD Node Configuration

| Component | Specification |
|-----------|---------------|
| CPU | 1x AMD EPYC 7A53 "Trento" (64 cores, 2.0 GHz base, 3.5 GHz boost) |
| GPUs | 4x AMD Instinct MI250X (2 GCDs per package, 8 GCDs total) |
| DDR4 Memory | 512 GiB (8 channels) |
| HBM2e Memory | 512 GiB total (128 GiB per MI250X) |
| NVMe Storage | 3.84 TB local (2 x 1.92 TB) |
| NICs | 4x Cassini Slingshot (200 Gbps / 25 GB/s each, 800 Gbps / 100 GB/s aggregate) |

### CPU Specifications (AMD EPYC 7A53 "Trento")

| Specification | Value |
|---------------|-------|
| Architecture | Zen 3c based "Trento" |
| Core Count | 64 cores per socket |
| Base Frequency | 2.0 GHz |
| Maximum Frequency | 3.5 GHz |
| Cache Hierarchy | L1: 32 KB/core, L2: 512 KB/core, L3: 32 MB shared |
| TDP | 400W (AMD spec); 280W in Bard Peak system power budget |
| Memory Channels | 8x DDR4-3200 |

### GPU Specifications (AMD Instinct MI250X)

| Specification | Value |
|---------------|-------|
| GCDs per Package | 2 |
| Stream Processors | 7,040 per GCD (14,080 per package) |
| Compute Units | 110 per GCD (220 per package) |
| HBM2e Memory | 64 GB per GCD (128 GB per package) |
| HBM Frequency | 1.2 GHz |
| GPU Base Frequency | 1.8 GHz |
| GPU Peak Frequency | 2.5 GHz |
| TDP | 560W per package |
| Peak FP64 (vector) | 23.9 TFLOPS per GCD |
| Peak FP64 (matrix) | 47.9 TFLOPS per GCD |

### Memory Architecture

- **Coherent Memory**: Full CPU-GPU coherency via AMD Infinity Fabric 3.0
- **HBM2e Bandwidth**: 1.6 TB/s per GCD, 3.2 TB/s per package, 12.8 TB/s aggregate per node
- **DDR4 Bandwidth**: ~205 GB/s (8 channels x ~25.6 GB/s)
- **HBM Access Latency**: ~100 ns typical

## GPU Memory Hierarchy

### Cache Organization Per GCD

| Cache Level | Size | Description |
|-------------|------|-------------|
| L0 Cache (Vector) | Per-SIMD | CPU-style L1 equivalent |
| L1 Cache (TCP) | 16 KB | Texture Cache Per-channel per vector unit |
| L2 Cache | 1 MB | Shared per GCD |
| LDS | 64 KB | Local Data Share per work group |

### Memory Types

- **VMEM (Vector Memory)**: Global HBM accessed via memory controller
- **SMEM (Scalar Memory)**: Private registers and L0 cache
- **LDS (Local Data Share)**: Per work-group shared memory (not globally addressable)

### Interconnect (XGMI v3)

| Specification | Value |
|---------------|-------|
| Links per GCD | 3 (XGMI0, XGMI1, XGMI2) |
| Bandwidth per Link | 16 GB/s unidirectional |
| Aggregate per GCD | 48 GB/s bidirectional |
| Latency (GCD-to-GCD) | ~200-300 ns |
| PCIe Interface | 4.0 x16 per GPU (16 GB/s) |

## GPU Power Management

### Power States

The MI250X operates in three primary performance states managed by AMD's PowerPlay technology: High (full compute, max frequency/power), Medium (balanced, reduced power envelope), and Low (idle, aggressive power gating). The AGT tool tracks "Time in State" as residency percentages.

### Voltage Rails

VDDGfx (graphics, 0.90V idle), VDDCR_SOC (SOC, 0.95V idle), VDDC (core, variable), VDDCI (I/O, variable).

### Power Limit Control

Configurable via `AGT -setpowerlimit=<watts>`. Per-package TDP: 560W nominal. Dynamic adjustment based on thermal and power envelope constraints.

### XGMI Power Management

Each XGMI link (XGMI0, XGMI1, XGMI2) supports independent power-down states. Telemetry tracks xGMI bandwidth utilization, power-down state per link, and link activity monitors.

## Thermal Performance

### Operating Temperatures

All major components (CPU, GPU, DDR4) operate in the 86-89C case temperature range.

### Thermal Monitoring

The internal AGT tool accesses 96 sensors per GPU package, aggregatable to a single "ASIC Temperature" value. Commands: `AGT -temp` or `AGT -vctfstatus`. Looping: `temp:loop<#>` or `temp:period<#>` (default 1000ms).

### Thermal Management Features

- **Thermal Trigger Tracking**: Logs instances where thermal limits were reached
- **DPTC**: Dynamic Power and Thermal Control
- **Temperature State Residency**: Tracks time at various temperature levels (internal tool only)

### Cooling Integration

All major components (CPU, GPUs, DDR4 DIMMs) use direct liquid cold plates. DDR4 direct liquid cooling is unique to Frontier. Over 97% of heat is removed via direct-to-water cooling.

## Reliability and RAS Infrastructure

Target reliability: 5-year system lifetime, < 1% failure rate over lifetime.

### RASDAEMON Integration

RASDAEMON is the primary userspace tool for collecting Machine Check Exceptions (MCEs) and memory failure events via AMD SMCA (Scalable Machine Check Architecture). Error logs are stored and forwarded for analysis.

### Telemetry Pipeline

```
Syslog (Kernel/Driver) -> journalbeat -> HPCM Kafka -> AM team Kafka -> ITDB
```

In analyzed snapshots from August 2022, AMDGPU logs comprised 98% of total syslog volume; RASDAEMON logs 0.6%.

### Machine Check Architecture (MCA)

Key components: SMCA (AMD Scalable MCA for error reporting), MSR (Model-Specific Registers), AGESA (AMD Generic Encapsulated Software Architecture), APCB (AGESA PSP Configuration Block tokens), CPM (Common Platform Module firmware), EDAC (Linux Error Detection And Correction driver framework).

## Error Detection and Tracking

### Error Categories

**CPU Errors**:
- Cache errors (L1, L2, L3)
- Memory controller errors
- Fabric errors

**GPU Errors**:
- GPU memory errors (correctable/uncorrectable)
- HBM correctable errors
- SRAM ECC errors
- Interconnect fabric errors
- gfx UE (Uncorrectable Error) events

**System Errors**:
- Ring engine errors (comp, sdma, vcn_dec/enc, jpeg_dec, kiq)
- VBIOS/ROM fetch errors
- PSP runtime database errors

### GPU Error Handling

Errors are handled via the AMDGPU device driver (`drivers/gpu/drm/amd/amdgpu/amdgpu_ras.c`), exposed through SysFS and debugFS. ECC status monitoring covers MEM ECC and SRAM ECC. Successful RAS initialization is logged as `hardware ability[e] ras_mask[e]` or `hardware ability[7fff] ras_mask[7fff]`.

### Tracked Failure Modes (RMA Tracker)

GPU card not present (detection failure), unable to flash (firmware update failure), fatal error during GPU Initial (boot-time initialization failure), gfx UE (uncorrectable error requiring replacement), HBM correctable errors (memory errors during hbm2e test), slow DGEMM (performance degradation), GPU power fault (power delivery failure).

## AGT Diagnostic Tool

AMD GPU Tool (AGT) provides comprehensive hardware diagnostics and monitoring.

Two versions exist: Internal (full parameters, 96 sensors, ORNL/AMD internal) and External (reduced parameters, NDA-protected release). Must be run with root/sudo privileges.

### Core Commands

| Command | Function |
|---------|----------|
| `-i` | List all AMD GPU, CPU, and APU devices |
| `hwid` | ASIC Device ID, Revision ID, BIOS part number |
| `sid` | ASIC Serial IDs (GCD, CCD, MCD) |
| `mc` | Memory controller settings |
| `efuse` | EFUSE information (lot number, wafer XY, date) |
| `unilog` | Unilog data (PM, PMF, TMON) |
| `pm` | Power management telemetry |
| `powerplay` | PowerPlay feature management |
| `dptc` | Dynamic Power and Thermal Control |
| `-eccinfo` | ECC error information |
| `-setpowerlimit=<#>` | Set power limit in Watts |
| `-temp` | Temperature monitoring |
| `-vctfstatus` | Voltage/Clock/Thermal/Fan status |

## Telemetry Collection

### Node-Level Metrics

- **Power**: Per-node consumption, voltage rails (VDDGfx, VDDCR_SOC, VDDC, VDDCI)
- **Temperature**: CPU, GPU (multiple ASIC points), memory, ambient
- **Frequency**: GFXCLK (target/actual), FCLK, LCLK
- **Memory**: Utilization, bandwidth, HBM device IDs
- **GPU**: Utilization, memory pressure, activity monitors
- **Interconnect**: XGMI bandwidth, XGMI power-down state per link

### Per-Component Telemetry Parameters

- **Frequency**: GFXCLK (target/actual), FCLK (Fabric), LCLK (Link)
- **Hardware IDs**: ASIC Serial ID (SID), Product/Board Serial Numbers, Vendor 0x1002 / Device 0x7408
- **HBM Memory**: HBM_DeviceID and Raw_ID for HBM0 through HBM3
- **Activity Monitors**: Context Switching Trigger, Activity Trigger, Static screen detection counts

### Collection Infrastructure

XNAME-based hierarchical addressing integrated with HPE Cray system management. Supports real-time and historical collection. Error logs forwarded via HPE to AMD for long-term monitoring.

## Serial Number Tracking

Each MI250 package contains multiple identification levels: Product Serial Number (fused on board, customer-readable), Board Serial Number (OEM, two per MI250 config), FUSE ID (metal fuses encoding lot number, wafer XY, date), SID (customer-readable FUSE ID), and DevID (from flash memory).

Board ID to Serial ID to FUSE ID correlation enables manufacturing traceability. Frequency binning is recorded at manufacturing. AMD's database contains FUSE IDs for failure traceability, with two FUSE IDs per MI250 pair enabling unique system identification. Serial numbers use hash translation encoding and require a lookup table for decoding.

## Performance Profiling

ROCm 5.2 supports up to 8 simultaneous counter samples, requiring 17 complete passes for full characterization. It provides full application recording and replay capability with XML-based configuration.

**Top-Down Analysis Methodology**: Wave launch bottleneck, compute utilization bottleneck, memory subsystem analysis, data fabric efficiency, HBM memory bandwidth saturation.

**Available Counters**: Wave dispatch efficiency, LDS utilization, L1/L2 cache behavior, data fabric traffic, memory controller operations, theoretical speed-of-light calculations.

## Related Notes

- [[hub]] - Frontier supercomputer main reference
- [[layout/compute]] - Physical composition and layout of compute components
- [[operations/power]] - Power delivery and management operations
- [[operations/cooling]] - Cooling systems and thermal management
- [[layout/interconnect]] - Interconnect topology and layout
