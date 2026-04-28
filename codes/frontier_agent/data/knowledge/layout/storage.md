# Storage Layout

Physical arrangement and infrastructure topology of the Orion storage system within the Frontier data center, covering the River zone floor placement, CDU assignment, OSS node distribution, and network connectivity.

## River Zone Overview

The Orion Lustre storage system is housed in the **River zone** of the Frontier data center (Building E102). This zone is physically separated from the Olympus compute zone and operates at lower thermal density.

### Zone Specifications

| Parameter | Value |
|-----------|-------|
| Total River cabinets | 55 |
| I/O cabinets (Orion storage) | 42 |
| Switch cabinets | 5 |
| Service cabinets | 4 |
| ITDB cabinets | 3 |
| Storage management cabinets | 1 |
| River CDUs | 6 |
| RDHX units | 55 |

### Zone Boundaries

The River zone occupies a distinct rectangular area adjacent to the Olympus compute zone:

- **North boundary**: Borders Olympus compute zone (77 compute cabinets)
- **West boundary**: Adjacent to future expansion area (reserved for 74 additional Olympus cabinets)
- **Connection to compute**: Via Slingshot Dragonfly fabric

## Cabinet Physical Layout

### Grid Coordinate System

The River zone uses the same X/Y grid coordinate system as the broader Frontier facility:

| Axis | Range |
|------|-------|
| Rows | BS through CB (10 rows) |
| Columns | 08/09 through 53/54 (7 main columns plus RDF section) |

### Main Cabinet Block

The primary Orion storage block consists of 70 cabinets arranged in a 7 x 10 grid:

| Column | Grid Position | Cabinet Count |
|--------|---------------|---------------|
| 53/54 | Far left | 10 |
| 49/50 | | 10 |
| 44/45 | | 10 |
| 39/40 | | 10 |
| 34/35 | | 10 |
| 30/31 | | 10 |
| 25/26 | Far right (adjacent to CDUs) | 10 |

### RDF Section

A separate RDF (Remote Data Facility) section at Column 08/09 contains at least 10 additional cabinets in a vertical stack, housing data transfer and gateway systems.

### Cabinet Dimensions

| Cabinet Type | Width (in) | Depth (in) | Height (in) | Weight (lbs) |
|--------------|------------|------------|-------------|--------------|
| I/O Cabinet | 23.60 | 47.25 | 92.00 | 4,000 |
| Switch Cabinet | 23.60 | 47.25 | 92.00 | 2,500 |
| Service Cabinet | 23.60 | 47.25 | 88.90 | 2,500 |
| ITDB Cabinet | 23.60 | 47.25 | 88.90 | 2,500 |
| Storage Mgmt | 23.60 | 47.25 | 88.90 | 2,500 |

## CDU Assignment and Placement

### River CDU Configuration

The River zone uses 6 MCDU-40 coolant distribution units positioned at the right edge of the cabinet block (Column 25/26).

| Parameter | Value |
|-----------|-------|
| CDU model | MCDU-40 |
| Total count | 6 (5 running + 1 standby) |
| CDU-to-cabinet ratio | 1:7 (one CDU per ~7 I/O cabinets) |
| Heat rejection | 11.50 KBTU/HR per CDU |
| Physical location | Adjacent to Row BS through CB |

### Cooling Distribution

Unlike the Olympus zone's direct liquid cooling (>97% heat removal via water), River cabinets use a hybrid approach:

- **Rear Door Heat Exchangers (RDHX)**: 55 M12 units mounted on cabinet backs
- **RDHX supply temperature**: 67 deg F (19 deg C)
- **RDHX dimensions**: 23.60" W x 16.25" D x 88.90" H
- **RDHX weight**: 200 lbs each
- **Feed type**: Direct-fed from CDUs with dew point management to prevent condensation

## OSS Node Placement

### Storage Server Distribution

Object Storage Servers (OSS) are distributed across the 42 I/O cabinets. The mapping follows the RDHX port assignments, which indicates physical node placement:

