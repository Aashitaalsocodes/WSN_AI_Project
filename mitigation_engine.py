"""
mitigation_engine.py
=====================
Task 3: Differentiated mitigation strategy per attack type.

Consumes classifier output in the agreed schema:
    {node_id, attack_type, confidence}

Currently reads from outputs/stub_classifier_predictions.json (the stub).
TO SWITCH TO PERSON B'S REAL CLASSIFIER: change CLASSIFIER_PATH below to
her real output file. No other code needs to change, as long as her
output uses the same {node_id, attack_type, confidence} schema.

Also reads outputs/preprocessed_nodes.json (Task 1 output) to get each
node's current trust-related fields (composite_risk_score, is_cluster_head,
etc.) so mitigation can factor in more than just the attack label alone.

Mitigation logic per attack type:
  Blackhole  -> node silently drops all relayed packets.
               Action: exclude from routing (trust -> near zero), reroute
               all traffic away, flag for physical inspection.
  Grayhole   -> node selectively drops packets (harder to detect).
               Action: sharply reduce trust (not to zero), increase
               monitoring frequency, reroute a portion of traffic away.
  Flooding   -> node/attacker floods network with junk traffic.
               Action: rate-limit packet acceptance from the node,
               temporarily isolate, no full reroute needed.
  TDMA       -> timeslot/scheduling attack, disrupts synchronization.
               Action: force TDMA resync, flag for slot reassignment,
               moderate trust reduction (could be clock drift, not
               necessarily malicious -- handled less aggressively).
  Normal     -> no attack. No mitigation; trust unchanged (or a small
               positive nudge to reward continued good behavior).

Mitigation severity scales with classifier confidence: a low-confidence
prediction gets a softer response (e.g. increased monitoring only)
rather than immediately taking a harsh action on what might be a false
positive. This directly protects against the ~1-11% miss rates we
already validated for the pipeline.

Outputs:
  outputs/mitigation_actions.json  -- one record per node
  outputs/mitigation_summary.json  -- aggregate stats for reporting/paper

Usage:
    python mitigation_engine.py
    python mitigation_engine.py --classifier outputs/real_classifier_output.json
"""

import json
import sys
import numpy as np
import pandas as pd
from pathlib import Path

BASE_DIR          = Path(__file__).parent
OUTPUTS           = BASE_DIR / "outputs"
NODES_PATH        = OUTPUTS / "preprocessed_nodes.json"       # Task 1 output
CLASSIFIER_PATH   = OUTPUTS / "stub_classifier_predictions.json"  # <-- swap this for Person B's real file
OUT_ACTIONS       = OUTPUTS / "mitigation_actions.json"
OUT_SUMMARY       = OUTPUTS / "mitigation_summary.json"

# Confidence thresholds that gate how aggressively we act.
HIGH_CONF = 0.80
LOW_CONF  = 0.50


def mitigate_blackhole(confidence, current_trust):
    if confidence >= HIGH_CONF:
        action = "EXCLUDE_FROM_ROUTING"
        trust_multiplier = 0.02   # near-zero trust
        reroute = "FULL"
        flag = "PHYSICAL_INSPECTION_URGENT"
    elif confidence >= LOW_CONF:
        action = "QUARANTINE_MONITOR"
        trust_multiplier = 0.15
        reroute = "PARTIAL"
        flag = "PHYSICAL_INSPECTION_RECOMMENDED"
    else:
        action = "INCREASE_MONITORING_ONLY"
        trust_multiplier = 0.60
        reroute = "NONE"
        flag = "WATCHLIST"
    return action, current_trust * trust_multiplier, reroute, flag


def mitigate_grayhole(confidence, current_trust):
    if confidence >= HIGH_CONF:
        action = "REDUCE_TRUST_REROUTE_PARTIAL"
        trust_multiplier = 0.20
        reroute = "PARTIAL"
        flag = "INCREASED_MONITORING"
    elif confidence >= LOW_CONF:
        action = "INCREASE_MONITORING"
        trust_multiplier = 0.45
        reroute = "NONE"
        flag = "WATCHLIST"
    else:
        action = "INCREASE_MONITORING_ONLY"
        trust_multiplier = 0.70
        reroute = "NONE"
        flag = "WATCHLIST"
    return action, current_trust * trust_multiplier, reroute, flag


def mitigate_flooding(confidence, current_trust):
    if confidence >= HIGH_CONF:
        action = "RATE_LIMIT_ISOLATE"
        trust_multiplier = 0.10
        reroute = "NONE"
        flag = "TEMP_ISOLATION"
    elif confidence >= LOW_CONF:
        action = "RATE_LIMIT"
        trust_multiplier = 0.40
        reroute = "NONE"
        flag = "WATCHLIST"
    else:
        action = "INCREASE_MONITORING_ONLY"
        trust_multiplier = 0.70
        reroute = "NONE"
        flag = "WATCHLIST"
    return action, current_trust * trust_multiplier, reroute, flag


