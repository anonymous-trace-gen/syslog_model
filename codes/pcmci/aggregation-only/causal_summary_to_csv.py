"""
Convert causal_summary.txt to a clean CSV file.
"""
import csv
import re
from pathlib import Path

INPUT  = Path("/lustre/orion/gen150/proj-shared/alz/aggregation-only/pcmciplus-results/causal_summary.txt")
OUTPUT = Path("/lustre/orion/gen150/proj-shared/alz/aggregation-only/pcmciplus-results/causal_summary.csv")

links = []

with open(INPUT) as fh:
    for line in fh:
        # Match data lines: CAUSE  LAG  EDGE  EFFECT  VAL  P-COMB  VOTES
        # Example:
        # GPU_RAS_FAIL                      3    -->  GPU_MEM_FAULT                     0.0608    0.00e+00      28
        m = re.match(
            r"^\s*(\S+)\s+(\d+)\s+([\-\<\>]+)\s+(\S+)\s+([-\d.e+]+)\s+([\d.e+\-]+)\s+(\d+)\s*$",
            line
        )
        if m:
            links.append({
                "cause":   m.group(1),
                "tau":     int(m.group(2)),
                "edge":    m.group(3),
                "effect":  m.group(4),
                "val":     float(m.group(5)),
                "p_comb":  float(m.group(6)),
                "n_votes": int(m.group(7)),
            })

print(f"Parsed {len(links):,} links")

with open(OUTPUT, "w", newline="") as fh:
    writer = csv.DictWriter(fh, fieldnames=["cause","tau","edge","effect","val","p_comb","n_votes"])
    writer.writeheader()
    writer.writerows(links)

print(f"CSV → {OUTPUT}")