# Compute Layout

Physical composition and layout of Frontier's compute infrastructure, from cabinet structure down to node-level component arrangement.

## System Scale

| Metric | Value |
|--------|-------|
| Olympus cabinets | 77 (expanded from 74 in Sep 2024) |
| Chassis per cabinet | 8 |
| Compute blades per chassis | 8 |
| Nodes per blade | 2 |
| Nodes per cabinet | 128 |
| Total chassis | 616 |
| Total compute nodes | 9,856 |

## Cabinet Configuration

### HPE Cray EX Olympus Cabinets

Frontier uses HPE Cray EX liquid-cooled cabinets (Olympus). The system does not use cabinet-level controllers; management occurs at the chassis level through Chassis Management Modules (CMMs).

**Cabinet Physical Organization**:
- Chassis are arranged vertically in pairs: 0/1, 2/3, 4/5, 6/7 (bottom to top)
- Front side: Compute blades with overhead coolant plumbing
- Rear side: Switch blades, CMMs, and Cabinet Environmental Controllers (CECs)
- Each chassis has 8 compute blade slots (0-7) on the front and 8 switch blade slots (0-7) on the rear

### Power Distribution

Each cabinet contains four Power Distribution Units (PDUs) that supply the rectifier shelves:

| PDU | Chassis Served |
|-----|----------------|
| PDU 0 | Chassis 0/1 |
| PDU 1 | Chassis 2/3 |
| PDU 2 | Chassis 4/5 |
| PDU 3 | Chassis 6/7 |

**Rectifier Shelf Configuration**:
- One rectifier shelf per chassis pair
- 8 rectifiers per shelf (4 per chassis, ABB CC15000H3C380T, 480 Vac to 380 Vdc). Frontier added two extra rectifiers per shelf beyond the standard HPE configuration to meet exascale power requirements.
- PSUs are liquid-cooled for thermal efficiency

### Cabinet Environmental Controllers

Two CECs per cabinet monitor and control environmental conditions:
- CEC 0: Right side (adjacent to chassis 4/5)
- CEC 1: Left side (adjacent to chassis 6/7)

## Chassis Architecture

### Chassis Management Module (CMM)

Each chassis includes a CMM that provides:
- Redfish REST endpoints for hardware management
- Control interface for all chassis components
- PSU monitoring and management
- Connection to the Hardware Management Network (HMN)

The CMM communicates with:
- Node controllers (nC) on compute blades
- Switch controllers (sC) on switch blades
- Power supply units

### Orthogonal Connection Design

The HPE Cray EX architecture uses orthogonal (backplane-free) connections between compute blades and switch blades, enabling direct blade-to-blade connections and independent upgrade paths for compute and network components. This forms the basis for the dragonfly topology within each chassis.

**Connection Topology**:
- Each switch blade has 16 terminal links to NIC Mezzanine Cards (NMCs)
- Each switch blade has 48 local/global links for inter-cabinet connectivity
- L0 cable assemblies connect switch blades to external fabric

## Blade Composition

### Frontier Compute Blade Design

Frontier blades contain 2 nodes per blade (vs. 4-node standard EX425) to accommodate the larger GPU packages and cooling requirements.

| Component | Per Blade |
|-----------|-----------|
| Node cards | 2 |
| Nodes per node card | 1 |
| CPUs per node | 1 |
| GPUs per node | 4 |
| Memory channels | 8 per node |
| NIC Mezzanine Cards | 2 |

### Node Card Layout

Each node card contains:
- One AMD EPYC 7A53 "Trento" CPU (64 cores, 2.0 GHz base)
- Four AMD Instinct MI250X GPU packages (each with 2 GCDs)
- Eight DDR4 memory channels (512 GB total per node)
- 512 GB HBM2e memory (128 GB per GPU package)
- Infinity Fabric connections between CPU and GPUs

### NIC Mezzanine Cards (NMCs)

- Two NMCs per blade (one per node card), pluggable design
- Slingshot HSN connections: 4x 200 Gb/s ports per node (800 Gb/s aggregate)
- Orthogonal connection to chassis switch blades

## Node Physical Layout

### Component Arrangement

Each Frontier node integrates components in a dense, liquid-cooled configuration:

**CPU Domain**:
- AMD EPYC 7A53 "Trento" (64-core, 2.0 GHz base clock)
- Custom variant of Milan with Infinity Fabric 3.0 for GPU coherency
- 8 memory channels with DDR4 DIMMs
- 512 GB DDR4 system memory

**GPU Domain**:
- 4x AMD Instinct MI250X packages
- Each package contains 2 Graphics Compute Dies (GCDs)
- 8 GCDs total per node (effectively 8 logical GPUs)
- 128 GB HBM2e per GPU package (32 GB per GCD)
- 512 GB total HBM2e per node

**Memory Hierarchy**:

| Memory Type | Capacity per Node | Bandwidth |
|-------------|-------------------|-----------|
| DDR4 DRAM | 512 GB | ~205 GB/s |
| HBM2e | 512 GB | 3.2 TB/s aggregate |
| Total | 1,024 GB | - |

### Infinity Fabric Topology

AMD Infinity Fabric 3.0 interconnects CPU and GPUs within each node, providing cache-coherent memory access across domains and GPU-to-GPU peer-to-peer communication.

## Thermal Design

Frontier achieves >97% direct-to-water cooling.

**Cooling Coverage**:

| Component | Cooling Method |
|-----------|----------------|
| CPUs | Direct liquid cold plate |
| GPUs | Direct liquid cold plate |
| DDR4 DIMMs | Direct liquid cold plate |
| Switch blades | Liquid cooled |
| CMMs | Secondary coolant loop |
| Rectifiers/PSUs | Liquid cooled |

