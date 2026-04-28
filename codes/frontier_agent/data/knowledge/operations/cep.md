# CEP Operations

Central Energy Plant (CEP) infrastructure, mechanical systems, and facility operations for the Frontier supercomputer.

## CEP Design and Capacity Overview

### Facility Scale

**Cooling System Specifications**:
- Heat capture: >97% direct-to-water cooling
- Target water temperature: ASHRAE W32 (41F to 89.6F / 5C to 32C)
- Facility targets:
  - Cooling capacity: 40 MW
  - Water flow: 12,000 tons / 16,000 gpm
  - Energy efficiency: 1.05 first-year annualized PUE

### Physical Footprint

- Total space: 4,000 ft2
- 77 compute cabinets (HPE Olympus design)
- 128 nodes per cabinet x 77 cabinets = 9,856 total nodes
- Weight per rack: 8,000 lbs
- Power per rack: 400 kW max capacity

## Water Systems Architecture

The CEP employs a three-loop thermal management system designed for efficiency and operational flexibility.

### HTW (Hot Thermal Water) System

**Purpose**: Direct cooling of Frontier compute nodes

**Design Parameters**:
- Supply to compute nodes: 86-89C (CPU/GPU/DDR4 case temperature)
- Return from nodes: Direct-to-water cooled
- Target nominal return: 29.4C (85F)
- Flow requirement: Variable based on load (observed operational range: 3,200-6,800 gpm at idle, up to 6,800 gpm at peak)

**Pump Control**:
- 1-3 variable speed HTW pumps depending on operational mode
- Supply regulation through variable speed operation
- Pressure-based control with dynamic setpoint reset

**Heat Rejection Path**:
- HTW cooled by economizer heat exchangers (EHX)
- EHX can stage 1-4 units based on load (4 total installed: EHX-1 to EHX-4)
- Rejection primarily to CTW (cooling tower water)

### MTW (Medium Temperature Water) System

**Purpose**: Intermediate cooling loop for facility support

**Design Parameters**:
- Supply temperature: 69-71F
- Used for facility support cooling
- Reduces load on HTW system during part-load conditions

### CHW (Chilled Water) System

**Purpose**: Facility cooling and cooling tower makeup water

**Design Parameters**:
- Supply temperature: 42F
- Used for cooling tower makeup and facility support
- Significant summer load contributor
- Minimal load in winter/cool months

## Cooling Infrastructure Components

### Cooling Towers

**Physical Specifications**:
- Total cells: 20 individual units (5 groups of 4 cells)
- Design type: Induced draft, direct counter flow
- Per-cell capacity: 500-1,000 gpm
- Motor power per cell: 50 hp fan motors
- Weight per 4-cell group: 85,820 lbs

**Structural Design**:
- Seismic rating: SDS up to 1.34g (earthquake load design)
- Wind load rating: up to 119 psf
- Material: Stainless steel (selected after materials analysis)
- Future-ready with flanged connections for adaptability

**Operational Modes**:
- Idle: 4 cells operating
- Normal: 4-9 cells (load dependent, limited-time mode)
- Peak: 6-12 cells
- Design capacity: 12-14 cells (~4 MW cooling each)

### Heat Exchangers

**Economizer HX Units (EHX-1 to EHX-4)**:
- 4 total installed, plate-and-frame design
- Staged operation: 1-4 units active based on cooling load
- Allows fine-tuning of HTW return temperature
- Critical for maintaining stable temperatures across load range

### Pumping Systems

**HTW Pumps (HTWP-1 to HTWP-4)**: 4 total installed, 1-3 running depending on mode
- Variable speed, VFD-controlled for supply regulation
- Pressure control on discharge side
- Provides HTW to compute nodes at required flow rate

**CTW Pumps (CTWP-1 to CTWP-4)**: 4 total installed, 1-3 running depending on mode
- VFD-controlled circulation of cooling tower water through heat exchangers
- Flow control for tower staging logic
- Pressure regulation at cooling tower discharge

**Support Pumps**:
- Chemical treatment circulation
- Blow-down management
- Filtration and purification

## Mechanical Design and Piping

### Distribution Piping

**HTW and CHW Distribution**:
- Underfloor water distribution to compute racks
- Overhead electrical distribution (separate from water)
- Materials: PP-R piping for many circuits with stainless steel and composite materials for critical sections
- Design considerations: Flanged connections for future adaptability
- Sizing: Large diameter piping to minimize pressure drop

### Instrumentation

**Pressure Monitoring**:
- Yokagawa pressure transmitters for HTW, CTW, and basin level control
- Distributed around system to enable pressure-based control logic

**Flow Measurement**:
- Onicon Flow/BTU meters for energy calculations
- Both vortex and magnetic flow meters deployed for redundancy
- Critical for:
  - Energy calculations and efficiency trending
  - Control logic for data center bypass valves (minimum flow)
  - Support for ASP-1 (Air Side Placement) enable logic
  - Cell staging decision logic

**Temperature Sensing**:
- JCI temperature and humidity sensors
- Multiple locations for HTW, MTW, CHW systems
- Support for dynamic setpoint calculation

## Construction and Commissioning

