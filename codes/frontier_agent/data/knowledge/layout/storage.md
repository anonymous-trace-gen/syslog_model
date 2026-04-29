# Storage Layout

Physical arrangement and infrastructure topology of the Orion storage system within the Frontier data center, covering the River zone floor placement, CDU assignment, OSS node distribution, and network connectivity.

## River Zone Overview

The Orion Lustre storage system is housed in the **River zone** of the Frontier data center (Building E102). This zone is physically separated from the Olympus compute zone and operates at lower thermal density.

### Zone Specifications

| Parameter | Value |
|-----------|-------|
| Total River cabinets | 55 |
| I/O cabinets (Orion storage) | 42 |
| Switch cabinets | 5 |
| Service cabinets | 4 |
| ITDB cabinets | 3 |
| Storage management cabinets | 1 |
| River CDUs | 6 |
| RDHX units | 55 |

### Zone Boundaries

The River zone occupies a distinct rectangular area adjacent to the Olympus compute zone:

- **North boundary**: Borders Olympus compute zone (77 compute cabinets)
- **West boundary**: Adjacent to future expansion area (reserved for 74 additional Olympus cabinets)
- **Connection to compute**: Via Slingshot Dragonfly fabric

## Cabinet Physical Layout

### Grid Coordinate System

The River zone uses the same X/Y grid coordinate system as the broader Frontier facility:

| Axis | Range |
|------|-------|
| Rows | BS through CB (10 rows) |
| Columns | 08/09 through 53/54 (7 main columns plus RDF section) |

