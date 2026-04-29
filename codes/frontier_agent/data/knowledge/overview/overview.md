# Frontier Overview

General knowledge, specifications, and historical context for the Frontier exascale supercomputer (OLCF-5) at Oak Ridge National Laboratory.

## Historical Context

Frontier is designated OLCF-5 (Oak Ridge Leadership Computing Facility, fifth generation), the successor to Summit (OLCF-4). The system continues ORNL's tradition of leadership-class computing:

| System | Year | Designation | Peak Performance | Power |
|--------|------|-------------|------------------|-------|
| Jaguar | 2009 | OLCF-2 | 2.3 PF | 7 MW |
| Titan | 2012 | OLCF-3 | 27 PF | 9 MW |
| Summit | 2017 | OLCF-4 | 200 PF | 13 MW |
| **Frontier** | 2022 | OLCF-5 | 1,700 PF (1.7 EF) | 29 MW |

Frontier was procured through the CORAL-2 (Collaboration of Oak Ridge, Argonne, and Livermore) program. HPE won the contract to build the system. DOE-funded vendor R&D programs (FastForward, DesignForward, PathForward) addressed exascale challenges in performance, scalability, resiliency, and power efficiency.

## Exascale Achievement

On May 30, 2022, Frontier achieved #1 on both the TOP500 and Green500 lists, becoming the world's first exascale-class supercomputer with a measured 1.102 exaFLOPS (Rmax on HPL benchmark).

### Energy Efficiency Breakthrough

The path to exascale required a 150x improvement in energy-efficient computing from Jaguar to Frontier:

| System | Energy per ExaFLOP |
|--------|--------------------|
| Jaguar (2009) | 3,043 MW/EF |
| Titan (2012) | 330 MW/EF |
| Summit (2017) | 65 MW/EF |
| **Frontier (2022)** | **21 MW/EF** |

Key factors enabling this efficiency:
- GPU acceleration (pioneered by ORNL starting with Titan in 2012)
- Increasing GPU:CPU ratios (1:1 on Titan, 3:1 on Summit, 4:1 on Frontier)
- DOE Forward vendor R&D investments (2012-2020)
- Warm water cooling (32 C inlet temperature)
- Data center PUE of 1.03-1.06

One cabinet of Frontier (2.5 m^2) delivers 10% higher HPL performance than all of Titan (200 cabinets, 404 m^2), while consuming only 309 kW compared to Titan's 7 MW.

## Architecture

### Fat Node Design

Frontier employs AMD's accelerator-centric "fat node" design with a 4:1 GPU to CPU ratio, maximizing compute density per node while maintaining coherent memory across all components.

### Key Architectural Decisions

**Coherent Memory Architecture**
- AMD Infinity Fabric provides high-speed coherent interconnect between CPU and GPUs
- All memory (DDR4 on CPU, HBM2e on GPUs) is accessible from any processor
- xGMI3 links at 50 GB/s between GPU dies; xGMI2 at 36 GB/s for CPU-GPU connections

**Network-Attached GPUs**
- Each of the 4 GPUs has a dedicated NIC (Cassini) attached directly to it
- HBM-resident data can be transmitted without traversing slower CPU links
- 100 GB/s aggregate network bandwidth per node (4x 25 GB/s NICs)

**Direct Liquid Cooling**
- All components are water-cooled, including DIMMs and NICs
- No fans in the compute blades
- Enables 400 kW per rack power density

### Node Architecture ("Bard Peak")

Each node contains:
- 1x AMD EPYC 7A53 "Trento" CPU with 8 CCDs (Core Complex Dies)
- 4x AMD Instinct MI250X GPUs (each with 2 GCDs, 8 GCDs total per node)
- One GCD paired with each CCD for optimal locality
- Fully connected mesh of GPUs and CPU via Infinity Fabric

## Specifications

### System Performance

