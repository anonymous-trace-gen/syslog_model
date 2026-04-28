# Frontier Hardware Topology

Frontier system overview and physical topology for interpreting telemetry datasets.

- **9,856 compute nodes** as of Sep 2024 (616 chassis x 16 nodes; see expansion timeline below)
- **Each node**: 1x AMD EPYC 7A53 CPU + 4x AMD MI250X GPUs
- **Node power range**: ~430W idle to ~2750W full load
- **System power**: 7.7-9.9 MW from chassis rectifiers (does not include cooling plant)
- **Cooling**: 25 CDUs, liquid-cooled nodes
- **Interconnect**: HPE Slingshot 11, dragonfly topology, 4 Cassini NICs per node (800 Gbps/node)
- **Switches**: 4 Rosetta switch blades per chassis (32 per cabinet = 1 dragonfly group)
- **Telemetry interval**: 15 seconds (some sensors at 2s or 1min)
- **Partitioning**: hive-style `date=YYYY-MM-DD/` partitions, one day per partition

## XName Format and Physical Topology

Every component in Frontier is identified by an **xname**, an HPE CrayEX hierarchical
naming scheme that encodes physical location. The xname for a node looks like:

```
x2509c4s4b1
^^^^|^|^|^
|||||| | └── b: board index within blade (0-1), 1:1 with node
|||||| └──── s: slot where blade is inserted (0-7)
||||└─────── c: chassis index within cabinet (0-7)
└──────────── x: cabinet number (encodes row and column)
```

Raw CrayEX telemetry sometimes includes a trailing `n0` suffix (e.g., `x2509c4s4b1n0`).
This is not meaningful for Frontier and is stripped during ingestion. All datasets in the
lake use the four-level form `x{NNNN}c{C}s{S}b{B}`.

### Cabinet Number to Row/Col

The cabinet number encodes grid position:

```
cabinet_number = 2000 + (row * 100) + col
```

To decode: `row = (N - 2000) // 100`, `col = (N - 2000) % 100`. For example,
`x2509` is row 5, col 9.

### XName Segments to Dataset Columns

| XName segment | Dataset column | Range | Physical meaning |
|---------------|----------------|-------|------------------|
| `x{NNNN}` | `row`, `col` | row 0-6, col 0-11 | Cabinet position in floor grid |
| `c{C}` | `chassis` | 0-7 | Chassis within cabinet |
| `s{S}` | `blade` | 0-7 | Slot where blade is inserted |
| `b{B}` | `node` | 0-1 | Board within blade (one node per board) |

CDU and chassis xnames are truncated to the relevant level:

| Component | XName form | Example | Columns present |
|-----------|------------|---------|-----------------|
| Node | `x{NNNN}c{C}s{S}b{B}` | `x2509c4s4b1` | row, col, chassis, blade, node |
| Chassis | `x{NNNN}c{C}` | `x2509c4` | row, col, chassis |
| CDU | `x{NNNN}c{C}` | `x2509c4` | row, col (CDU shares xname with adjacent chassis) |

### Cabinet Grid

Frontier has 77 liquid-cooled EX compute cabinets (as of Sep 2024; originally
74) and 3 standard racks for I/O and management switches. The compute cabinets
occupy a 7-row by 12-column floor grid. Four CDU columns (a, b, c, d) sit in
aisles between cabinet columns, dividing the floor into four cooling zones of
three cabinet columns each. 79 of the 84 possible grid positions have active
cabinets (77 compute plus 2 non-compute; the third non-compute rack is located
outside the main grid):

```
        col: 0  1  2  3  4  5  6  7  8  9  10 11
row 0:       x  x  x  x  x  x  x  x  x  x  x  x   (12)
row 1:       x  x  x  x  x  x  x  x  x  x  x  x   (12)
row 2:       x  x  x  x  x  x  x  x  x  x  x  x   (12)
row 3:       x  x  x  x  x  .  x  x  x  x  x  x   (11, col 5 missing)
row 4:       x  x  x  x  x  x  x  x  x  x  x  x   (12)
row 5:       x  x  x  x  x  x  x  x  x  x  x  x   (12)
row 6:       x  x  x  .  .  .  .  .  .  x  x  x    (6, sparse)
```

Cross-section of one row showing CDU column placement (not to scale):

```
 0  1  2 [a] 3  4  5 [b] 6  7  8 [c][d] 9  10  11
```

CDU columns c and d are co-located between cabinet columns 8 and 9.

