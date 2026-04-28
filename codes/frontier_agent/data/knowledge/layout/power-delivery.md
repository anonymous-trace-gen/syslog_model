# Power Delivery Layout

Physical power delivery infrastructure for the Frontier supercomputer: feeders, transformers, voltage stepping, switchboard-to-cabinet mapping, and XNAME naming conventions for power components.

## Electrical Infrastructure Overview

| Parameter | Value |
|-----------|-------|
| Typical Operation | ~29 MW |
| Peak Capacity | 40 MW |
| Transformer Capacity | 36 MVA |
| Power Factor | 0.998 |
| VTHD | 3.2% |
| ITHD | 6.5% |
| Support Systems | ~1.4 MW capacity (~0.8 MW typical) |
| Power Efficiency | 52.23 gigaflops/watt (Green500 #1 at launch) |

## Voltage Stepping

Power flows through four transformation stages:

1. **Grid Input**: 161 kV from external substation
2. **Primary Distribution**: 13.8 kV overhead feeders to facility
3. **Secondary Distribution**: 480Y/277V at switchboard level
4. **Rack Level**: Direct 480V/150A circuits to compute cabinets

## Feeder Configuration

The facility receives power through four 13.8 kV overhead feeders from the 161 kV substation:

| Feeder Type | Count | Rating |
|-------------|-------|--------|
| New overhead feeders | 2 | 13.8 kV / 1200 A |
| Reused existing feeders | 2 | 13.8 kV / 600 A |

## Transformer Configuration

A mix of reused and new transformers provides the 36 MVA total capacity.

### Existing Transformers (Reused)

- **Seven units**: 2.5/3.3 MVA each
- **One unit**: 3.0/4.0 MVA

### New Transformers (Added)

- **Four units**: 3.0/4.0 MVA each
- **Efficiency**: 99.54% at 50% load
- **Insulation**: FR3 oil-filled with containment
- **Compliance**: Designed to meet FM requirements

### Transformer Oil Management

Two existing transformers experienced low oil levels after 16 years of service. Mitigations included:
- Added cooling fans and lowered room temperature to 55F
- Verified manufacturer approval for continued operation
- Filled transformers after achieving Top500 milestone
- Ongoing monitoring with thermal imaging (IR cameras)

### Main Switchboard (MSB) to Cabinet Mapping

Ten Main Switchboards distribute 480 Vac from the facility to cabinets and CDUs. The west half (cabinet cols 0-5, CDU cols a, b) is served by MSB24-27; the east half (cabinet cols 6-11, CDU cols c, d) by MSB8-14. Each MSB covers roughly a two-row band within its half.

Cabinets connect to either a north or south switchboard panel. Some positions at zone boundaries are dual-powered by two MSBs (comma-separated below). North panel assignments:

```
          0   1   2   a   3   4   5   b   6   7   8   c     d   9    10   11
row 0:   24  24  24  24  24  24  24  24  13  13  13  13    13  13    13   13
row 1:   24  24  24  24  25  25  25  25   8   8   8   8 13,11  11 13,11   13
row 2:   25  25  25  25  25  25  25  25  11  11  11  11    11  11    11   11
row 3:   26  26  26  26  14  14  14  14   -  14  14  14 10,14  14 13,10   10
row 4:   26  26  26  26  26  26  26  26  10  10  10  10    10  10    10   10
row 5:   27  27  27  27  27  27  27  27   9   9   9   9     9   9     9    9
row 6:   27  27  27  27   -   -   -   -   -   -   9   9  9,14  14  14,9    -
```

Positions marked `-` have no cabinet or are powered from the south panel. Columns a-d are CDU column positions (see [[telemetry/hardware-topology]], Cabinet Grid).

Each cabinet receives 4 power feed circuits from its MSB, one per chassis pair (0/1, 2/3, 4/5, 6/7), entering through the PDU circuit breakers at the bottom of the cabinet. Each CDU receives 2 feed circuits. Dual-powered positions split feeds evenly: 2+2 for cabinets, 1+1 for CDUs.

### Transformer-to-MSB Assignment

Each MSB is fed by a 13.8 kV to 480Y/277V unit substation. The four 3.0/4.0 MVA units serve the west/north MSBs (MSB24-27).

| MSB | Cabinets | CDUs | Design Load (MVA) | Transformer | Origin |
|-----|----------|------|--------------------|-------------|--------|
| MSB24 | 9.0 | 3.0 | 3.58 | 3.0/4.0 MVA | New |
| MSB25 | 9.0 | 3.0 | 3.58 | 3.0/4.0 MVA | New |
| MSB26 | 9.0 | 3.0 | 3.58 | 3.0/4.0 MVA | New |
| MSB27 | 8.0 | 2.0 | 3.17 | 3.0/4.0 MVA | New |
| MSB13 | 8.0 | 2.5 | 3.18 | 3.0/4.0 MVA | Reused |
| MSB9  | 6.5 | 2.5 | 2.59 | 2.5/3.3 MVA | Reused |
| MSB10 | 7.5 | 2.5 | 2.98 | 2.5/3.3 MVA | Reused |
| MSB11 | 7.5 | 2.5 | 2.98 | 2.5/3.3 MVA | Reused |
| MSB14 | 6.5 | 3.0 | 2.60 | 2.5/3.3 MVA | Reused |
| MSB8  | 3.0 | 1.0 | 1.19 | 2.5/3.3 MVA | Reused |

Design load estimates assume 2,683 W max node power at SuperIVOC input, ~355 kW DC per cabinet (including switch blades and CMMs), rectifier efficiency of 95%, CDU max AC input of 9.5 kW, and measured power factor of 0.998. Dual-powered positions count as half load per MSB. During HPL runs, measured per-cabinet power is 294-300 kW at the PDU input, approximately 75% of the design maximum.

This accounts for 10 of the 12 transformers. The two remaining 2.5/3.3 MVA reused transformers likely serve non-compute loads (cooling plant, management infrastructure, or south panel circuits).

## Distribution Architecture

### Switchboard Configuration

The primary switchboards operate at 480Y/277V with 5000A capacity.

| Breaker Type | Count | Assignment |
|--------------|-------|------------|
| 150A feeder breakers | 36 | 9 compute racks per breaker |
| 60A feeder breakers | 6 | 3 CDUs per breaker |

### Overhead Distribution

- **Circuits per rack**: 4 (max 400 kVA per rack), 480V / 150A each
- **Cable type**: MC cable to fused flexible cord transition, direct to racks
- **Expansion**: Spare cable tray for future growth

## XNAME Hierarchy for Power Components

HPE Cray EX systems use the XNAME naming convention to identify component geolocation. For power monitoring and management, the hierarchy follows this structure:

### Cabinet Level

| Pattern | Range | Description |
|---------|-------|-------------|
| `xX` | X: 0-9999 | Liquid-cooled cabinet (8 chassis, no cabinet-level controller) |
| `xXeE` | E: 0-1 | Cabinet Environmental Controller (CEC); E=0 right, E=1 left |

### PDU Hierarchy

| Pattern | Range | Description |
|---------|-------|-------------|
| `xXmM` | M: 0-3 | PDU Controller (BMC) for one or more PDUs |
| `xXmMpP` | P: 0-7 | Rack PDU managed by controller |
| `xXmMpPjJ` | J: 1-32 | PDU outlet (power outlet on specific PDU) |
| `xXm0pPvV` | V: 1-64 | PDU power connector to node cards/enclosures |

### Chassis Power Components

| Pattern | Range | Description |
|---------|-------|-------------|
| `xXcC` | C: 0-7 | Chassis within cabinet |
| `xXcCtT` | T: 0-2 | Power rectifier XNAME (4 physical rectifiers per chassis; CSM XNAME range is 0-2) |

### Node Power Connections

| Pattern | Range | Description |
|---------|-------|-------------|
| `xXcCsS` | S: 0-64 | Node slot position (blades 0-7 in chassis) |
| `xXcCsSvV` | V: 1-2 | Power connector for node enclosure (1-2 per node) |

### CDU (Coolant Distribution Unit)

| Pattern | Range | Description |
|---------|-------|-------------|
| `dD` | D: 0-999 | CDU identifier (1 CDU serves up to 6 cabinets) |
| `dDwW` | W: 0-31 | Management switch within CDU |
| `xXdD` | D: 0-1 | Rack-mounted CDU |

### Example XNAME Paths

The x1016 examples below use HPE's generic cabinet number to illustrate the xname format. Frontier's actual cabinets use the x2000+ encoding (e.g., x2509 for row 5, col 9).

```
x1016m0p0j12    = Outlet 12, PDU 0, controller 0, cabinet 1016
x1016c3t2       = PSU 2, chassis 3, cabinet 1016
x1016c1s7       = Compute blade 7, chassis 1, cabinet 1016
x3000c0s4v1     = Power connector 1, server U4, chassis 0, rack 3000
d3              = CDU 3 (serves up to 6 cabinets)
```

## Per-Cabinet Power Distribution

Each Olympus rack (cabinet) in Frontier has the following power characteristics:

| Parameter | Value |
|-----------|-------|
| Maximum Power | 400 kW per rack |
| Weight | 8,000 lbs |
| Nodes | 128 AMD nodes |
| Chassis | 8 per cabinet |
| Rectifiers per Chassis | 4 (ABB CC15000H3C380T, 480 Vac to 380 Vdc) |
| CECs | 2 (one left, one right) |

## Metering Points

Power and energy measurement occurs at multiple levels for PUE calculation and operational monitoring.

### Space-Level Compute Metering

- **12 power meters** at the compute space level
- Measures IT load consumption

### Facility Metering

| Type | Count |
|------|-------|
| Power meters | 16 |
| Flow meters | 4 |
| Estimates | 5 |

### Switchboard-Level Metering

- Metered at switchboard level with CDU sub-metering
- Largest facility consumers: cooling tower fans, chilled water system (summer only)

## Power Quality and Protection

### UPS Configuration

- **Compute systems**: No traditional UPS/generator backup
- **Support circuits**: Dual-corded with flywheel-backed UPS on one side
- **Racks**: Single-corded (CDUs have internal transfer switch)

### Protection Coordination

- Quality ORNL craft checks: torquing, micro-ohm resistance, visual inspection
- SCCR coordination with available fault currents
- HPE/Frontier racks equipped with fuses providing >65 kA SCCR

## Known Issues and Solutions

### CDU VFD DC Bus Voltage

**Problem**: Harmonics from Frontier racks caused CDU variable frequency drives (VFDs) to exceed voltage thresholds.

**Solutions Applied**:
- Added in-line chokes to VFDs
- Decreased transformer secondary voltage
- Supply single circuit when CDU has internal transfer switch

### LED Lighting Flicker

**Problem**: Unique Frontier load profile (7.6 MVA swings over 3 cycles at 13.8 kV) causes voltage fluctuations affecting LED lighting.

**Solutions**:
- Separate LED lighting from HPC power feeders
- Install UPS on lighting circuits
- Work with LED vendors on voltage tolerance

## Related Notes

- [[overview/overview]] - System overview and high-level architecture
- [[operations/power]] - Operational procedures for power management
- [[layout/cooling-distribution]] - CDU placement and cooling distribution layout
- [[layout/data-center]] - Facility layout and floor plan
- [[telemetry/hardware-topology]] - Cabinet grid and XNAME topology
