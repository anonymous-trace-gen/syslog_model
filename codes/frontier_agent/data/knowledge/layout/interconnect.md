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


### Data Center Floor Arrangement

The 77 Olympus compute cabinets (housing 74 dragonfly compute groups) are arranged in the primary compute section:

- **Layout Pattern**: Rows of 5 to 9 cabinets each, arranged in approximately 9 columns
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

