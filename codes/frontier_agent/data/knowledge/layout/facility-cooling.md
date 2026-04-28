# Facility Cooling Layout

Facility-level cooling infrastructure and physical arrangement for the Frontier supercomputer, including cooling towers, heat exchangers, pump systems, piping, and the three-loop water architecture managed by the Central Energy Plant.

## Cooling Tower Array

### Physical Configuration

The cooling tower system comprises 20 individual cells arranged in 5 groups of 4 cells each.

**Design Specifications per Cell**:
- Capacity: 500-1,000 gpm (design target: 1,000 gpm per cell)
- Motor power: 50 hp fan motor
- Design type: Induced draft, direct counter flow
- Fan control: Variable frequency drives (VFDs) with Hz ramping to maintain setpoints

**4-Cell Group Specifications**:
- Weight per group: 85,820 lbs
- Seismic rating: SDS up to 1.34g
- Wind load rating: up to 119 psf
- Material: Stainless steel (selected after materials analysis comparing stainless, composite, and galvanized options)

### Tower Positioning

Cooling towers are located externally on elevated platforms adjacent to the CEP. The 5-group arrangement enables staged operation from 4 cells (idle) to 12-14 cells (design capacity).

### Cell Staging Logic

Cell staging is controlled via CTW return header pressure:
- High setpoint: ~36 psig (triggers stage-up)
- Low setpoint: ~31 psig (triggers stage-down)
- Minimum turndown: 500 gpm per cell

**Operational Modes by Cell Count**:

| Mode | Load (MW) | Cells Active | Notes |
|------|-----------|--------------|-------|
| Idle | 8 | 4 | Minimum operation |
| Normal | Variable | 4-9 | Load-dependent, limited-time mode |
| Peak | 28.7 | 6-12 | HPL and heavy workloads |
| Design | 40 | 12-14 | ~4 MW cooling capacity per cell group |

The staging logic is biased toward running more cells rather than fewer, with stage-up being quick and stage-down being slow. This bias improves temperature stability during load transients.

## Heat Exchanger Placement

### Economizer Heat Exchangers (EHX)

The CEP contains plate-and-frame heat exchangers that transfer heat between the CTW and HTW loops. These are staged based on system flow:

| Unit | Activation Threshold |
|------|---------------------|
| EHX-1 | Active normally |
| EHX-2 | Stages up at 2,000 gpm |
| EHX-3 | Stages up at 4,000 gpm |
| EHX-4 | Stages up at 6,000 gpm |

This staged approach allows fine-tuning of HTW return temperature across the full load range (8 MW to 40 MW).

### Cooling Distribution Units (CDUs)

CDUs are distributed throughout the data center floor:
- Total Frontier CDUs: 25 units
- TDS (Test/Development System) CDUs: 2 units
- Connection: 4-inch high temperature water lines
- Control mechanism: Modulates differential pressure via facility-facing control valve
- Control valve capacity: 280 gpm per CDU

Each CDU separates facility water (HTW) from direct-to-chip water (DECS), preventing compute-side coolant contamination from affecting facility systems.

### Rear Door Heat Exchangers (RDHX)

84 RDHXs (RDHX-71 to RDHX-171) on support racks capture air-side heat before it enters room air, maintaining the >97% direct-to-water cooling ratio.

## Pump Infrastructure

### HTW Pumps (HTWP-1 to HTWP-4, 4 total installed, 1-3 running)

**Location**: Central Energy Plant

**Specifications**:
- Type: Large vertical in-line centrifugal pumps
- Operation: Variable speed for supply regulation
- Staging: Up at 90% capacity, down at minimum flow
- Rotation: Based on runtime for even wear distribution

**Flow Rates**:
- Idle: 3,200-6,800 gpm
- Peak: 6,800 gpm
- Design: 16,000 gpm (with all 3 pumps)

### CTW Pumps (CTWP-1 to CTWP-4, 4 total installed, 1-3 running)

**Location**: Central Energy Plant

**Specifications**:
- Type: Large vertical in-line centrifugal pumps
- Purpose: Circulation of cooling tower water through heat exchangers
- Staging: Up at 90% capacity, down at minimum flow
- Control: Pressure regulation at cooling tower discharge

CTW pumps maintain static pressure at tower discharge, with dynamic setpoint reset based on HTW supply temperature.

### CHW Pumps

**Location**: Central Energy Plant (labeled CHWP-11 in facility diagrams)

**Purpose**: Chilled water circulation for trim mode cooling and facility support.

### Support Pumps

Additional pumps handle ancillary functions:
- Chemical treatment circulation
- Blow-down management
- Filtration and purification systems

## Piping Infrastructure

### Distribution Architecture

Water and electrical systems are routed through separate pathways:

**Underfloor Distribution**:
- HTW supply and return piping to compute racks
- CHW distribution for support systems
- Materials: PP-R (polypropylene random copolymer) for many circuits
- Stainless steel and composite materials for critical sections
- Flexible braided hoses for final connections to compute nodes

**Overhead Distribution**:
- Electrical power (480V/150A circuits to racks)
- MC cable to fused flexible cord transition
- Spare cable tray for future expansion

### Primary Headers