def mitigate_tdma(confidence, current_trust):
    if confidence >= HIGH_CONF:
        action = "FORCE_RESYNC_REASSIGN_SLOT"
        trust_multiplier = 0.50   # moderate -- may not be malicious
        reroute = "NONE"
        flag = "SLOT_REASSIGNMENT"
    elif confidence >= LOW_CONF:
        action = "FORCE_RESYNC"
        trust_multiplier = 0.70
        reroute = "NONE"
        flag = "WATCHLIST"
    else:
        action = "INCREASE_MONITORING_ONLY"
        trust_multiplier = 0.85
        reroute = "NONE"
        flag = "WATCHLIST"
    return action, current_trust * trust_multiplier, reroute, flag


def mitigate_normal(confidence, current_trust):
    action = "NONE"
    # small positive nudge for sustained good behavior, capped at 1.0
    trust_multiplier = 1.02
    reroute = "NONE"
    flag = "CLEAR"
    return action, min(current_trust * trust_multiplier, 1.0), reroute, flag


MITIGATION_DISPATCH = {
    "Blackhole": mitigate_blackhole,
    "Grayhole":  mitigate_grayhole,
    "Flooding":  mitigate_flooding,
    "TDMA":      mitigate_tdma,
    "Normal":    mitigate_normal,
}


def load_nodes():
    with open(NODES_PATH) as f:
        return json.load(f)


def load_classifier_output(path):
    with open(path) as f:
        return json.load(f)


def run_mitigation(classifier_path=CLASSIFIER_PATH):
    print("=" * 60)
    print("Task 3 -- Differentiated Mitigation Strategy Engine")
    print("=" * 60)

    print(f"\n[1/3] Loading preprocessed nodes from {NODES_PATH}...")
    nodes = load_nodes()
    print(f"      {len(nodes):,} nodes loaded")

    print(f"\n[2/3] Loading classifier predictions from {classifier_path}...")
    predictions = load_classifier_output(classifier_path)
    print(f"      {len(predictions):,} predictions loaded")
    if classifier_path == CLASSIFIER_PATH:
        print("      NOTE: using STUB classifier output. Swap --classifier to")
        print("            Person B's real file once available.")

    print(f"\n[3/3] Applying mitigation logic per node...")
    actions = {}
    action_counts = {}
    reroute_counts = {"FULL": 0, "PARTIAL": 0, "NONE": 0}
    trust_deltas = []

    for node_id, pred in predictions.items():
        attack_type = pred.get("attack_type", "Normal")
        confidence = float(pred.get("confidence", 0.5))

        node_rec = nodes.get(node_id, {})
        # Use composite_risk_score inverted as a stand-in "current trust"
        # (low risk = high trust). Falls back to 0.8 baseline if missing.
        current_risk = node_rec.get("composite_risk_score", 0.2)
        current_trust = float(np.clip(1.0 - current_risk, 0.05, 1.0))

        mitigate_fn = MITIGATION_DISPATCH.get(attack_type, mitigate_normal)
        action, new_trust, reroute, flag = mitigate_fn(confidence, current_trust)
        new_trust = float(np.clip(new_trust, 0.0, 1.0))

        actions[node_id] = {
            "node_id": node_id,
            "attack_type": attack_type,
            "confidence": round(confidence, 4),
            "is_cluster_head": node_rec.get("is_cluster_head", 0),
            "mitigation_action": action,
            "reroute_scope": reroute,
            "flag": flag,
            "trust_before": round(current_trust, 4),
            "trust_after": round(new_trust, 4),
            "trust_delta": round(new_trust - current_trust, 4),
        }

        action_counts[action] = action_counts.get(action, 0) + 1
        reroute_counts[reroute] = reroute_counts.get(reroute, 0) + 1
        trust_deltas.append(new_trust - current_trust)

    OUTPUTS.mkdir(exist_ok=True)
    with open(OUT_ACTIONS, "w") as f:
        json.dump(actions, f)
    size_mb = OUT_ACTIONS.stat().st_size / (1024 * 1024)
    print(f"      Wrote {len(actions):,} mitigation records ({size_mb:.1f} MB)")

    summary = {
        "total_nodes": len(actions),
        "classifier_source": str(classifier_path),
        "action_counts": action_counts,
        "reroute_counts": reroute_counts,
        "avg_trust_delta": round(float(np.mean(trust_deltas)), 4),
        "cluster_heads_flagged": sum(
            1 for a in actions.values()
            if a["is_cluster_head"] == 1 and a["attack_type"] != "Normal"
        ),
    }
    with open(OUT_SUMMARY, "w") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "=" * 60)
    print("MITIGATION SUMMARY")
    print("=" * 60)
    print("Actions taken:")
    for action, count in sorted(action_counts.items(), key=lambda x: -x[1]):
        print(f"  {action:30s}: {count:,}")
    print("\nReroute scope:")
    for scope, count in reroute_counts.items():
        print(f"  {scope:10s}: {count:,}")
    print(f"\nAverage trust delta: {summary['avg_trust_delta']}")
    print(f"Cluster heads flagged as attacked: {summary['cluster_heads_flagged']}")
    print(f"\nOutput: {OUT_ACTIONS}")
    print(f"Summary: {OUT_SUMMARY}")
    print("=" * 60)

    return summary


if __name__ == "__main__":
    classifier_path = CLASSIFIER_PATH
    if "--classifier" in sys.argv:
        idx = sys.argv.index("--classifier")
        classifier_path = Path(sys.argv[idx + 1])
    run_mitigation(classifier_path=classifier_path)