### Project Timeline

- **April 1, 2018**: Design start
- **Summer 2019**: Relocation and construction begins
- **March 2020**: COVID-19 pandemic impacts to schedule
- **October 2019**: Demo facilities 5600/5800, rebuild and expand phases
- **October 2019**: Pipe bridge construction
- **April 2021**: Lab relocation completed
- **June 1, 2021**: Rack ready for installation
- **August 23 to November 1, 2021**: Cabinet arrivals and rack population
- **May 30, 2022**: Achieved Top500 ranking (operational validation)

### Comparison to Summit (Predecessor)

| Metric | Summit (2018) | Frontier |
|--------|---------------|----------|
| Heat capture | 75% direct-to-water | >97% direct-to-water |
| CPU/GPU case temps | 86-89C | 86-89C |
| Water supply | 70F warm + 42.5F trim | ASHRAE W32 nominal 29.4C (85F) |
| Capacity | 20 MW / 7,700 tons / 3,300 gpm | 40 MW / 12,000 tons / 16,000 gpm |
| PUE | 1.10 annualized | 1.05 annualized |
| Footprint | ~13,000 ft2 | 4,000 ft2 |

Key improvements: higher inlet water temperatures reduce cooling power, nearly complete direct-to-water cooling (including network switches and memory modules), and water-cooled CDUs.

## HTW Supply Temperature Control Strategy

### Design Philosophy

**Stable Temperature Emphasis**: The system prioritizes stable, responsive temperature control over maintaining specific setpoints.

**ASHRAE W32 Design Range**:
- Minimum: 41F (5C)
- Maximum: 89.6F (32C)
- Operating nominal: 29.4C (85F)

### Temperature Management Challenges

**Disruption Sources**:
- Outdoor air temperature (OAT) changes
- Compute workload transients
- Cooling tower staging events (largest disruption)
- No thermal reservoir/buffer outside circulating system volume
- Large load changes can cause temperature excursions

### Dynamic Setpoint Calculation

**Control Logic**:
- Based on OAT sensor input
- Temperature setpoint compared against design conditions
- Dynamic adjustment supporting cooling load requirements
- Emphasis on 1:1 load matching rather than fixed temperature

**Cell Staging as Primary Disruption**:
- Switching cooling tower cells significantly impacts pressure and flow
- Stage-up is quick; stage-down is slow (biased toward more cells)
- Critical for control stability

## Known Construction Challenges

The CEP experienced 20 significant technical challenges during construction and commissioning. Notable issues include: factory CRAH solder joint defects, SCH10 stainless steel "egging" (deformation under pressure), 24-inch PP-R pipe rupture (~90 psig, required 150 LF replacement), cooling tower material selection, CDU tap repositioning by HPE, flow meter reliability issues, underfloor piping adaptability constraints, and CTW/building steel isolation concerns.

**Lessons Learned**: Detailed design review, vendor coordination, and field verification critical for exascale facility commissioning.

## Future Expansion Capability

### HHTW System (Higher Hot Thermal Water)

**Proposed Future System**:
- Target supply temperature: 158F (70C)
- Designed dT: 5F
- Efficiency: kW/ton TBD
- Use case: Further heat rejection temperature increase for improved facility PUE

### Scalability Considerations

- Flanged piping connections enable future reconfiguration
- Spare cable tray for electrical expansion
- Modular 4-cell cooling tower groups for staged expansion
- Underfloor piping sized to support expansion with adaptation

## BACnet Sensor Inventory

The CEP has ~4,038 BACnet sensors monitored via the Johnson Controls Metasys BMS. Major monitored equipment:

| Type | Count | Description |
|------|-------|-------------|
| RDHX | 84 (RDHX-71 to RDHX-171) | Rear-Door Heat Exchangers on support racks |
| THX | 3 (THX-1 to THX-3) | Trim Heat Exchangers with flow control valves |
| EHX | 4 (EHX-1 to EHX-4) | Economizer plate-and-frame heat exchangers |
| CDU | 25 Frontier + 2 TDS | Motivair 1.6 MW floor-standing, 800-9,500 W AC input each |
| CTWP | 4 (CTWP-1 to CTWP-4) | Condenser/Tower Water Pumps, VFD-controlled |
| HTWP | 4 (HTWP-1 to HTWP-4) | Hot Tower Water Pumps, VFD-controlled |
| CT cells | 20 (5 groups of 4) | Induced draft cooling tower cells, 50 hp fan each |
| VFDs | ~40 | Variable Frequency Drives for CT fans and pumps |
| MSBs | ~10 | Main Switchboards for power metering |

### Control System Integration

- Johnson Controls Metasys BMS with NAEs and FACs
- BACnet point database in CEP Metasys Points
- Sensor network driving control logic
- See [[operations/cooling]] for detailed control strategies

## Related Notes

- [[overview/overview]] - Frontier system overview and architecture
- [[layout/cooling-distribution]] - Cooling distribution layout and infrastructure
- [[layout/facility-cooling]] - Facility cooling layout
- [[operations/cooling]] - Detailed cooling control strategies and operations
- [[operations/power]] - Electrical infrastructure and power integration
