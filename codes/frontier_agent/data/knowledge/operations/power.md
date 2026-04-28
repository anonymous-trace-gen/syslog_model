# Power Operations

Power delivery operations, monitoring, and management for the Frontier supercomputer at OLCF.

## Power Specifications

| Parameter | Value |
|-----------|-------|
| Peak IT Load | ~29 MW |
| Design Capacity | 40 MW |
| Idle Power | ~7-8 MW |
| Support Systems | ~0.8 MW (capacity ~1.5 MW) |
| Transformer Capacity | 36 MVA |
| Power Factor | 0.998 |
| Total System Capacity | 30,265.77 KVA / 29,463.60 KW |

| State | Power Level | Notes |
|-------|-------------|-------|
| Idle/Low Load | ~7-8 MW | Baseline system draw |
| Average Operation | ~13.9 MW | Typical mixed workload |
| HPL Benchmark | ~21-23 MW | Peak during Linpack runs |
| Design Maximum | 40 MW | Electrical infrastructure limit |

## Power Quality

VTHD: 3.2%, ITHD: 6.5%, Power Factor: 0.998. Frontier's power supplies generate unique high-frequency harmonics creating a characteristic "warble" effect (beat frequency) from alternating CPU/GPU computational cycles.

**CDU VFD issue**: Harmonics cause VFD DC bus voltage threshold exceedances. Fixed with in-line chokes, decreased transformer secondary voltage, and single circuit supply for CDUs with internal transfer switches.

**LED flicker**: 7.6 MVA swings over 3 cycles at 13.8kV cause voltage fluctuations affecting facility LED lighting. Fixed by separating LED circuits from HPC power feeders and adding UPS backup on lighting circuits.

## Load Transients

| Parameter | Value | Notes |
|-----------|-------|-------|
| Maximum Swing | 7.6 MVA | Over 3 cycles at 13.8kV |
| Thermal Response Capability | 18 MW | Power swing range for cooling response |
| Ramp Rate | Near-instantaneous | 10 MW to 20+ MW transitions observed |

| Workload | Load Swing | Duration | Characteristics |
|----------|-----------|----------|-----------------|
| HPL (Linpack) | ~15-16 MW | 2h 38m | PUE ~1.06 during run |
| DGEMM | ~18 MW | Variable | Larger draw than HPL |
| Pennant | Intermittent | - | Sharp spikes, sawtooth pattern |
| Idle | ~8 MW | - | Baseline load |

Swing patterns: sawtooth (HPL tuning), decay slopes (large-scale jobs over hours), rapid transients (~10 MW to 20+ MW nearly instantaneously).

## Distribution Architecture

### Feeders and Transformers

- 2 new 13.8kV/1200A + 2 reused 13.8kV/600A overhead feeders from 161kV substation
- 8 reused transformers (2.5/3.3 MVA and 3.0/4.0 MVA) + 4 new transformers (3.0/4.0 MVA, 99.54% efficiency at 50% load)
- All FR3 oil-filled with containment

### Switchboards and Rack Distribution

- 480Y/277V/5000A with 5000A copper busway
- 36x 150A feeder breakers (9 compute racks each), 6x 60A feeder breakers (3 CDUs each)
- 4 circuits per compute rack, 480V/150A, max 400 kVA per rack
- Per-rack power: 399.05 KVA / 391.09 KW (Olympus cabinets)

### Cabinet Inventory

| Equipment Type | Count | Power Factor |
|----------------|-------|--------------|
| Olympus Compute Cabinets | 77 | 0.98 |
| River Cabinets (I/O, Switch, Service) | 55 | 0.95 |
| Olympus CDUs (1.6 MW) | 25 | - |
| MCDU-40 Units | 6 | - |

### Chassis Rectifiers

Four rectifiers per chassis convert 480 Vac to 380 Vdc for 8 compute blades (16 nodes), 4 switch blades, and the CMM. N+1 redundant configuration.

### SuperIVOC (Node-Level Conversion)

One SuperIVOC per node converts 380 Vdc to 48V for all node components. This is the single measurement point for total node power.

| Parameter | Value |
|-----------|-------|
| Max output power | 3,200 W (3.2 kW) |
| Max output current | 66 A |
| Efficiency | 96.5% |
| Input voltage | 380 Vdc |
| Output voltage | 48 V |

### PDB E-Fuse Architecture

The PDB sits between SuperIVOC and node card, using LM5066i hot-swap controllers (E-Fuses) for soft-start sequencing, overcurrent protection, and I2C telemetry. Five 48V cables: 4 GPU cables (one per MI250X, each with E-Fuse) and 1 CPU/memory cable (splits to 48V-to-POL for CPU Vcore and 48V-to-12V NBM for other circuits).

### Node Power Budget (at SuperIVOC input)

