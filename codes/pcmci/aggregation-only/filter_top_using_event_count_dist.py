"""
Filter and rank causal links using event-count-aware scoring.

Logic:
  - Every event is classified by rarity from the actual telemetry counts.
  - The MAXIMUM POSSIBLE VOTES for an edge is determined by how many nodes
    observed the rarer of the two events (cause or effect).
  - A link's vote_fraction = n_votes / max_possible_votes  (not / total_groups).
    This means a rare-event link seen by 3 out of 3 possible groups scores
    vote_fraction=1.0, same as a common link seen by 1080/1080 groups.
  - p-value threshold is tightened for low max_possible_votes to compensate
    for the lower statistical power available.
  - Final score = vote_fraction * (-log10(p_comb))
  - Both tiers (common + rare) are ranked by the same score and merged into
    one unified list.

Outputs:
  top_links.txt   — human-readable ranked table
  top_links.csv   — full machine-readable output
"""
import json
import math
import csv
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────
CAUSAL_GRAPH = Path("/lustre/orion/gen150/proj-shared/alz/aggregation-only/pcmciplus-results/causal_graph.json")
EVENT_CSV    = Path("/lustre/orion/gen150/proj-shared/alz/aggregation-only/pcmciplus-results/event_count_distribution.csv")
OUTPUT_TXT   = Path("/lustre/orion/gen150/proj-shared/alz/aggregation-only/pcmciplus-results/top_links.txt")
OUTPUT_CSV   = Path("/lustre/orion/gen150/proj-shared/alz/aggregation-only/pcmciplus-results/top_links.csv")

GROUP_SIZE   = 8      # nodes per group — must match what was used in PCMCIplus run

# ── P-value thresholds per rarity tier ───────────────────────────────────
# Rarer events need stricter p-value to compensate for lower power.
# These are applied to the combined p_comb value.
P_THRESHOLD = {
    "ZERO":       None,    # never seen — skip entirely
    "ULTRA_RARE": 1e-4,    # very strict: must be undeniable
    "RARE":       1e-3,    # strict
    "MODERATE":   5e-3,    # moderately strict
    "COMMON":     1e-2,    # standard alpha
    "VERY_COMMON":1e-2,    # standard alpha
}

# ── Load event count distribution ────────────────────────────────────────
event_info = {}   # event -> {total_count, nodes_with_event, rarity}
with open(EVENT_CSV) as fh:
    for row in csv.DictReader(fh):
        event_info[row["event"]] = {
            "total_count":      int(row["total_count"]),
            "nodes_with_event": int(row["nodes_with_event"]),
            "rarity":           row["rarity"],
        }

print(f"Loaded event info for {len(event_info)} events")

