# Compute Layout

Physical composition and layout of Frontier's compute infrastructure, from cabinet structure down to node-level component arrangement.

## System Scale

| Metric | Value |
|--------|-------|
| Olympus cabinets | 77 (expanded from 74 in Sep 2024) |
| Chassis per cabinet | 8 |
| Compute blades per chassis | 8 |
| Nodes per blade | 2 |
| Nodes per cabinet | 128 |
| Total chassis | 616 |
| Total compute nodes | 9,856 |

## Cabinet Configuration

### HPE Cray EX Olympus Cabinets

Frontier uses HPE Cray EX liquid-cooled cabinets (Olympus). The system does not use cabinet-level controllers; management occurs at the chassis level through Chassis Management Modules (CMMs).

**Cabinet Physical Organization**:
- Chassis are arranged vertically in pairs: 0/1, 2/3, 4/5, 6/7 (bottom to top)
- Front side: Compute blades with overhead coolant plumbing
- Rear side: Switch blades, CMMs, and Cabinet Environmental Controllers (CECs)
- Each chassis has 8 compute blade slots (0-7) on the front and 8 switch blade slots (0-7) on the rear

