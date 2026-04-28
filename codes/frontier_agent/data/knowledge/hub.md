# Frontier Supercomputer (OLCF)

Reference hub for domain knowledge about the Frontier supercomputer at Oak Ridge Leadership Computing Facility.

## Overview

| Topic | Note | Description |
|-------|------|-------------|
| System Overview | [[overview/overview]] | Architecture, specifications, performance history, Summit comparison, allocation programs |

## Physical Layout

| Component | Note | Description |
|-----------|------|-------------|
| Data Center | [[layout/data-center]] | Building E102 floor plan, Mountain/River zones, grid coordinates, feeder routing |
| Compute | [[layout/compute]] | Olympus cabinets, chassis, blades, node cards, xname encoding, cabinet grid |
| Cooling Distribution | [[layout/cooling-distribution]] | CDU placement, coolant loops, manifold piping, HTW/CTW circuits |
| Facility Cooling | [[layout/facility-cooling]] | Cooling towers, heat exchangers, chillers, pump systems, seasonal modes |
| Power Delivery | [[layout/power-delivery]] | Feeders, transformers, switchboards, MSB-to-cabinet mapping, rectifiers |
| Interconnect | [[layout/interconnect]] | Slingshot dragonfly topology, Rosetta switches, cable types, port allocation |
| Storage | [[layout/storage]] | Orion/Lustre architecture, River zone layout, BAS3 network switches |

## Operations

| Domain | Note | Description |
|--------|------|-------------|
| Applications | [[operations/applications]] | Science domains, ECP codes, GPU porting, workload characteristics |
| CEP and Facility | [[operations/cep]] | Central Energy Plant, chillers, cooling towers, BACnet/Metasys controls |
| Compute | [[operations/compute]] | CPU/GPU specs, power management, RAS, thermal limits, AGT diagnostics |
| Cooling | [[operations/cooling]] | CDU control, flow valves, temperature setpoints, seasonal operation modes |
| Interconnect | [[operations/interconnect]] | Slingshot operations, Cassini/Rosetta telemetry, congestion, adaptive routing |
| Job Scheduling | [[operations/job-scheduling]] | Slurm partitions, priority bins, walltime limits, backfill, allocation programs |
| Power | [[operations/power]] | PDU/MSB/rectifier monitoring, voltage regulation, load transients, telemetry paths |
| Storage | [[operations/storage]] | Orion/Lustre I/O patterns, quotas, NVMe burst buffer, energy characteristics |

## Telemetry

| Topic | Note | Description |
|-------|------|-------------|
| Hardware Topology | [[telemetry/hardware-topology]] | xname hierarchy, cabinet numbering, CDU hostnames, expansion timeline |
