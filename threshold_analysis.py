"""
threshold_analysis.py
Run this from WSN_AI_Project root (same folder as trust_engine.py, config.py).

Reconstructs per-node, per-round trust scores using the REAL TrustEngine and
REAL attack ground truth (attacked_nodes per round), since the actual
classifier's continuous anomaly_score was not found on disk. This is an
APPROXIMATION: anomaly_score is set to 0.8 if a node is in that round's
attacked_nodes list, else 0.2 (matching TrustEngine.initialize_trust's own
baseline convention) -- NOT the real classifier's probability output.
historical_accuracy/protocol_compliance/neighbor_recommendation use the same
fixed constants (0.8, 0.8, 0.5) that trust_aware_routing.py already uses
throughout the project.

This lets us compute genuine round-to-round trust-score deltas for
LEGITIMATE nodes (never attacked across all 23 rounds) and see where the
0.4 plausibility-check threshold actually falls relative to real volatility.

Prints only summary statistics -- no huge dump.
"""

import json
import pandas as pd
from trust_engine import TrustEngine

SIM_FILE = "outputs/digital_twin_results_packetmodel_seed42.json"


def main():
    with open(SIM_FILE, encoding="utf-8") as f:
        data = json.load(f)

    rounds = data["rounds"]
    num_nodes = data["num_nodes"]

    all_node_ids = list(rounds[0]["node_energy_snapshot"].keys())

    ever_attacked = set()
    for r in rounds:
        ever_attacked.update(r["attacked_nodes"])

    legit_ids = [n for n in all_node_ids if n not in ever_attacked]
    print(f"Total nodes: {len(all_node_ids)}")
    print(f"Ever attacked (excluded from legitimate): {len(ever_attacked)}")
    print(f"Legitimate (never attacked) nodes: {len(legit_ids)}")

    engine = TrustEngine()

    trust_by_round = []
    for r in rounds:
        attacked_set = set(r["attacked_nodes"])
        df = pd.DataFrame({
            "node_id": all_node_ids,
            "historical_accuracy": 0.8,
            "protocol_compliance": 0.8,
            "neighbor_recommendation": 0.5,
            "anomaly_score": [0.8 if n in attacked_set else 0.2 for n in all_node_ids],
        })
        df = engine.update_trust(df)
        trust_by_round.append(dict(zip(df["node_id"], df["trust_score"])))

    legit_deltas = []
    for node in legit_ids:
        series = [trust_by_round[t][node] for t in range(len(rounds))]
        for t in range(1, len(series)):
            legit_deltas.append(abs(series[t] - series[t - 1]))

    deltas_series = pd.Series(legit_deltas)
    print(f"\nLegitimate-node round-to-round abs-delta trust_score distribution "
          f"(n={len(deltas_series)} observations, {len(legit_ids)} nodes x "
          f"{len(rounds)-1} transitions):")
    print(deltas_series.describe())
    for pct in [50, 90, 95, 99, 99.9, 100]:
        print(f"  p{pct}: {deltas_series.quantile(pct/100):.6f}")

    print("\nFalse-reject rate on legitimate nodes at candidate thresholds:")
    for thresh in [0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.6]:
        false_reject_rate = (deltas_series > thresh).mean()
        print(f"  threshold={thresh}: false_reject_rate={false_reject_rate:.6f} "
              f"({int((deltas_series > thresh).sum())}/{len(deltas_series)})")

    attacked_transition_deltas = []
    for node in all_node_ids:
        if node not in ever_attacked:
            continue
        series = [trust_by_round[t][node] for t in range(len(rounds))]
        attacked_rounds = {r["round"] for r in rounds if node in r["attacked_nodes"]}
        for t in range(1, len(rounds)):
            was_attacked_now = rounds[t]["round"] in attacked_rounds
            was_attacked_before = rounds[t-1]["round"] in attacked_rounds
            if was_attacked_now != was_attacked_before:
                attacked_transition_deltas.append(abs(series[t] - series[t-1]))

    if attacked_transition_deltas:
        atd = pd.Series(attacked_transition_deltas)
        print(f"\nFor contrast -- abs-delta at attack-status transitions (n={len(atd)}):")
        print(atd.describe())
        print("\nDetection rate at candidate thresholds:")
        for thresh in [0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.6]:
            detect_rate = (atd > thresh).mean()
            print(f"  threshold={thresh}: flagged_rate={detect_rate:.6f} "
                  f"({int((atd > thresh).sum())}/{len(atd)})")


if __name__ == "__main__":
    main()