# ── Compute max possible votes for each event ─────────────────────────────
# max_possible_votes = floor(nodes_with_event / GROUP_SIZE)
# This is the maximum number of groups that could EVER observe this event.
# Minimum 1 to avoid division by zero for events seen on < GROUP_SIZE nodes.
def max_votes_for_event(event: str) -> int:
    info = event_info.get(event)
    if info is None:
        return 1
    return max(1, info["nodes_with_event"] // GROUP_SIZE)

def rarity_of_edge(cause: str, effect: str) -> str:
    """
    The rarity of an edge is determined by the RARER of cause/effect.
    Rarity order: ZERO > ULTRA_RARE > RARE > MODERATE > COMMON > VERY_COMMON
    """
    order = ["ZERO", "ULTRA_RARE", "RARE", "MODERATE", "COMMON", "VERY_COMMON"]
    r_cause  = event_info.get(cause,  {}).get("rarity", "VERY_COMMON")
    r_effect = event_info.get(effect, {}).get("rarity", "VERY_COMMON")
    # return the rarer one (lower index in order = rarer)
    return r_cause if order.index(r_cause) < order.index(r_effect) else r_effect

def p_threshold_for_edge(cause: str, effect: str) -> float:
    rarity = rarity_of_edge(cause, effect)
    return P_THRESHOLD.get(rarity, 1e-2)

# ── Load causal graph ─────────────────────────────────────────────────────
with open(CAUSAL_GRAPH) as fh:
    data = json.load(fh)

links        = data["links"]
total_groups = data["n_groups"] - data.get("n_groups_skipped", 0)

print(f"Total links in causal_graph.json : {len(links):,}")
print(f"Total eligible groups            : {total_groups}")

# ── Score every link ──────────────────────────────────────────────────────
scored       = []
skipped_zero = 0
skipped_p    = 0

for lk in links:
    cause  = lk["cause"]
    effect = lk["effect"]
    p_val  = lk["p_val"]
    votes  = lk["n_votes"]

    # ── Determine edge rarity ──────────────────────────────────────────────
    edge_rarity = rarity_of_edge(cause, effect)

    # ── Skip ZERO events — they were never observed ────────────────────────
    if edge_rarity == "ZERO":
        skipped_zero += 1
        continue

    # ── Apply rarity-aware p-value threshold ──────────────────────────────
    p_thresh = p_threshold_for_edge(cause, effect)
    if p_val > p_thresh:
        skipped_p += 1
        continue

    # ── Compute max possible votes for this edge ───────────────────────────
    # Use the rarer event's node count — that is the bottleneck.
    max_v_cause  = max_votes_for_event(cause)
    max_v_effect = max_votes_for_event(effect)
    max_v        = min(max_v_cause, max_v_effect)   # bottleneck

    # ── Vote fraction: votes / max_possible (not / total_groups) ──────────
    # A rare-event link seen by 3/3 possible groups = 1.0 (perfect replication)
    # A common link seen by 540/1080 groups          = 0.5
    vote_fraction = min(1.0, votes / max_v)

    # ── Final score ────────────────────────────────────────────────────────
    log_p = -math.log10(max(p_val, 1e-300))
    score = vote_fraction * log_p

    # ── Enrich link dict ───────────────────────────────────────────────────
    scored.append({
        **lk,
        "edge_rarity":    edge_rarity,
        "max_votes":      max_v,
        "vote_fraction":  round(vote_fraction, 4),
        "log_p":          round(log_p, 4),
        "score":          round(score, 4),
        "p_thresh":       p_thresh,
        "cause_count":    event_info.get(cause,  {}).get("total_count", 0),
        "effect_count":   event_info.get(effect, {}).get("total_count", 0),
    })

# Sort by score descending
scored.sort(key=lambda x: x["score"], reverse=True)

print(f"\nLinks skipped (ZERO events)      : {skipped_zero:,}")
print(f"Links skipped (p > threshold)    : {skipped_p:,}")
print(f"Links surviving                  : {len(scored):,}")

# ── Rarity breakdown of surviving links ──────────────────────────────────
print("\nSurviving links by edge rarity:")
for tier in ["ULTRA_RARE", "RARE", "MODERATE", "COMMON", "VERY_COMMON"]:
    n = sum(1 for lk in scored if lk["edge_rarity"] == tier)
    print(f"  {tier:<12} : {n:>5,}")

# ── Write TXT ─────────────────────────────────────────────────────────────
HDR = (f"  {'SCORE':>7}  {'V_FRAC':>7}  {'VOTES':>6}  {'MAX_V':>6}  "
       f"{'P_COMB':>10}  {'RARITY':<12}  "
       f"{'CAUSE':<25} {'LAG':>4}  {'EDGE':>5}  {'EFFECT':<25}\n")
SEP = "  " + "-" * 115 + "\n"

def fmt(lk):
    return (f"  {lk['score']:>7.3f}  {lk['vote_fraction']:>7.4f}  "
            f"{lk['n_votes']:>6}  {lk['max_votes']:>6}  "
            f"{lk['p_val']:>10.2e}  {lk['edge_rarity']:<12}  "
            f"{lk['cause']:<25} {lk['tau']:>4}  {lk['edge']:>5}  "
            f"{lk['effect']:<25}\n")

with open(OUTPUT_TXT, "w") as fh:
    fh.write("=" * 117 + "\n")
    fh.write(f"  PCMCIplus top causal links — rarity-aware ranking\n")
    fh.write(f"  score = vote_fraction × (-log10(p_comb))\n")
    fh.write(f"  vote_fraction = n_votes / max_possible_votes_for_rarer_event\n")
    fh.write(f"  total_links={len(links):,}  surviving={len(scored):,}  "
             f"total_groups={total_groups}\n")
    fh.write("=" * 117 + "\n\n")

    fh.write("P-VALUE THRESHOLDS BY RARITY TIER:\n")
    for tier, thresh in P_THRESHOLD.items():
        if thresh is not None:
            fh.write(f"  {tier:<12} : p_comb < {thresh:.0e}\n")
    fh.write("\n")

    # ── All links unified, sorted by score ───────────────────────────────
    fh.write(f"ALL SURVIVING LINKS — ranked by score  ({len(scored):,} total)\n")
    fh.write(HDR)
    fh.write(SEP)
    for lk in scored:
        fh.write(fmt(lk))

    # ── Rare-only section for easy reference ─────────────────────────────
    rare_links = [lk for lk in scored
                  if lk["edge_rarity"] in ("ULTRA_RARE", "RARE")]
    fh.write(f"\n\nRARE / ULTRA_RARE LINKS ONLY  ({len(rare_links):,} links)\n")
    fh.write("  (These involve events seen on very few nodes — "
             "vote_fraction accounts for limited observability)\n")
    fh.write(HDR)
    fh.write(SEP)
    for lk in rare_links:
        fh.write(fmt(lk))

print(f"\nTXT → {OUTPUT_TXT}")

# ── Write CSV ─────────────────────────────────────────────────────────────
with open(OUTPUT_CSV, "w") as fh:
    writer = csv.writer(fh)
    writer.writerow([
        "score", "vote_fraction", "n_votes", "max_votes",
        "p_comb", "p_val_best", "edge_rarity", "p_thresh",
        "cause", "cause_count", "tau", "edge",
        "effect", "effect_count",
    ])
    for lk in scored:
        writer.writerow([
            lk["score"], lk["vote_fraction"], lk["n_votes"], lk["max_votes"],
            lk["p_val"], lk.get("p_val_best", lk["p_val"]),
            lk["edge_rarity"], lk["p_thresh"],
            lk["cause"], lk["cause_count"], lk["tau"], lk["edge"],
            lk["effect"], lk["effect_count"],
        ])

print(f"CSV → {OUTPUT_CSV}")

# ── Print top 30 to screen ────────────────────────────────────────────────
print(f"\nTop 30 links (score = vote_fraction × -log10(p_comb)):\n")
print(HDR, end="")
print(SEP, end="")
for lk in scored[:30]:
    print(fmt(lk), end="")