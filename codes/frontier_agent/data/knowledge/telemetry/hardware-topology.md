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