| CDU col | Physical position    | Cools cabinet cols | XName col |
|---------|----------------------|--------------------|-----------|
| a       | Between col 2 and 3  | 0, 1, 2            | 2         |
| b       | Between col 5 and 6  | 3, 4, 5            | 3         |
| c       | Between col 8 and 9  | 6, 7, 8            | 6         |
| d       | Between col 8 and 9  | 9, 10, 11          | 9         |

25 CDUs serve the full system at a 1:3 CDU-to-cabinet ratio.

Each cabinet is powered by a Main Switchboard (MSB). Ten MSBs (MSB8-14 for the
east half, MSB24-27 for the west half) distribute 480 Vac from the facility;
see [[layout/power-delivery]] Stage 0 for the full MSB-to-cabinet mapping.

77 compute cabinets, 8 chassis each, 8 slots per chassis, 2 nodes per slot = 9,856
node slots (as of Sep 2024). The 2 non-compute grid positions and 1 off-grid rack
house TOR switches for I/O and management dragonfly groups (see
[[layout/interconnect]] for details).

### System Expansion Timeline

Three cabinets were added to row 6 (col 0, 1, 2) over April-September 2024,
growing the system from 592 to 616 chassis (9,472 to 9,856 nodes). All new
chassis are in row 6. Dates are first telemetry appearance in `power_aggregate`.

| Date | Chassis added | Cabinets | Cumulative chassis | Cumulative nodes |
|------|--------------|----------|-------------------|-----------------|
| (initial) | -- | 74 (rows 0-5 full, row 6: col 9,10,11) | 592 | 9,472 |
| 2024-04-16 | r6c1s0-s7, r6c2s0-s3 | +1.5 (col 1 full, col 2 half) | 604 | 9,664 |
| 2024-08-23 | r6c2s4-s7 | +0.5 (col 2 completed) | 608 | 9,728 |
| 2024-08-29 | r6c0s2-s5, r6c0s7 | +0.6 (col 0 partial) | 613 | 9,808 |
| 2024-09-12 | r6c0s0, r6c0s1, r6c0s6 | +0.4 (col 0 completed) | 616 | 9,856 |

Stable at 616 chassis from Sep 2024 through end of 2025.

### CDU Hostname Mapping

Each CDU has a logical ID (used in facility management) and an xname (used in
telemetry). All 25 CDU xnames end in `c1`, placing them at chassis index 1 within
their cabinet. Rows 0-5 each have four CDUs (one per CDU column); row 6 has a
single CDU in column d.

| CDU ID | XName | Row | CDU col |
|--------|-------|-----|---------|
| `cdu200` | `x2002c1` | 0 | a |
| `cdu201` | `x2003c1` | 0 | b |
| `cdu202` | `x2006c1` | 0 | c |
| `cdu203` | `x2009c1` | 0 | d |
| `cdu210` | `x2102c1` | 1 | a |
| `cdu211` | `x2103c1` | 1 | b |
| `cdu212` | `x2106c1` | 1 | c |
| `cdu213` | `x2109c1` | 1 | d |
| `cdu220` | `x2202c1` | 2 | a |
| `cdu221` | `x2203c1` | 2 | b |
| `cdu222` | `x2206c1` | 2 | c |
| `cdu223` | `x2209c1` | 2 | d |
| `cdu230` | `x2302c1` | 3 | a |
| `cdu231` | `x2303c1` | 3 | b |
| `cdu232` | `x2306c1` | 3 | c |
| `cdu233` | `x2309c1` | 3 | d |
| `cdu240` | `x2402c1` | 4 | a |
| `cdu241` | `x2403c1` | 4 | b |
| `cdu242` | `x2406c1` | 4 | c |
| `cdu243` | `x2409c1` | 4 | d |
| `cdu250` | `x2502c1` | 5 | a |
| `cdu251` | `x2503c1` | 5 | b |
| `cdu252` | `x2506c1` | 5 | c |
| `cdu253` | `x2509c1` | 5 | d |
| `cdu263` | `x2609c1` | 6 | d |

The CDU ID encodes position: the hundreds digit is the row, the tens digit
identifies the CDU column (0=a, 1=b, 2=c, 3=d). XName columns 2, 3, 6, 9
correspond to CDU columns a, b, c, d respectively.

## Related Notes

- [[layout/data-center]] - Facility floor plan, zone layout, and equipment placement
- [[layout/compute]] - Cabinet architecture, blade composition, and xname conventions
- [[layout/cooling-distribution]] - CDU systems and liquid cooling distribution
- [[layout/power-delivery]] - Power delivery stages and MSB-to-cabinet mapping
- [[layout/interconnect]] - Slingshot fabric topology and switch configuration
- [[overview/overview]] - Frontier system overview and key specifications