| Column | RDHX Port Range | Function |
|--------|-----------------|----------|
| 53/54 | p/20 - p/29 | OSS nodes (Switch BV53 domain) |
| 49/50 | p/11 - p/19 | OSS nodes |
| 44/45 | p/1 - p/10 | OSS nodes |
| 39/40 | p/11 - p/20 | OSS nodes (Switch BW40 domain) |
| 34/35 | p/1 - p/10 | OSS nodes |
| 30/31 | p/11 - p/20 | OSS nodes (Switch BW31 domain) |
| 25/26 | p/1 - p/10 | OSS nodes + CDU proximity |

### Metadata Server Placement

Metadata Servers (MDS) are co-located within the storage cabinet block, managing the 5,400+ Object Storage Targets (OSTs) that constitute Orion's 679 PB capacity.

## Network Connectivity

### BAS3 Industrial Telemetry Network

The River zone connects to facility monitoring through the BAS3 (Building Automation System 3) industrial telemetry network. This network provides:

- Power consumption monitoring
- Environmental sensor data
- Cooling system telemetry
- Equipment health status

### Switch Distribution

Three primary BAS3 switches serve the Orion storage infrastructure:

| Switch ID | Location | Port Range | Coverage |
|-----------|----------|------------|----------|
| SWA-E102-BV53 | Column 53/54 | p/20 - p/29 | Leftmost cabinet columns |
| SWA-E102-BW40 | Column 39/40 | p/11 - p/20 | Central cabinet columns |
| SWA-E102-BW31 | Column 25/26, 30/31 | p/1 - p/20 | Rightmost columns + CDU area |

### Aggregation and Gateway

All BAS3 switches aggregate to a central point:

| Component | Location | Function |
|-----------|----------|----------|
| SWD-RDF-BD08 | RDF BD08 | Central aggregation for BV53, BW40, BW31 |
| CI14 JCI Metasys Panel | | Building management integration |
| CI14 Switch 4 | | Connects to RDF BD08 |
| CI14 Switch 5 | | CF09 Gateway, RDF BD08, River CDUs |

### Slingshot Fabric Connectivity

Storage nodes connect to compute through the Slingshot-11 network:

- High-speed fabric connections to all 9,856 compute nodes
- Dragonfly topology integration
- 4 x 200 Gb/s aggregate bandwidth per storage server
- Direct RDMA capability for efficient data transfer

## Power Infrastructure

### Electrical Specifications

| Parameter | Value |
|-----------|-------|
| Power supply | 400/230V, 3-phase, 60Hz |
| Power per cabinet | 33.25 kVA / 31.59 kW |
| Receptacle type | Hubbell SEJCER |
| Distribution | Overhead routing (same as Olympus zone) |

### Total Storage Power

Based on cabinet count and per-cabinet power ratings:

| Component | Count | Power Each | Total |
|-----------|-------|------------|-------|
| I/O cabinets | 42 | 31.59 kW | ~1,327 kW |
| Switch cabinets | 5 | ~31 kW | ~155 kW |
| Service cabinets | 4 | ~31 kW | ~124 kW |
| Other cabinets | 4 | ~31 kW | ~124 kW |
| **Estimated Total** | | | **~1,730 kW** |

Note: Actual operational power consumption averages ~850 kW with +/- 50 kW variation (see [[operations/storage]]).

## Integration with Facility Systems

### Central Energy Plant Connection

The River zone receives cooling from the Central Energy Plant through the same pipe bridge serving the Olympus zone:

- HTW (High Temperature Water) supply: 85 deg F nominal
- Underfloor PP-R piping distribution
- Flanged connections for serviceability

### Infrastructure Separation

Like the Olympus zone, the River zone maintains strict separation:

- **Overhead**: Electrical power distribution
- **Underfloor**: Water/coolant piping

This separation simplifies maintenance and mitigates risk from potential cooling system leaks.

## Related Notes

- [[hub]] - Frontier Supercomputer main hub
- [[layout/data-center]] - Comprehensive facility layout including River zone placement
- [[layout/cooling-distribution]] - CDU specifications including River MCDU-40 units
- [[layout/compute]] - Olympus compute zone layout (adjacent to River zone)
- [[layout/power-delivery]] - Power delivery infrastructure shared with storage
- [[operations/storage]] - Operational characteristics and energy profile
