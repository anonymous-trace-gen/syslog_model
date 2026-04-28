# Cooling Operations

Facility cooling and distribution system operations, control architecture, and thermal management for the Frontier supercomputer.

## Control System Architecture

### Building Management System

The facility uses a Johnson Controls Metasys-based building management system with hierarchical control:

- **NAEs (Network Automation Engines)**: Supervisory controllers coordinating data between BACnet devices and FACs
- **FACs (Field Advanced Controllers)**: Distributed controllers for specific devices/systems with independent control logic
- **Carel PLCs**: CDU-level controllers managing local setpoints and demand response

### Sensor Network

| Sensor Type | Vendor | Application |
|-------------|--------|-------------|
| Pressure transmitters | Yokogawa | HTW, CTW, basin level |
| Flow/BTU meters | Onicon | Energy calculations, control |
| Temperature/humidity | JCI | System-wide monitoring |
| Flow meters | Vortex + Magnetic | Redundant flow measurement |

### Control Hierarchy

Three-tier architecture:

1. **Central Plant Level**: Metasys BMS with supervisory logic
2. **CDU Level**: Carel PLCs managing local demand
3. **Rack Level**: CEC (Central Engineering Console) communication to CDUs

Three racks communicate to each CDU, with the CEC relaying cooling demand based on IT load and inlet temperatures.

## Control System Implementation

### Model Predictive Control (MPC)

MPC-influenced strategies for anticipatory cooling management:

- **Weighted Averaging**: Return temperatures from flow meters FM-11 through FM-14 are weighted rather than single-point measurement
- **Mode Command Logic**: CDU Global Mode automatically changes to match Valve Group Status, anticipating cooling needs from valve positions
- **Lead-Follow Configuration**: FCV-910 designated as "LEAD" for primary trimming delegation

### PID Loop Control

Two primary control loops at the CDU level:

**Flow Rate (dP) Loop**: Controls pump speed via differential pressure measurements. Setpoint reset based on HTW temperature supply.

**Temperature Loop**: Manages facility valve position and heat exchange with secondary loop. Dynamic setpoint calculation based on OAT.

### Valve Control and Deadbanding

- **Deadband Control**: Valves (FCV-910, FCV-911) show Command of 0.0% while Status reads 0.1-0.2% open, preventing valve chattering
- **Latch Status**: Software locks valves in specific states during rapid oscillation, requiring manual or conditional reset

## Response Latency and Dynamics

**Sub-Minute Load Transitions**: Handles transitions between idle (8 MW) and peak (28 MW) in less than one minute.

**Thermal Lag Behavior**: During HPL power spikes (90 MW to 105+ MW), return temperatures show delayed ramp-up. This thermal inertia provides natural damping.

**Flow Response Latency**: Flow rate adjustments in 10-15 minute stepped intervals rather than continuous modulation, preventing overshoot.

**Control Response Asymmetry**: Less responsive while outdoor wet bulb is increasing; more responsive when decreasing. Better response when secondary supply setpoints allow flow modulation throughout range.

System monitoring provides 30-second trended data, with custom trend graphs at 10-20 minute sampling intervals.

## Stability Challenges and Hunting Behavior

**Hunting Phenomenon**: Rapid CDU water demand requests create oscillation when control systems react faster than thermal inertia allows. HPL workloads with synchronized compute phases exacerbate this.

**Temperature Excursion Risk**: No thermal reservoir/buffer outside circulating system volume. Cooling tower staging is the largest disruption source.

**Hardware-Level Damping**: Valve deadbanding (0.1-0.2% leakage tolerance), valve latch status, stepped flow adjustments.

**Software-Level Control**: Weighted temperature averaging across multiple sensors, intentional response delays for sustained load verification, cell staging bias toward running more cells (slower stage-down).

Trend data shows aggressive pump speed steps (sudden drops to ~78 then recovery to ~94) during stabilization attempts.

## HTW Supply Temperature Management

**Design Philosophy**: Stable temperatures meeting cooling load 1:1 rather than maintaining specific setpoints.

**ASHRAE W32 Design Range**: Min 41F (5C), Max 89.6F (32C), Operating nominal 29.4C (85F). Dynamic setpoint calculated from outdoor air temperature (OAT).

### Observed Temperature Values (HPL Run, January 2024)

| Parameter | Value |
|-----------|-------|
| HTW Supply (HTWS) | 68.7F |
| HTW Return (HTWR) | 84.8F |
| Delta-T | 16.1F |
| MTW Supply (MTWS) | 68.4F |
| Average IT Air Inlet | 74.4F |

Heat exchanger return temps vary by flow meter (73.4F to 90.3F), indicating localized thermal variations within compute rows.

## Cooling Tower Staging

20 total cells in 5 groups of 4. Staging based on system pressure and flow measurements.

**Stage-Up**: Quick response when pressure threshold exceeded. **Stage-Down**: Slow, biased toward maintaining more active cells for stability. Both vortex and magnetic flow meters track conditions for staging decisions.

