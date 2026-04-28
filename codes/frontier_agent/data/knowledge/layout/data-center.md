# Data Center Layout

Physical layout and spatial organization of the Frontier supercomputer data center at Oak Ridge National Laboratory, including compute and storage zones, cabinet configurations, and infrastructure routing.

## Floor Plan Overview

The Frontier data center floor is organized into two primary zones: the Olympus compute zone and the River storage/I/O zone. The facility uses a grid coordinate system spanning X (55 to 16) and Y (AA to CE) for precise equipment placement.

### Physical Specifications

| Parameter | Value |
|-----------|-------|
| Footprint | ~4,000 ft² (compute floor) |
| Grid coordinates | X (55→16) x Y (AA→CE) |
| Total compute racks | 77 Olympus cabinets (expanded from 74 in Sep 2024) |
| Total storage racks | 42 River cabinets |
| Total CDUs | 31 (25 Olympus + 6 River) |
| Compute chassis | 616 |
| Compute nodes | 9,856 |
| Rack weight | 8,000 lbs (3,629 kg) each |
| Rack power | Up to 400 kW per cabinet |

## Zone Layout

### Olympus Zone (Compute)

The Olympus zone occupies the primary compute area and contains all GPU-accelerated compute nodes.

| Parameter | Value |
|-----------|-------|
| Olympus cabinets | 77 (plus 1 hot spare TDS Hill cabinet) |
| Olympus CDUs | 25 |
| CDU-to-cabinet ratio | 1:3 (one CDU per three cabinets) |
| Cabinet dimensions | 2.75 x 2 grid cells |
| CDU dimensions | 2.75 x 1.5 grid cells |
| RDHX units | 74+ (Rear Door Heat Exchangers) |
| Heat load per cabinet | Up to 400 kW |

The zone also includes 3 Shasta cabinets and 2 additional CDUs for system management functions (labeled as TDS on floor plans).

### River Zone (Storage I/O)

The River zone houses the Orion Lustre storage system with lower thermal density than the compute zone.

| Parameter | Value |
|-----------|-------|
| River cabinets | 42 (I/O) |
| Switch cabinets | 5 |
| Service cabinets | 4 |
| ITDB cabinets | 3 |
| Storage management | 1 |
| River CDUs | 6 |
| RDHX units | 42 |
| CDU-to-cabinet ratio | 1:7 (one CDU per seven cabinets) |
| Cabinet dimensions | 2 x 1 grid cells |

The River zone uses MCDU-40 cooling distribution units (6 total: 5 running, 1 standby) that operate at lower capacity due to reduced thermal load from storage hardware.

## Row Configuration

### Olympus Column Layout

The Olympus zone organizes cabinets in 7 columns with a repeating interleaved pattern that places CDUs centrally among the cabinets they serve:

```
Y-pattern: o,o,o,c,o,o,o,c,o,o,o,c,c,o,o,o
```

Where `o` = compute cabinet and `c` = CDU

### Cabinet Grid

The 77 compute cabinets occupy a 7-row by 12-column grid. Cabinet numbers encode grid position: `cabinet_number = 2000 + (row * 100) + col` (e.g., x2509 = row 5, col 9).

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

Row 6 is sparsely populated: the original 3 cabinets (col 9, 10, 11) were present at launch, and 3 additional cabinets (col 0, 1, 2) were added during the Apr-Sep 2024 expansion.

### CDU-to-Cabinet Cooling Assignment

Four CDU columns (a, b, c, d) divide the floor into four cooling zones:

```
 0  1  2 [a] 3  4  5 [b] 6  7  8 [c][d] 9  10  11
```

CDU columns c and d are co-located between cabinet columns 8 and 9. Rows 0-5 each have four CDUs; row 6 has only column d.

| CDU col | Position | Cools cols |
|---------|----------|------------|
| a | Between col 2-3 | 0, 1, 2 |
| b | Between col 5-6 | 3, 4, 5 |
| c | Between col 8-9 | 6, 7, 8 |
| d | Between col 8-9 | 9, 10, 11 |

### River Column Layout

The River zone uses 8 columns of varying height (4-10 cabinets per column) to accommodate different equipment types:
- I/O cabinets (42 total)
- Switch cabinets (5)
- Service cabinets (4)
- ITDB cabinets (3)
- Storage management (1)

### Cabinet Dimensions

| Cabinet Type | Width (in) | Depth (in) | Height (in) | Weight (lbs) |
|--------------|------------|------------|-------------|--------------|
| Olympus | 46.50 | 68.50 | 98.00 | 8,000 |
| CDU (1.6MW) | 35.13 | 68.50 | 98.00 | 2,800 |
| River I/O | 23.60 | 47.25 | 92.00 | 4,000 |
| River Switch | 23.60 | 47.25 | 88.90 | 2,500 |
| River Service | 23.60 | 47.25 | 88.90 | 2,500 |

## Infrastructure Corridors

Service aisles provide 36 in (914 mm) clearance on both front (blade access) and rear (cooling/cable) sides.

Frontier does not use traditional hot/cold aisle containment; >97% of heat removal occurs via direct liquid cooling. The remaining <3% air-cooled components use 55 Rear Door Heat Exchangers (RDHX) on River cabinets, operating at 67°F (19°C) supply water.

## Overhead vs Underfloor Distribution

Electrical and water infrastructure are strictly separated: power overhead, water underfloor.

### Overhead Distribution (Electrical)