| Parameter | Value |
|-----------|-------|
| Peak Performance | 2 exaFLOPS (2x10^18 FLOPS) |
| Linpack (Rmax) | 1.102 exaFLOPS |
| Power Consumption | ~29 MW (typical), 40 MW (design) |
| Footprint | 4,000 ft^2 (360 m^2) |
| PUE | 1.05-1.06 (annualized) |
| Energy Efficiency | 52.23 gigaflops/watt (Green500 #1 at launch) |

### Hardware Configuration

| Component | Specification |
|-----------|---------------|
| Compute Racks | 77 Olympus racks (expanded from 74 in Sep 2024) |
| Total Nodes | 9,856 (expanded from 9,472 in Sep 2024) |
| CPU per Node | 1x AMD EPYC 7A53 "Trento" (64 cores) |
| GPUs per Node | 4x AMD Instinct MI250X |
| DDR4 Memory | 512 GiB per node (4.6 PB total) |
| HBM2e Memory | 512 GiB per node (128 GiB per GPU, 4.6 PB total) |
| NVMe Storage | 3.84 TB per node (2 x 1.92 TB; ~38 PB total) |
| NICs per Node | 4x Cassini (200 Gbps / 25 GB/s each, 800 Gbps / 100 GB/s aggregate) |
| Rack Weight | 8,000 lbs (3,600 kg) |
| Rack Power | 400 kW maximum |

### Storage

| Component | Capacity |
|-----------|----------|
| Node Local (NVMe) | ~38 PB (75 TB/s read, 38 TB/s write) |
| Center-wide (Orion) | 716 PB |
| Orion Peak Bandwidth | 5 TB/s |
| Flash Performance Tier | 11 PB |
| Metadata Flash | 10 PB |

### Interconnect

- Cray Slingshot-11 with dragonfly topology
- 200 Gb/s per port (4 ports per node)
- 161,844 total network ports
- 150+ km of cables (18,816 L0, 9,472 L1, 5,402 L2 AOC)
- All water cooled (including DIMMs and NICs)
- Libfabric/OFI programming interface

## TOP500 and Green500 History

### TOP500 Rankings

| Date | Rank | Rmax (PFLOPS) | Notes |
|------|------|---------------|-------|
| May 2022 | #1 | 1,102 | First exascale system; debut |
| Nov 2022 | #1 | 1,102 | Retained position |
| May 2023 | #1 | 1,194 | +92 PFLOPS upgrade |
| Nov 2023 | #1 | 1,206 | Continued improvements |
| May 2024 | #1 | 1,206 | Fifth consecutive #1 |
| Nov 2024 | #2 | 1,206 | Displaced by El Capitan (1.742 EF) |

Frontier held the #1 position for five consecutive TOP500 lists (June 2022 through June 2024).

### Green500 Rankings

| Date | Rank | Efficiency (GF/W) | Notes |
|------|------|-------------------|-------|
| May 2022 | #1 | 52.23 (production) | First system to top both TOP500 and Green500 simultaneously |
| May 2022 | #1 | 62.68 (TDS) | Frontier Test and Development System partition |
| Nov 2022 | #2 | 52.23 | Passed by Henri (Flatiron Institute, 65.40 GF/W) |
| May 2023 | #6 | 52.59 | Continued efficiency improvements |

## Comparison with Summit (OLCF-4)

| Attribute | Summit (2017) | Frontier (2022) | Change |
|-----------|---------------|-----------------|--------|
| Peak Performance | 200 PF | 1,700 PF | 8.5x |
| Node Count | 4,608 | 9,408 (at launch; 9,856 after Sep 2024 expansion) | 2x |
| CPU Vendor | IBM POWER9 | AMD EPYC | - |
| GPU Vendor | NVIDIA Volta | AMD MI250X | - |
| GPUs per Node | 6 | 4 (8 GCDs) | - |
| GPU:CPU Ratio | 3:1 | 4:1 | Higher |
| On-node Interconnect | NVIDIA NVLink | AMD Infinity Fabric | - |
| System Interconnect | Mellanox EDR IB | HPE Slingshot | - |
| Node Injection BW | 25 GB/s | 100 GB/s | 4x |
| Topology | Fat Tree | Dragonfly | - |
| Power | 13 MW | 29 MW | 2.2x |
| Storage Type | GPFS | Lustre | - |
| Storage Capacity | 250 PB | 716 PB | 2.9x |

### Programming Model Migration

| Summit | Frontier | Notes |
|--------|----------|-------|
| CUDA C/C++ | HIP C/C++ | hipify tool assists migration |
| OpenACC | OpenMP (offload) | Direct OpenACC support under discussion |
| OpenMP (offload) | OpenMP (offload) | Compatible |
| CUDA Fortran | Fortran w/HIP C/C++ | Requires C/C++ interfaces |

## Open Science Mission

The Oak Ridge Leadership Computing Facility's mission is to provide capability computing resources for the most difficult problems to enable new scientific insights.

