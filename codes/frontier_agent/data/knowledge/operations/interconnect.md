# Interconnect Operations

Slingshot-11 network operations, telemetry, and performance characteristics for the Frontier supercomputer.

## Slingshot-11 Architecture

Frontier uses HPE's **Slingshot-11** interconnect, a purpose-built HPC network combining Ethernet compatibility with specialized HPC features.

### Cassini NIC (Network Interface Controller)

- 200 Gb/s Ethernet-based with HPC extensions
- Supports both Ethernet and proprietary HPC transport modes
- Hardware-based congestion control mechanisms
- Approximately 1,400 telemetry counters available per NIC
- 4 NICs per compute node providing 800 Gb/s aggregate bandwidth
- Effective injection bandwidth: ~100 GB/s per node

### Rosetta Switch ASIC

- 64-port switch fabric
- 200 Gb/s per port (12.8 Tb/s switching capacity)
- Hardware adaptive routing support
- RFC 3635 compliant counters (HCinOctets, packet rates)
- Port error event reporting

### Network Scale

- **9,856 compute nodes** (9,408 in production use at launch)
- **2,464 Rosetta switches** total (74 compute groups x 32 + 6 I/O/mgmt groups x 16)
- **80 dragonfly groups** total: 74 compute, 5 I/O (storage connectivity), 1 management
- **32 switches per compute group**
- Global bandwidth: 270+270 TB/s between compute groups

## Dragonfly Topology

Frontier implements a **three-hop dragonfly topology** optimized for cost efficiency while maintaining high bandwidth.

### Port Allocation per 64-port Rosetta Switch

- **16 L0 ports** (`cassini`): Connect to endpoints (NICs)
- **31 L1 ports** (`local`): Intra-group connectivity (full mesh within group)
- **~9 L2 ports** (`global`): Inter-group connectivity (global links)
- **~8 unused/mgmt** (`ieee`): Management network or unused

### Taper Ratio

The network implements a **57% global-to-injection taper ratio**:
- Reduces cable count and cost (~30% more cost efficient than equivalent fat-tree)
- Requires adaptive routing to distribute traffic
- Achieves ~30 GB/s/node all-to-all bandwidth in practice

### Routing Policies

**UGAL (Universal Globally Adaptive Load-balancing)**: Default routing algorithm. Dynamically selects between minimal and non-minimal paths using real-time queue depth information.

**Minimal Routing Bias**: Frontier configured with **5% bias away from minimal routing**, spreading traffic across multiple paths to reduce hotspot formation during collective operations.

**Adaptive Routing Behavior**:
- Under light load: primarily uses minimal (direct) paths
- Under congestion: automatically routes through intermediate groups
- GPCNeT benchmark shows identical isolated/congested performance at 8 processes per node

## XName Conventions for Network Components

| Component | XName Form | Example | Description |
|-----------|------------|---------|-------------|
| Switch | `x{NNNN}c{C}r{R}` | `x2011c6r1` | Router R in chassis C of cabinet NNNN |
| Switch port | `x{NNNN}c{C}r{R}j{JJJ}p{P}` | `x2011c6r1j100p0` | Port P on jack JJJ of the switch |
| Link | `x{NNNN}c{C}r{R}a{A}l{LL}` | `x2011c6r1a0l50` | Link LL on adapter A of the switch |
| Host port | `x{NNNN}c{C}s{S}b{B}n{N}h{H}` | `x2011c6s0b0n0h3` | NIC H on node N (each node has 4 NICs, h0-h3) |

The switch xname (`x{NNNN}c{C}r{R}`) shares the same cabinet/chassis namespace as compute nodes. The `r` segment distinguishes the router from compute blades (`s` segments) within the same chassis.

### Fabric Topology File

The authoritative fabric topology lives at `/opt/cray/fabric_template.json` on the fabric manager node. It contains:

- A list of **switch objects** with `edgePorts` (L0 to NICs) and `fabricPorts` (L1/L2 to other switches)
- A list of **link objects** with cable IDs, lengths, and routing paths
- `maxLocalSwcs`: maximum number of local switches (switches per dragonfly group)
- Number of switch groups (dragonfly groups)

There are 40,683 host-port-to-switch-port mappings across the system (9,408 nodes x 4 NICs = 37,632 compute connections, with the remainder covering service/login nodes).

## Network Telemetry

### Cassini NIC Metrics

Of approximately 1,400 available Cassini counters, **35 curated metrics** are collected operationally:

**Traffic Metrics**: HNI RX/TX paused metrics (buckets 0-7, 0-8), packet counts, byte counters, per-port bandwidth utilization.

**Stall Counters**:
- `ixe_dmawr_stall_fctch_amo_cnt`: DMA write stalls
- `ixe_dmawr_stall_np_cdt`: Non-posted credit stalls
- Various PCIe interaction stalls

**Error Metrics**: PCt (packet) timeouts and drops, RSP dropped packets, CLS drops, request/response error counts, ATU cache evictions.

