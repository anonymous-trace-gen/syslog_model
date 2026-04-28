# Cooling Distribution Layout

Coolant Distribution Units (CDUs) and how HPE distributes coolants to components in the Frontier supercomputer.

## CDU Overview

The floor-standing Coolant Distribution Unit (CDU) is the heart of Frontier's direct liquid cooling system. Each CDU pumps coolant to HPE Cray EX cabinets through overhead plumbing (the secondary coolant loop), supplying 1 to 4 cabinets per unit (a cabinet cooling group). The CDU regulates coolant flow rate and temperature while compensating for variations in facility water temperature.

Beyond cooling, each CDU rack also houses the top-of-rack (ToR) leaf switches that aggregate all management network links for its entire cabinet cooling group.

### CDU Models

Frontier uses floor-standing CDUs manufactured by Motivair. HPE Cray EX systems support two CDU capacities:

| Model | Heat Capacity | Water Flow | Weight | Power |
|-------|---------------|------------|--------|-------|
| 1.2 MW CDU | 1.2 MW | Up to 240 GPM | 2,400 lbs (1,089 kg) | 16 kW max |
| 1.6 MW CDU | 1.6 MW | Up to 380 GPM | 2,740 lbs (1,242 kg) | 17.64 kW max |

Observed CDU AC input power from telemetry ranges from 800 W to 9,500 W per unit, depending on pump speed and cooling demand.

## CDU Specifications

### Physical Dimensions

Both 1.2 MW and 1.6 MW CDUs share the same external dimensions:

| Dimension | Value |
|-----------|-------|
| Height (with overhead cable trays) | 98.00 in (2,489 mm) |
| Height (cabinet with piping and doors) | 90.50 in (2,299 mm) |
| Height (frame only) | 80.25 in (2,038 mm) |
| Width | 35.13 in (892 mm) |
| Depth | 68.50 in (1,740 mm) |
| Access clearance (front/rear) | 36.00 in (914 mm) |
| Acoustical noise level | 72 dBA |

### Electrical Requirements

| Parameter | Specification |
|-----------|---------------|
| Voltage | 480 VAC (460-495 VAC) or 400 VAC (380-415 VAC) |
| Frequency | 50 Hz or 60 Hz |
| Phases | Three phase |
| Power circuits | Two circuits required (A+B redundant) |
| Circuit size | 60A @ 480 VAC or 63A @ 400 VAC |
| Power cord length | 8 ft (2.4 m) |
| Hold-up time | 20 ms minimum |

### Cooling Water Requirements

| Parameter | Specification |
|-----------|---------------|
| Temperature range | 41°F (5°C) to 90°F (32°C) maximum |
| Pressure range | 25-75 psi (172-517 kPa) |
| Temperature stability | Rate of change < 0.5°C per minute |
| Water quality | ASHRAE TC9.9 FWS specification |

## Zone Layout

Frontier's data center floor is divided into two primary cooling zones, each with distinct CDU-to-cabinet ratios reflecting their different thermal loads.

### Olympus Zone (Compute)

The Olympus zone houses all 77 compute cabinets containing the 9,856 AMD-based compute nodes.

| Parameter | Value |
|-----------|-------|
| Olympus cabinets | 77 |
| Olympus CDUs | 25 |
| CDU-to-cabinet ratio | 1:3 (one CDU per three cabinets) |
| Compute nodes | 9,856 total |
| Heat load per cabinet | Up to 400 kW |
| Cabinet dimensions | 2.75 x 2 grid cells |
| CDU dimensions | 2.75 x 1.5 grid cells |

The Olympus zone is organized in 7 columns with a repeating Y-pattern layout: `o,o,o,c,o,o,o,c,o,o,o,c,c,o,o,o` where `o` represents compute cabinets and `c` represents CDUs. This interleaving places CDUs centrally among their served cabinets to minimize coolant routing distances.

### River Zone (Storage I/O)

The River zone contains the Orion Lustre storage system with lower thermal density than compute.

