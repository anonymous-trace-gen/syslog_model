# Cooling Distribution Layout

Coolant Distribution Units (CDUs) and how HPE distributes coolants to components in the Frontier supercomputer.

## CDU Overview

The floor-standing Coolant Distribution Unit (CDU) is the heart of Frontier's direct liquid cooling system. Each CDU pumps coolant to HPE Cray EX cabinets through overhead plumbing (the secondary coolant loop), supplying 1 to 4 cabinets per unit (a cabinet cooling group). The CDU regulates coolant flow rate and temperature while compensating for variations in facility water temperature.

Beyond cooling, each CDU rack also houses the top-of-rack (ToR) leaf switches that aggregate all management network links for its entire cabinet cooling group.

### CDU Models

Frontier uses floor-standing CDUs manufactured by Motivair. HPE Cray EX systems support two CDU capacities:

| Model | Heat Capacity | Water Flow | Weight | Power |
|-------|---------------|------------|--------|-------|
| 1.2 MW CDU | 1.2 MW | Up to 240 GPM | 2,400 lbs (1,089 kg) | 16 kW max |
| 1.6 MW CDU | 1.6 MW | Up to 380 GPM | 2,740 lbs (1,242 kg) | 17.64 kW max |

Observed CDU AC input power from telemetry ranges from 800 W to 9,500 W per unit, depending on pump speed and cooling demand.