**Counter Behavior**: Counters persist across warm resets (no cold/warm ASIC reset clears them).

### Rosetta Switch Metrics

**RFC 3635 Compliance**: HCinOctets (high-capacity input octets), packet rate counters, standard Ethernet MIB statistics.

**Slingshot-Specific**: Port error events, link status changes, congestion scores per port, adaptive routing decision counts.

### Collection Infrastructure

**Periodicity**: Minimum telemetry interval >= 1 second for all fabric agent metrics.

**Location Tagging**: Each metric includes port type classification (Local, Global, IEEE, CASSINI), network logical location (dragonfly coordinates: Group, switch, port), and physical location (system name: Rack, chassis, blade, port).

### CrayFabricPerfTelemetry Kafka Stream

Published to Kafka topic `stf002hpc.frontier.hpcm.slingshot_CrayFabricPerfTelemetry`. Each message contains a metric category (`name`), a single key-value measurement (`fields`), dimensional tags, and a timestamp.

**Metric Categories**:

| Category | Metrics | Description |
|----------|---------|-------------|
| Congestion | `idle_{ctx}`, `txBW_{ctx}`, `rxBW_{ctx}`, `rxCongestion_{ctx}`, `BlockedPercentage`, `BlockedRate`, `BlockedReason` | Per-port congestion and bandwidth utilization |
| PauseDetails | `txPausePercent_cassini`, `rxPausePercent_cassini`, PFC pause cycles per priority class (00-07) | Pause frame metrics (L0/Cassini ports only) |

Where `{ctx}` is `cassini`, `local`, `global`, or `ieee`, matching the port's `DeviceSpecificContext`.

**Tag Dimensions**: Each message is tagged with `Switch` (switch xname), `Location` (port xname), `DeviceSpecificContext` (port type), `Index`/`SubIndex`/`ParentalIndex` (port indices), and `PhysicalContext` (metric subcategory).

**Volume**: ~148K unique switch port locations, ~2,560 unique switches, ~28 distinct metric series per applicable port.

## Monitoring Infrastructure

### Trellis Analytics Framework

Real-time network monitoring for Slingshot. Correlates network telemetry with job performance, integrates MPI latency measurements with switch counters. Uses **OmniSciDB** columnar database. Produces congestion heatmaps by group/switch/port and identifies incast patterns.

### Data Pipeline

**Collection**: Switch controllers stream via Redfish. Fabric manager aggregates switch telemetry. LDMS with DVS/Cassini samplers.

**Transport**: **Kafka** message bus. Default retention: 7 days (crayex_telemetry: 1 day).

**Storage**: **ElasticSearch/OpenSearch** for events/logs. **TimeScaleDB** for time-series. Retention: 1, 7, 14, or 30 days.

**Visualization**: **Grafana** with HPE cluster view plugin. **ElasticAlert** for automated alerting.

## Congestion Management

### Hardware Congestion Control

Slingshot implements congestion control in hardware: real-time queue depth monitoring at switch ports, backpressure signaling to source NICs, per-flow credit management.

### Performance Variability

Network performance shows higher variance compared to fat-tree topologies:
- **MPIGraph benchmark**: Frontier variance 12.09 vs Summit (fat-tree) 0.04
- Variance stems from non-uniform path lengths in dragonfly
- Adaptive routing mitigates but does not eliminate variance
- Applications with regular communication patterns less affected

### Incast Handling

Common pattern in collective operations (many ranks writing to one). Hardware mechanisms throttle sources during congestion. Trellis visualizations reveal incast hotspots.

## Network Digital Twin

The **ExaDigiT Network Digital Twin (NDT)** integrates with RAPS to predict network performance alongside power/cooling models. System telemetry at 15-second intervals is aggregated into bins to bridge the gap with nanosecond-scale network switching (100-350 ns).

**SST Macro** (Structural Simulation Toolkit) provides discrete-event simulation supporting dragonfly, fat-tree, and 3D torus topologies with trace-driven replay. Outputs include Fixed-Time Quanta (FTQ), Spyplot communication matrices, and congestion heatmaps.

**Coupling Models**: (1) Capacity-only, (2) Topology-aware, (3) Slowdown coupling with full network effects on application performance.

## Operational Patterns

**Job Scaling**: As jobs scale across more nodes, communication patterns shift from intra-group to inter-group, global link utilization increases, adaptive routing becomes more critical, and latency may increase due to longer paths.

**Power Swing Correlation**: Network activity correlates with system power behavior. Collective operations cause synchronized NIC activity, and NIC power consumption varies with traffic load. Network telemetry provides early indicator of workload phase changes.

## Related Notes

- [[hub]] - Frontier supercomputer main reference
- [[layout/interconnect]] - Physical network topology and cabling
- [[operations/compute]] - Node-level telemetry integration
- [[operations/power]] - Network power correlation
- [[telemetry/hardware-topology]] - Hardware topology and xname conventions