### Coolant Flow Paths

- **Primary loop**: Supply manifolds at cabinet bottom, flows upward through chassis cold plates (CPUs, GPUs, memory), return manifolds at cabinet top
- **Secondary loop**: Services switch blades and CMMs via overhead plumbing

### Thermal Parameters

| Parameter | Value |
|-----------|-------|
| HTW supply temperature | 29.4C (85F) nominal |
| Component inlet range | 41F to 89.6F (ASHRAE W32) |
| CPU/GPU/DDR4 exhaust | 86-89C |
| Direct-to-water ratio | >97% |

High coolant temperature (vs. traditional chilled water) enables higher cooling tower efficiency and reduced refrigeration requirements (PUE ~1.05).

## Row Configuration

### Data Center Floor Layout

| Parameter | Value |
|-----------|-------|
| Olympus cabinets | 77 |
| Coolant Distribution Units (CDUs) | 25 |
| CDU to cabinet ratio | 1:3 |
| Grid coordinates | X (55-16) x Y (AA-CE) |

### Cabinet and CDU Arrangement

Column layout pattern (Y-axis): `o,o,o,c,o,o,o,c,o,o,o,c,c,o,o,o` (o=cabinet, c=CDU).

Each CDU serves a cooling group of 3-4 cabinets with floor-standing design and under-floor piping.

## Component Naming Convention (xnames)

HPE Cray EX uses a hierarchical component naming scheme (xnames) for system management.

### Naming Pattern Examples

Examples use generic cabinet x1016. Frontier uses x2000+ encoding (see Frontier-Specific Ranges).

| Level | Pattern | Example | Description |
|-------|---------|---------|-------------|
| Cabinet | xX | x1016 | Cabinet 1016 |
| Chassis | xXcC | x1016c3 | Chassis 3, cabinet 1016 |
| Blade slot | xXcCsS | x1016c3s7 | Blade slot 7, chassis 3, cabinet 1016 |
| Node card | xXcCsSbB | x1016c3s7b0 | Node card 0, blade 7, chassis 3 |
| Node | xXcCsSbBnN | x1016c3s7b0n0 | Node 0, node card 0, blade 7 |
| GPU | xXcCsSbBnNaA | x1016c3s7b0n0a1 | GPU 1, node 0, node card 0 |

### Controller Naming

| Component | Pattern | Example |
|-----------|---------|---------|
| Chassis BMC (CMM) | xXcCbB | x1016c4b0 |
| Node controller (nC) | xXcCsSbB | x1016c3s1b0 |
| Switch controller (sC) | xXcCrRbB | x1016c3r4b0 |
| CEC | xXeE | x1016e0 |

### Frontier-Specific Ranges

Cabinet numbers encode grid position: `cabinet_number = 2000 + (row * 100) + col` (e.g., x2509 = row 5, col 9).

- Cabinet range: x2000 - x2611 (77 cabinets across 7 rows, not contiguous)
- Chassis range: c0 - c7 (8 per cabinet)
- Blade slot range: s0 - s7 (8 per chassis)
- Node card range: b0 - b1 (2 per blade)
- Node range: n0 (1 per node card)

### Cabinet Grid

The 77 compute cabinets occupy a 7-row by 12-column floor grid:

```
        col: 0  1  2  3  4  5  6  7  8  9  10 11
row 0:       x  x  x  x  x  x  x  x  x  x  x  x   (12)
row 1:       x  x  x  x  x  x  x  x  x  x  x  x   (12)
row 2:       x  x  x  x  x  x  x  x  x  x  x  x   (12)
row 3:       x  x  x  x  x  .  x  x  x  x  x  x   (11, col 5 missing)
row 4:       x  x  x  x  x  x  x  x  x  x  x  x   (12)
row 5:       x  x  x  x  x  x  x  x  x  x  x  x   (12)
row 6:       x  x  x  .  .  .  .  .  .  x  x  x    (6, sparse)
```

Row 6: original 3 cabinets (col 9-11) at launch; 3 added (col 0-2) during Apr-Sep 2024 expansion.

### CDU-to-Cabinet-Column Cooling Assignment

Four CDU columns (a, b, c, d) in aisles between cabinet columns:

```
 0  1  2 [a] 3  4  5 [b] 6  7  8 [c][d] 9  10  11
```

| CDU col | Physical position    | Cools cabinet cols |
|---------|----------------------|--------------------|
| a       | Between col 2 and 3  | 0, 1, 2            |
| b       | Between col 5 and 6  | 3, 4, 5            |
| c       | Between col 8 and 9  | 6, 7, 8            |
| d       | Between col 8 and 9  | 9, 10, 11          |

Rows 0-5: four CDUs each; row 6: one CDU (column d only).

## Summary Statistics

| Hierarchy Level | Count |
|-----------------|-------|
| Olympus cabinets | 77 |
| Chassis | 616 |
| Compute blades | 4,928 |
| Node cards | 9,856 |
| Compute nodes | 9,856 |
| CPUs | 9,856 |
| GPU packages | 39,424 |
| GCDs (logical GPUs) | 78,848 |
| CDUs | 25 |
| Switch blades | 4,928 |

## Related Notes

- [[layout/data-center]] - Facility-level floor layout, grid coordinates, and zone organization
- [[layout/cooling-distribution]] - CDU arrangement, coolant distribution piping, and cabinet cooling groups
- [[layout/power-delivery]] - Power distribution from facility to cabinet rectifiers
- [[layout/interconnect]] - Slingshot HSN fabric, switch blade topology, and inter-cabinet cabling
- [[operations/compute]] - Compute node operations, health monitoring, and troubleshooting
- [[telemetry/hardware-topology]] - Telemetry-validated xname encoding and chassis counts