- Large-bore carbon steel or stainless steel for main headers
- Color-coded: Green for CTW/MTW, Blue/Green for CHW
- Flanged connections throughout
- 40% design margin for worst-case CDU demand

### Control Sensor Placement

Differential pressure (dP) sensors at CEP (system-wide) and data center (rack-level distribution).

## Water Loop Architecture

### Three-Loop System Overview

The CEP employs a three-loop thermal management system:

1. **CTW Loop**: Cooling Towers (20 cells) -> variable flow -> EHX 1-4
2. **CHW Loop**: 42°F supply -> trim cooling (when needed)
3. **HTW Loop**: CEP distribution (underfloor, 56-90°F) -> Compute Racks (CDUs)

### HTW (Hot Thermal Water) System

**Purpose**: Direct cooling of Frontier compute nodes

**Operating Parameters**:
- Supply temperature range: 56°F to 90°F (ASHRAE W32 standard: 41°F to 89.6°F)
- Operating baseline: 80°F
- Target nominal return: 29.4°C (85°F)
- CPU/GPU/DDR4 case temperature: 86-89°C

**Flow Characteristics** (design-point values):
- Idle flow: 6,000 gpm
- Maximum flow: 8,000 gpm
- Frontier tolerance: Supply temperature forgiving; primary concern is rate of change

### MTW (Medium Temperature Water) System

**Purpose**: Intermediate cooling loop for facility support

**Operating Parameters**:
- Supply temperature: 69-71°F
- Load response: 6 MW load swing correlates to 4.4°F MTW supply temperature increase over 2 minutes
- Used for auxiliary cooling when HTW cannot meet full load

### CHW (Chilled Water) System

**Purpose**: Facility cooling and trim mode operation

**Operating Parameters**:
- Supply temperature: 42°F
- Activation trigger: When HTW supply exceeds 67°F or HTW supply > MTW return
- Significant summer load contributor
- Minimal load in cool weather conditions

### CTW (Cooling Tower Water) System

**Purpose**: Heat rejection to atmosphere via cooling towers

**Operating Parameters**:
- Flow per cell: 500-1,000 gpm
- System pressure setpoints: 31-36 psig
- Direct loop from towers to economizer heat exchangers

### DECS (Datacom Equipment Cooling System)

**Purpose**: Propylene glycol secondary closed loop within compute racks for direct-to-chip cooling

Separated from facility HTW by CDU heat exchangers, preventing contamination crossover. Propylene glycol-water mixture provides corrosion protection.

## Waste Heat Path and Recovery Points

**Primary path** (>97% of compute heat): Compute Rack -> CDU -> HTW Loop -> Central HX -> Cooling Tower -> Atmosphere

**Trim mode path** (when ambient prevents towers from meeting 67°F): HTW Return -> CHW Trim HX -> Lower Temp HTW -> Data Center

**Air-side path**: Support Rack -> RDHX -> Water Loop -> Central HX -> Cooling Tower

### Potential Waste Heat Recovery Points

Potential recovery points:

1. **HTW Return Header**: Highest temperature water (up to 85°F) before cooling tower rejection
2. **Post-CDU Manifold**: Concentrated heat from compute racks before mixing
3. **HHTW Future System**: Design provisions for 158°F (70°C) supply

**Current Status**: No active waste heat recovery; all heat rejected through cooling towers. Flanged piping supports future retrofit.

### Temperature Dynamics

The system must handle rapid load transitions:
- Load swing range: 8 MW (idle) to 28 MW (peak) in less than one minute
- Non-HPL profiles: Power jumping from ~12 MW to ~24 MW
- Temperature control target: Maintain excursions within +/-5°F over 5-minute windows
- Primary challenge: Cooling tower staging causes largest temperature disruptions

## Instrumentation and Control Points

### Pressure Monitoring

- Yokagawa pressure transmitters for HTW, CTW, and basin level control
- Distributed around system to enable pressure-based control logic

### Flow Measurement

- Onicon Flow/BTU meters for energy calculations and trending
- Both vortex and magnetic flow meters deployed for redundancy
- Critical for cell staging decisions and minimum flow enforcement

### Temperature Sensing

- JCI temperature and humidity sensors at multiple locations
- OAT (Outdoor Air Temperature) sensor drives HTW setpoint calculation
- 30-second trended data available for analysis

### Control Integration

- Johnson Controls Metasys BMS with NAEs (Network Automation Engines) and FACs (Field Advanced Controllers)
- BACnet protocol for device communication
- Model Predictive Control (MPC) algorithm employed

## Future Expansion Capability

**HHTW System** (Higher Hot Thermal Water): Target 158°F (70°C) supply, 5°F dT, improves PUE and enables waste heat recovery.

**Scalability**: Modular 4-cell tower groups, flanged piping connections, spare cable tray, and underfloor piping sized for expansion.

## Related Notes

- [[operations/cep]] - Central Energy Plant infrastructure and mechanical systems
- [[operations/cooling]] - Cooling control systems and efficiency metrics
- [[operations/power]] - Electrical distribution and power management
- [[layout/data-center]] - Compute floor arrangement and rack placement
- [[layout/cooling-distribution]] - CDU-to-rack cooling distribution details