| Component | TDP | Notes |
|-----------|-----|-------|
| GPU (x4 packages) | 4 x 500 W = 2,000 W | AMD spec TDP 560W; max 569W for cabinet rollup |
| CPU (AMD Trento) | 280 W | Bard Peak budget (AMD spec TDP 400W) |
| Memory (8 DIMMs) | 50 W | DDR4, 6.25W each |
| NMC (x2) | 100-156 W | Sawtooth NMC with Cassini ASIC |
| SMC (x1) | 39-50 W | Storage Mezzanine Card |
| **Max node power** | **2,683 W** | |

MUS per cabinet: 391 kW (400 kW design max provides transient headroom).

### Chassis Power Decomposition

```
rect_output = node_power + board_power + unaccounted
node_power:   SuperIVOC input (GPUs, CPU, memory, NICs, storage)
board_power:  OOB controllers (~99 W/node, powered via CMMs)
unaccounted:  CMM, 4 Rosetta switch blades, fixed loads (~2,500 W/chassis)
```

Idle baseline (2025 yearly avg, 613 chassis, 339 days):

| Component | Per Chassis | Per Node | Share |
|-----------|------------|----------|-------|
| Rectifier AC input | 12,356 W | 772 W | -- |
| Rectifier DC output | 11,908 W | 744 W | 100% DC |
| Node power (SuperIVOC) | 8,133 W | 512 W | 68.3% |
| Board power (OOB ctrl) | 1,564 W | 99 W | 13.1% |
| Unaccounted | 2,211 W | 138 W | 18.6% |

Rectifier efficiency at idle: 96.4%.

## Telemetry

### Collection Path

```
PDB E-Fuse / VR -> SMBUS/I2C -> nFPGA (Spartan6/7, 11 I2C masters)
  -> K64 (MK64FN1M0VMD) -> iLO 5 BMC -> Kafka (crayex_telemetry, Avro, ~60 GiB/day)
```

Sampling: 2s SuperIVOC power, 15s VR outputs, 1min energy counters and temperatures.

### XNAME Power Hierarchy

| Level | Pattern | Example |
|-------|---------|---------|
| Cabinet | `xX` | `x2500` |
| Chassis | `xXcC` | `x2500c3` |
| Slot | `xXcCsS` | `x2500c3s0` |
| Node Card | `xXcCsSbB` | `x2500c3s0b0` |
| Node | `xXcCsSbBnN` | `x2500c3s0b0n0` |
| GPU | `xXcCsSbBnNaA` | `x2500c3s0b0n0a1` |

Power-specific XNAMEs: `dD` (CDU, 1 per 6 cabinets), `xXmM` (PDU controller), `xXmMpP` (PDU), `xXmMpPjJ` (outlet), `xXm0pPvV` (power connector), `xXeE` (CEC), `xXcCtT` (rectifier, T:0-2 for 4 physical units).

### Data Sources and Validation

- **Redfish API**: Hierarchy mapping and rough rack power (requires index mapping for XNAME correlation)
- **CEC paths**: `/var/volatile/cec[0-1]/rectifiers/chassis*/rect*/power` (granular), `/var/volatile/cec/rectifiers/total_cab_power` (aggregate, more accurate than Redfish)
- **Message types**: Power index 0 (node power), Power index 2 (PDB INRUSH CPU), Temp, Current
- **Tools**: SIVOC (index-to-component mapping), Bard Peak (analysis dashboard)
- **Metering**: 12 space-level compute meters, 16 facilities meters, 4 flow meters, 5 calculated estimates

CEC rectifier data is the authoritative source for total cabinet draw.

## Efficiency

| Metric | Value |
|--------|-------|
| PUE target (annualized) | 1.05 |
| PUE during HPL | 1.06 |
| Green500 ranking at launch | #1 (52.23 GFLOPS/W) |
| Linpack per-cabinet draw | 294-300 kW |
| Linpack operating temp | 65F |

Largest facility power consumers: cooling tower fans (variable with cell staging), CHW system (summer only).

## UPS and Backup

- Flywheel-backed UPS on one side of dual-corded support circuits, 0.8 MW (est. 1.5 MW redundant capacity)
- Compute systems have no traditional UPS/generator backup; availability via redundant distribution
- SCCR: 100 kA system, >65 kA rack fuses
- QA: torquing, micro-ohm resistance, visual inspection, lock-out/tag-out procedures

## Related Notes

- [[hub]] - Frontier system overview and entry point for all subsystems
- [[layout/power-delivery]] - Physical layout of power delivery infrastructure
- [[operations/cooling]] - Cooling operations, largest facility power consumer, must respond to power transients
- [[operations/compute]] - CPU/GPU workload characteristics driving power consumption patterns
- [[telemetry/hardware-topology]] - XNAME hierarchy and component naming conventions
