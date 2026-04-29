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