| Component | Specification |
|-----------|---------------|
| Power feed per cabinet | 4 x 120A circuits (480VAC, 3-phase, 4-wire) |
| Maximum per cabinet | 399 kVA sustained |
| Expected draw (ORNL config) | 373 kVA |
| Efficiency | >83% from facility AC to point of load |
| Cable routing | MC cable transitioning to fused flexible cord |
| PDU location | Top of each cabinet |

### Underfloor Distribution (Water/Cooling)

| Component | Specification |
|-----------|---------------|
| Piping material | PP-R (polypropylene random copolymer) |
| HTW supply | 29.4°C (85°F) nominal to CDUs |
| CHW supply | 42°F for facility support |
| Connection type | Flanged (designed for future adaptability) |
| Pipe bridge | Connects to Central Energy Plant |

## Thermal Neighborhoods

CDU grouping creates thermal neighborhoods where cabinets sharing a cooling source exhibit correlated thermal behavior.

### Olympus Cooling Groups

| Cooling Group Size | Nodes Affected | Thermal Coupling |
|--------------------|----------------|------------------|
| 3 cabinets | ~384 nodes | High (shared secondary loop) |
| CDU fault domain | Up to 500 nodes | Complete cooling loss |

Cabinets within a cooling group share:
- Secondary coolant supply temperature
- Coolant flow rate (pressure-balanced)
- CDU control setpoints
- Failure propagation risk

### Hotspot Factors and Thermal Topology

Localized thermal challenges arise from: CDU boundary temperature gradients, row-end reduced air mixing, sustained GPU thermal spikes, and CDU thermal lag (seconds response time vs millisecond workload changes).

Spatial arrangement impacts thermal modeling through: 1:3 CDU-to-cabinet thermal coupling, secondary loop time constants, CDU/facility-level HTW control interactions, CDU fault domains affecting entire cooling groups, and correlated telemetry within cooling groups.

## Cable Routing

### Power Distribution

Power flows from facility transformers to cabinets through:

1. **161kV substation**: 2 new + 2 reused feeders
2. **Facility transformers**: 12 total (8 reused from Summit + 4 new)
3. **Switchboards**: 480Y/277V, 5000A configuration
4. **Feeder breakers**: 9 compute racks per 150A breaker; 3 CDUs per 60A breaker
5. **Cabinet PDU**: Distributes to rectifiers via AC bus bars
6. **Rectifiers**: Convert 480VAC to 380VDC (96% efficient at half load)
7. **SIVDC bus**: Delivers 380VDC to chassis
8. **IVOC**: Converts 380VDC to 48VDC for components

### Cooling Connections

Coolant routing from facility to components:

1. **Pipe bridge**: HTW/CHW from Central Energy Plant
2. **Underfloor plenum**: PP-R piping to CDU locations
3. **CDU heat exchanger**: Primary (facility) to secondary (cabinet) loop transfer
4. **Overhead plumbing**: Top Feed Secondary Lines from CDU to cabinets
5. **Cabinet manifolds**: Supply and return distribution within cabinet
6. **Blade connections**: Flexible hoses to compute blade cold plates
7. **Component cooling**: Direct liquid to CPU, GPU, DIMM, NIC cold plates

### Network Connections

Slingshot interconnect cabling:
- 4 x 200 Gb/s injection ports per node
- Dragonfly topology with local and global links
- ToR (Top of Rack) leaf switches housed in CDU racks
- Management network aggregated through CDU-hosted switches

## Equipment Summary

| Equipment Type | Quantity | Electrical (per unit) | Cooling (per unit) |
|----------------|----------|----------------------|-------------------|
| Olympus Cabinet | 77 | 399 kVA max | 400 kW max |
| Olympus CDU (1.6MW) | 25 | 17.64 kW max | 1.6 MW capacity |
| River Cabinet (I/O) | 42 | 33.25 kVA | Air + RDHX |
| River Cabinet (Switch) | 5 | 33.25 kVA | Air + RDHX |
| River Cabinet (Service) | 4 | 33.25 kVA | Air + RDHX |
| River CDU (MCDU-40) | 6 | 18.00 kW | Varies |
| RDHX (Rear Door Coolers) | 55 | Fed from rack PDU | 0.84 kW each |
| TDS Hill Cabinet | 1 | 76.85 kVA | 7.68 kW |

### System Totals

| Parameter | Value |
|-----------|-------|
| Total electrical load | ~30.3 MW (cabinets + CDUs) |
| Total heat rejection | ~29.5 MW typical operation |
| System weight | ~3,353 tons |

## Construction Timeline

| Date | Milestone |
|------|-----------|
| April 2018 | Design start |
| Summer 2019 | Construction begins |
| March 2020 | COVID-19 impacts |
| June 2021 | Rack ready |
| Aug-Nov 2021 | Cabinet arrivals |
| May 30, 2022 | TOP500 #1 achieved (1.102 exaFLOPS) |

## Related Notes

- [[hub]] - Frontier supercomputer main hub
- [[layout/compute]] - Cabinet and blade architecture details
- [[layout/power-delivery]] - Electrical distribution from substation to component
- [[layout/cooling-distribution]] - CDU specifications and cooling loops
- [[layout/facility-cooling]] - Facility-level cooling infrastructure (Central Energy Plant)
- [[layout/storage]] - River zone storage placement and Orion Lustre system
- [[layout/interconnect]] - Slingshot network topology and cabling
- [[telemetry/hardware-topology]] - Cabinet grid positions, CDU hostname mapping, Row 6 expansion timeline
