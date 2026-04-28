---
name: frontier-diagnosis
description: >
  Diagnose Frontier supercomputer system failures from syslog entries,
  error messages, and operator reports. Triage the failure domain, identify
  affected components, trace causal chains, and recommend actions.
---

# Frontier System Diagnosis

You are diagnosing a system event on the Frontier supercomputer at OLCF.
Follow this procedure to analyze the input and produce a structured diagnosis.

## Step 1: Read the Hub Note

Start by reading the hub note ("Frontier Supercomputer (OLCF)") using the
`read_note` tool. This gives you the map of all Frontier domain knowledge.

## Step 2: Identify the Domain

From the input (syslog entries, error messages, or operator description),
determine which operational domain(s) are involved:

- **Power**: Rectifier faults, voltage drops, MSB issues, PDU failures
- **Cooling**: CDU alerts, temperature spikes, coolant flow anomalies
- **Compute**: GPU/CPU errors, RAS daemon events, node health failures
- **Interconnect**: Slingshot link errors, fabric congestion, NIC failures
- **Storage**: Orion/Lustre I/O errors, metadata server issues
- **CEP**: Central Energy Plant mechanical systems, chiller faults
- **Job Scheduling**: Slurm allocation failures, node drain events

## Step 3: Load Domain Knowledge

Use `read_note` to load the relevant operations note(s) for the identified
domain. Follow wikilinks (`[[Note Name]]`) to dig deeper into related topics.

Use `search_notes` if you need to find information across domains or locate
specific technical details.

## Step 4: Parse Component Identifiers

Frontier uses xnames to identify physical components. Parse any xnames in the
input to determine physical location:

```
x{NNNN}c{C}s{S}b{B}
  |      |   |   |
  |      |   |   +-- board/node (0-1)
  |      |   +------ blade slot (0-7)
  |      +---------- chassis (0-7)
  +----------------- cabinet (row*100 + col + 2000)
```

To decode cabinet position: `row = (N - 2000) // 100`, `col = (N - 2000) % 100`

## Step 5: Trace the Causal Chain

Work through the failure sequence:
1. What triggered the initial event?
2. What components are directly affected?
3. What downstream systems could be impacted (cross-domain effects)?
4. Is this an isolated failure or part of a pattern?

## Step 6: Classify Severity

- **Critical**: Multiple cabinets affected, potential data loss, safety risk
- **High**: Full cabinet or major subsystem down, significant compute loss
- **Medium**: Single chassis or node group affected, partial degradation
- **Low**: Individual node or component, minimal impact

## Step 7: Recommend Actions

Based on the diagnosis, suggest concrete operator actions. Reference specific
Frontier operational procedures where applicable.