| Parameter | Value |
|-----------|-------|
| River cabinets | 42 |
| River CDUs | 6 |
| CDU-to-cabinet ratio | 1:7 (one CDU per seven cabinets) |
| Cabinet dimensions | 2 x 1 grid cells |
| Layout | 8 columns of varying height (4-10 cabinets each) |

## Primary and Secondary Coolant Loops

The CDU operates two distinct flow loops that interface through a liquid-to-liquid heat exchanger.

### Primary Loop (Facility Water)

The primary loop transports cool water from the facility's HTW (Hot Thermal Water) system into the heat exchanger and returns warmed water back to the facility. This loop is entirely contained within the CDU chassis.

Primary loop components:
- **2W regulating valve**: PID-controlled mixing valve that regulates facility water flow into the heat exchanger for secondary temperature control
- **Butterfly valves**: Twelve-position valves for primary flow isolation and coarse flow tuning
- **Inline flowmeter**: Provides primary-side flow rate telemetry to the controller
- **Inlet/outlet sensors**: Pressure (P1, P2) and temperature (T1, T5) monitoring at water entry and exit points

### Secondary Loop (Cabinet Coolant / DECS)

The secondary loop, also called DECS (Datacom Equipment Cooling System), carries chilled coolant from the heat exchanger into compute cabinets, through component heatsinks, and back to the CDU. This propylene glycol secondary closed loop uses a propylene glycol-water mixture for corrosion protection.

Secondary loop components:
- **Redundant pumps**: Two variable-speed pumps share load continuously (not cycled); either can maintain flow if one fails
- **Expansion vessel**: Maintains loop pressure stability across operating temperature range
- **Makeup unit**: 6-gallon (22.7 L) reservoir with pump for system fill and active coolant injection
- **Secondary loop filter**: 74-micron screen filtering impurities
- **Pressure relief valve**: Over-pressure protection
- **Auto air vents**: Purge trapped air from the fluid loop
- **Redundant sensors**: Pressure (P3, P4, P5) and temperature sensors throughout

The differential pressure (dP) between warm and cold secondary streams controls pump speed. Flow rate is estimated from pressure sensors rather than using a dedicated flow meter.

## Coolant Routing

### Underfloor Distribution

Frontier uses underfloor water distribution for the HTW (Hot Thermal Water) and CHW (Chilled Water) systems. PP-R (polypropylene random copolymer) piping carries coolant through the raised floor plenum to each CDU. The facility designed this routing for future adaptability using flanged connections.

### Overhead Distribution

Electrical power distribution runs overhead, keeping electrical and water systems separated. Each compute rack receives 4 circuits (maximum 400 kVA per rack) via MC cable transitioning to fused flexible cord connections.

### CDU-to-Cabinet Connections

From each CDU, coolant travels through overhead piping (Top Feed Secondary Lines) to its cabinet cooling group. The secondary coolant enters cabinets through supply manifolds at the top, flows down through the cabinet's internal plumbing to component cold plates, and returns via return manifolds.

Within each cabinet:
1. Coolant travels through pipes and hoses to conduction plates and heatsinks
2. Components transfer heat to the secondary coolant via thermal interface material (TIM)
3. Warmed coolant returns to the CDU for heat exchange
4. The heat exchanger transfers heat to the primary (facility) water loop

## Component Connections

Frontier achieves >97% direct-to-water cooling by routing coolant to all major heat-generating components within each compute node.

### Cooled Components

| Component | Cooling Method |
|-----------|----------------|
| AMD EPYC 7A53 CPU | Direct liquid cold plate |
| AMD MI250X GPUs (4 per node) | Direct liquid cold plate |
| DDR4 DIMMs | Conduction plate cooling |
| Power supplies | Conduction plate cooling |
| Slingshot NICs | Direct liquid cooling |

All components use thermal interface material (TIM) between device heatsinks and conduction plates to enhance thermal coupling to the coolant.

### Temperature Targets

