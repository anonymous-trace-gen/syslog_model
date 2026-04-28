# Interconnect Layout

Physical network topology, switch placement, and cabling architecture for the Frontier Slingshot-11 interconnect.

## Overview

Frontier's interconnect uses the HPE Slingshot-11 network with a three-hop dragonfly topology. The physical layout integrates network switches directly into compute cabinets, minimizing cable lengths and optimizing for cost efficiency. This architecture achieves approximately 30% lower cost compared to an equivalent fat-tree topology while maintaining high bandwidth.

## Switch Locations

### Cabinet Integration

Network switches are integrated into the Olympus liquid-cooled cabinets using an **orthogonal switch blade** architecture:

- **Switch Chassis Position**: Switch blades mount vertically (orthogonally) in the middle-to-rear section of each cabinet, positioned directly behind compute blades and rectifiers
- **Water Cooling**: All blade switches in compute groups are water-cooled, sharing the cabinet's liquid cooling infrastructure
- **Separation**: Each cabinet contains a dedicated Switch Chassis separate from the Compute Chassis

### Switch Types by Location

| Cabinet Type | Switch Type | Cooling | Count |
|--------------|-------------|---------|-------|
| Olympus (Compute) | Blade switches | Liquid-cooled | 2,368 |
| River (I/O) | Top-of-Rack (TOR) | Air-cooled (1U 19" rack-mount) | 80 |
| River (Management) | Top-of-Rack (TOR) | Air-cooled (1U 19" rack-mount) | 16 |
| **Total** | | | **2,464** |

### Rosetta ASIC

The Rosetta switch ASIC is fabricated on TSMC 16nm, consuming up to 250W per switch. Internal architecture uses a tiled crossbar: 32 tiles arranged in 4 rows of 8, each tile handling 2 ports. Packets traverse at most 2 internal hops (row bus, then column channel). Typical switch latency is ~350 ns.

The same Rosetta ASIC ships in two physical form factors:

| Form Factor | Cooling | Mounting | Used in |
|-------------|---------|----------|---------|
| Switch blade | Liquid-cooled | Perpendicular to compute blades (cableless orthogonal) | Compute groups (EX cabinets) |
| Top-of-rack (TOR) | Air-cooled | Standard 1U 19" rack-mount, 64 front-facing QSFP-DD | I/O and management groups |

Both form factors expose the same 64 ports at 200 Gb/s.

### Data Center Floor Arrangement

The 77 Olympus compute cabinets (housing 74 dragonfly compute groups) are arranged in the primary compute section:

- **Layout Pattern**: Rows of 5 to 9 cabinets each, arranged in approximately 9 columns
- **Scalable Units**: Olympus cabinets cluster physically with associated Cooling Distribution Units (CDUs)
- **Cabinet Dimensions**: 46.5" wide x 68.5" deep x 98" high per Olympus cabinet
- **River Cabinets**: 42 air-cooled cabinets for storage, gateway, and management functions
- **Switch Cabinets**: 5 dedicated River cabinets house additional switching infrastructure

## Dragonfly Group Structure

### Group Organization

Frontier implements an 80-group dragonfly topology:

| Group Type | Count | Switches per Group | Purpose |
|------------|-------|-------------------|---------|
| Compute | 74 | 32 | Production compute workloads |
| I/O (Storage) | 5 | 16 | Orion filesystem connectivity |
| Management | 1 | 16 | System administration |
| **Total** | **80** | **2,464** | |

### Compute Group Composition

Each of the 74 compute groups contains:

- **32 Rosetta switches** (blade switches within cabinets)
- **8 chassis**, each with 4 switch blades and 8 compute blades
- **128 compute nodes** total per group (8 chassis x 8 blades x 2 nodes)
- **512 Cassini NICs** (4 NICs per node, 37,632 system-wide from 18,816 ASICs)

Groups and cabinets are not 1:1. The 74 compute groups span 77 physical cabinets; 3 row-6 expansion cabinets share groups with adjacent cabinets rather than forming their own groups.

### Intra-Group Connectivity

Switches within each group connect in a **fully-meshed** (all-to-all) pattern:

- Each switch connects to every other switch in the group via L1 (local) links
- This creates a single-hop path for any intra-group communication
- Provides 12.8 TB/s injection bandwidth per group

### Intra-Chassis Wiring

Each chassis contains 4 switch blades and 8 compute blades. Although the chassis has 8 physical switch blade slots, Frontier's wider GPU blade configuration means only 4 switch blades fit:

- Each switch blade has **8 connectors** (one per compute blade), each carrying **2 ports**
- 4 switch blades x 2 ports = 8 L0 ports per compute blade = 8 NICs (1:1 mapping)
- Each node's **4 NICs connect to 4 different switch blades**

```
Within one chassis (4 switch blades, 8 compute blades):

                    Switch 0        Switch 1        Switch 2        Switch 3
                   (16 L0 ports)   (16 L0 ports)   (16 L0 ports)   (16 L0 ports)
                       |               |               |               |
Blade 0 (2 nodes):  2 ports         2 ports         2 ports         2 ports  -> 8 NICs
Blade 1 (2 nodes):  2 ports         2 ports         2 ports         2 ports  -> 8 NICs
  ...
Blade 7 (2 nodes):  2 ports         2 ports         2 ports         2 ports  -> 8 NICs
```

L0 connections use a cableless orthogonal direct-mount (no backplane): switch blades sit perpendicular to compute blades with direct connectors at each crossing point.

Per group: 8 chassis x 4 switch blades = 32 switches per group.
Per group: 8 chassis x 8 blades x 2 nodes = 128 nodes per group.

## Port Topology

### Rosetta Switch Port Allocation

Each 64-port Rosetta switch allocates ports across three hierarchical levels:

| Level | Port Count | DeviceSpecificContext | Connection Target |
|-------|------------|----------------------|-------------------|
| L0 | 16 | `cassini` | Cassini NICs in compute nodes |
| L1 | 31 | `local` | Other switches in same group (full mesh) |
| L2 | ~9 | `global` | Switches in other groups |
| Unused/mgmt | ~8 | `ieee` | Management network or unused |
| **Total** | **64** | | |

Frontier uses only ~9 of the 17 possible L2 ports per switch: 74 compute groups x 4 links per arc = 292 global links per group, distributed across 32 switches. This tapering produces the 57% global-to-injection ratio. At full 17 L2 ports, the architecture could support up to 545 groups (~279K nodes).

I/O and management groups have 16 switches each, so their L1 mesh uses 15 ports per switch. The remaining 49 ports are split between edge and L2 connections depending on attached endpoints and required inter-group bandwidth.

### Bandwidth per Level

- **L0 (Injection)**: 16 ports x 200 Gb/s = 3.2 Tb/s per switch to endpoints
- **L1 (Intra-group)**: 31 ports x 200 Gb/s = 6.2 Tb/s per switch within group
- **L2 (Inter-group)**: ~9 ports x 200 Gb/s = ~1.8 Tb/s per switch to other groups

### Node-to-Switch Connectivity

Each compute node connects to 4 different switches:

- **4 Cassini NICs per node**, each providing 200 Gb/s (effective ~100 GB/s usable)
- Each NIC connects to a **distinct switch** within the chassis
- Total node injection bandwidth: 800 Gb/s (~100 GB/s effective per node)
- This distribution improves fault tolerance and load balancing

### Inter-Group Link Distribution

Global (L2) connectivity between groups follows a structured pattern:

| Connection Type | Bundle Size | Description |
|-----------------|-------------|-------------|
| Compute to Compute | 2 bundles | Two 200 Gb/s links between compute groups |
| Compute to Storage | 1 bundle | One bundle from each compute group to each storage group |
| Storage to Storage | 5 bundles | Higher bandwidth between storage groups |
| Storage to Management | 3 bundles | Administrative connectivity |

## Cabling Architecture

### Link Scope and Media

| Link | Scope | Medium |
|------|-------|--------|
| L0 (edge) | Intra-chassis only | Cableless orthogonal mount |
| L1 (intra-group) | Cross-chassis within cabinet | Copper DAC (0.75-2.39m) |
| L2 (inter-group) | Cross-cabinet | Optical (5-35m, up to 100m) |

### Cable Types

Frontier uses three distinct connection technologies based on link level:

**L0 (Cableless Orthogonal Mount)**:
- No cables: switch blades mount perpendicular to compute blades with direct connectors
- Zero cable cost, zero signal loss from connectors

**L1 Copper DAC (Short-reach)**:
- Used for intra-group (cross-chassis) connections
- Lower cost (~$100 per cable in cost models)
- Lengths 0.75-2.39m within the cabinet

**L2 Optical Cables (Long-reach)**:
- Used for inter-group connections
- **QSFP-DD Active Optical Cables (AOC)**
- Each bundle carries two 200 Gb/s links
- Higher cost (~$1,000 per cable in cost models)
- Lengths 5-35m, up to 100m between cabinet groups

### Cable Count Estimates

Based on the 2,464-switch topology with 64-port switches:

| Link Type | Cable Count | Cable Type |
|-----------|-------------|------------|
| L0 (Node to Switch) | ~37,888 | Electrical |
| L1 (Intra-group) | ~37,888 | Electrical |
| L2 (Inter-group) | ~18,944 | Optical (AOC) |

### Cost Efficiency

The dragonfly topology achieves cost savings by minimizing optical cable use:

- **~30-34% more cost-efficient** than equivalent non-blocking fat-tree
- Primary savings from reducing optical cable count
- Fat-tree would require roughly double the optical cables
- Estimated network cost difference: ~$23M savings at exascale

## Network Component Placement

### Cassini NIC Placement in Nodes

The Cassini NICs have an unusual placement optimized for GPU memory access:

- **Attached to GPU packages**: Unlike traditional designs where NICs connect to CPUs, Frontier's NICs attach directly to the **MI250X GPGPU OAM packages**
- **Purpose**: Enables direct high-bandwidth memory (HBM) access for GPU-driven communication
- **Configuration**: 4 NICs per node, each providing 200 Gb/s
- **Interface**: Each NIC connects to 2 of the 8 Graphics Compute Dies (GCDs) in the node

### Rosetta Switch Placement

**In Compute Cabinets (Olympus)**:
- Integrated as water-cooled blade switches
- Mounted orthogonally (vertically) in Switch Chassis
- Share liquid cooling with compute blades
- 32 switches per compute group across multiple chassis

**In I/O and Management Cabinets (River)**:
- Standard Top-of-Rack (ToR) switches
- Air-cooled configuration
- 16 switches per I/O or management group

### Cabinet-Level View

Within each Olympus cabinet:

```
Front (Hot Aisle)
+------------------+
|  Compute Blades  |  <-- CPU + GPU + Memory
|                  |
+------------------+
|    Rectifiers    |  <-- Power conversion
+------------------+
|  Switch Blades   |  <-- Rosetta switches (orthogonal mount)
+------------------+
|  Cooling/Mgmt    |
+------------------+
Back (Cold Aisle)
```

## Topology Characteristics

### Taper Ratio

Frontier implements a **57% global-to-injection taper ratio**:

- **Injection bandwidth per group**: 12.8 TB/s
- **Global connectivity per group**: 7.3 TB/s
- **System-wide global bandwidth**: 540 TB/s (270+270 TB/s bidirectional)

This intentional taper:
- Reduces cable count and cost
- Requires adaptive routing (UGAL) to distribute traffic
- Achieves practical all-to-all bandwidth of ~30 GB/s per node

### Three-Hop Maximum

The dragonfly topology ensures any two nodes communicate in at most three hops:

1. **Hop 1 (L0)**: Source node to source switch
2. **Hop 2 (L1 or L2)**: Within group or to intermediate/destination group
3. **Hop 3 (L0)**: Destination switch to destination node

For intra-group communication, only two hops are needed. Inter-group communication may use additional L1 hops through intermediate groups under congestion (non-minimal routing).

### Comparison to Fat-Tree

| Characteristic | Dragonfly (Frontier) | Fat-Tree (Summit) |
|----------------|---------------------|-------------------|
| Maximum hops | 3 | 5-7 |
| Path uniformity | Variable | Uniform |
| Performance variance | Higher (12.09 MPIGraph) | Lower (0.04 MPIGraph) |
| Cable cost | Lower (~30% savings) | Higher |
| Optical cable count | Lower | ~2x higher |

## Related Notes

- [[hub]] - Frontier supercomputer main hub
- [[operations/interconnect]] - Network operations and telemetry
- [[layout/compute]] - Cabinet and NIC placement context
- [[layout/data-center]] - Facility floor layout
- [[layout/storage]] - Storage system layout