**CTW Flow Control**: Pressure-based PID with dynamic setpoint reset. Min/Max flow per cell enforced (500-1,000 gpm). Static pressure maintained at discharge side.

## Operational Parameters

### System Operating Modes

| Mode | Load (MW) | Flow (gpm) | HTW Pumps | EHX | CTW Pumps | Cooling Towers |
|------|-----------|-----------|-----------|-----|-----------|-----------------|
| Idle | 8 | 3,200-6,800 | 1 | 1 | 1 | 4 |
| Normal | Variable | Variable | 2 | 2-3 | 2 | 4-9 |
| Peak | 28.7 | 6,800-8,000 | 2-3 | 2-3 | 2-3 | 6-12 |
| Design | 40 | 16,000 | 3 | 3-4 | 3 | 12-14 |

4 total installed for each: HTWP-1 to HTWP-4, EHX-1 to EHX-4, CTWP-1 to CTWP-4.

### Three-Loop Water System

**HTW (Hot Thermal Water)**: Supply CPU/GPU/DDR4 at 86-89C. Target nominal 29.4C (85F). Variable speed pumps. >97% direct-to-water cooling.

**MTW (Medium Temperature Water)**: Supply 69-71F. Intermediate cooling loop for facility support.

**CHW (Chilled Water)**: Supply 42F. Cooling tower makeup and facility support. Summer-only major load contributor.

### CDU Specifications

- Frontier CDU count: 25 units; TDS CDU count: 2 units
- Piping: 4-inch connections; control via modulated differential pressure
- CDU control valve: 280 GPM; system total: 6,000 GPM idle / 8,000 GPM max
- Piping design margin: 40% headroom for worst-case CDU demand
- Olympus Racks: 70-80 GPM nominal, 75 GPM target
- Shasta Racks: 65-70 GPM nominal, 67 GPM target

### Cooling Tower Specifications

- 20 cells, induced draft, direct counter flow design
- 500-1,000 gpm per cell, 50 hp fan motors per cell
- 4-cell groups weigh 85,820 lbs each
- Seismic rating: SDS up to 1.34g; Wind load: up to 119 psf
- Stainless steel construction

## Seasonal Operation

### Winter (Economizer Mode)

Example conditions (January 2024): OAT 57.6-58.7F, RH 97.8-100.8%, Wet Bulb 58.3F.

"Econ-Trim" mode active. Cooling towers handle nearly entire load. Trim load on CHW only 8.3 tons vs HTW load 2,778.7 tons. Mechanical chillers effectively bypassed.

Cold weather basin management uses waste heat to maintain basin temps below 45F. HTW Return maintained at ~85F despite cold ambient.

### Summer

Automatic Mode Changeover between "Econ-Trim" and "Chilled Water Mode." Higher outdoor wet bulb reduces economizer effectiveness. PUE increases due to chiller operation.

## HPL Cooling Optimization

HPL (High Performance Linpack) presents unique cooling challenges: 2-hour runs with ~15-16 MW load swings, synchronized compute phases causing rapid CDU demand, transitions between idle and peak in <1 minute.

**Hybrid Cooling**: HTW handles primary compute load; "Trim CDU Mode" manages specific requirements. Compute power distributed across zones (5600 E102 Compute at ~8.5 MW vs I/O at ~1.0 MW).

**Control Behavior**: FCV-910 LEAD = True with tight deadband. Valve Latch Status and Fault Resets prevent hardware damage during rapid fluctuations.

**Performance**: PUE during HPL 1.06 (vs 1.058 instantaneous at part load). Thermal lag and stepped flow intervals prevent overshoot.

## PUE and Efficiency

Measurement infrastructure: 12 compute power meters, 16 facilities power meters, 4 flow meters, 5 estimates.

**Observed Values** (January 2024 HPL): Compute 8.568 MW, Support 1.032 MW, Total IT 9.600 MW, Total Facility 0.553 MW. **Instantaneous PUE: 1.058**. Cooling overhead accounts for ~6% of total power draw.

| System | Configuration | Efficiency (kW/ton) |
|--------|---------------|---------------------|
| CHW | 12-20F dT | 0.8 |
| MTW | 12-20F dT | 0.4 |
| HTW | 20-30F dT | 0.2 |

**PUE Targets**: First-year annualized 1.05; HPL runs 1.06 observed. Tracks Instantaneous, Trailing Month (Totalized), and Trailing Annual PUE.

## Related Notes

- [[hub]] - Frontier supercomputer main reference
- [[operations/cep]] - Central Energy Plant operations and infrastructure
- [[operations/power]] - Electrical power delivery and management
- [[layout/cooling-distribution]] - Physical cooling distribution layout
- [[layout/facility-cooling]] - Facility-level cooling infrastructure layout
- [[operations/compute]] - Compute operations and workload management