| Parameter | Value |
|-----------|-------|
| CPU/GPU/DDR4 case temperature range | 86-89°C |
| HTW supply temperature (nominal) | 29.4°C (85°F) |
| ASHRAE W32 inlet range | 5°C to 32°C (41°F to 89.6°F) |

## CDU Monitoring and Control

### Communication Architecture

The CDU integrates with the cabinet management system through:
- **RS-485 bus**: Connects to Cabinet Sensor Breakout Assembly (CSBA) and Cabinet Environmental Controller (CEC)
- **CDU Master**: By default, CMM1 in cabinet 0 (cooling group offset 0:0) serves as CDU master
- **Redfish API**: 52 telemetry metrics accessible via `/redfish/v1/Chassis/CDU`

### Control Signals

| Signal | Function |
|--------|----------|
| CDU_ENABLE | CEC requests CDU to start pumps |
| CDU_OK | CDU confirms operational status and sensor readings normal |
| CDU_EPO | Bidirectional Emergency Power Off signal |
| CDU_INT | Interrupt for warnings or alerts |

### Operational Features

- Any cabinet requesting power-up can start its CDU
- Cabinet cooling faults (leak, high pressure) can independently shut down the CDU
- Cabinets continuously verify CDU_OK signal; loss triggers shutdown after short delay
- CDU shuts down when no cabinets request operation (with delay for coolant cool-down)
- Bypass mode allows CDU operation without downstream load if dew point margin maintained

### Key Telemetry Points

The CDU PLC reports status bitmaps at 5 Hz including:
- Unit status (on/off)
- VFD alarms (pump 1, pump 2)
- Flow alarms (low flow P1, P2)
- Temperature alarms (high/low heat exchanger temps)
- Dew point warnings and alarms
- Pressure alarms (low suction, high filter delta-P)
- Water detection alarms
- Probe fault status

## Facility Integration

### Central Energy Plant Connection

Frontier's Central Energy Plant (CEP) manages the three-loop water system:

1. **HTW (Hot Thermal Water)**: Supplies CDUs at nominal 29.4°C (85°F)
2. **MTW (Medium Temperature Water)**: Supply at 69-71°F for intermediate cooling
3. **CHW (Chilled Water)**: Supply at 42°F for cooling tower makeup and facility support

The CEP targets:
- 40 MW heat rejection capacity
- 12,000 tons cooling
- 16,000 GPM total flow
- 1.05 first-year annualized PUE

### Electrical Distribution to CDUs

CDUs receive power through:
- 6 x 60A feeder breakers (3 CDUs per breaker)
- Metered at switchboard level with CDU sub-metering
- Two redundant power feeds (A+B) with automatic switching
- VFD (Variable Frequency Drive) control for pump speed regulation

### Known Electrical Challenges

The Frontier installation encountered CDU VFD DC bus voltage issues from harmonics generated by compute racks. Solutions applied:
- Added in-line chokes to VFDs
- Decreased transformer secondary voltage
- Single circuit supply when CDU has internal transfer switch

## Thermal Topology Relevance

This cooling distribution architecture directly impacts thermal modeling:

1. **Spatial coupling**: The 1:3 CDU-to-cabinet ratio creates thermal dependencies among cabinets sharing a CDU
2. **Loop dynamics**: Secondary loop response time affects thermal transient behavior during workload changes
3. **Control interactions**: CDU temperature and pressure setpoints interact with facility-level HTW control
4. **Failure propagation**: CDU faults affect entire cooling groups (up to 4 cabinets / ~500 nodes)
5. **Dew point management**: Condensation avoidance requires coordinated temperature control

## Related Notes

- [[hub]] - Frontier supercomputer main reference
- [[layout/data-center]] - Cabinet and CDU spatial relationships on the data center floor
- [[layout/facility-cooling]] - Facility-level cooling infrastructure (CEP, cooling towers, water loops)
- [[layout/compute]] - Cabinet and chassis architecture for compute nodes
- [[operations/cooling]] - Operational procedures and temperature management
- [[operations/cep]] - Central Energy Plant operational details
