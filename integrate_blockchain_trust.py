"""
integrate_blockchain_trust.py
Feeds REAL trust scores -- computed the same way trust_aware_routing.py's
main() does for the actual paper results -- into the decentralized 5-node
blockchain trust network.

Trust inputs: historical_accuracy=0.8, protocol_compliance=0.8,
neighbor_recommendation=0.5 are fixed constants (matches the project's
existing methodology in trust_aware_routing.py); anomaly_score comes from
the real attack classifier's per-node attack_probability. Only anomaly_score
varies node to node -- this is not new synthetic data, it's the same
approach the paper's own trust-aware routing numbers already use.

Run this from the WSN_AI_Project root (same folder as trust_engine.py).
"""

import json
import time
import pandas as pd
from pathlib import Path
from trust_engine import TrustEngine
from blockchain_trust_network import build_network

OUTPUTS_DIR = Path("outputs")


def load_real_trust_scores(seed=42):
    with open(OUTPUTS_DIR / f"routing_simulation_seed{seed}.json", encoding="utf-8") as f:
        sim = json.load(f)
    with open(OUTPUTS_DIR / "attack_classifier_predictions.json", encoding="utf-8") as f:
        classifier = json.load(f)

    node_ids = sim["node_ids"]
    df = pd.DataFrame({
        "node_id": [int(nid) for nid in node_ids],
        "historical_accuracy": 0.8,
        "protocol_compliance": 0.8,
        "neighbor_recommendation": 0.5,
        "anomaly_score": [
            float(classifier.get(nid, {}).get("attack_probability", 0.2))
            for nid in node_ids
        ],
    })
    df = TrustEngine().update_trust(df)
    return df, node_ids


def main():
    df, node_ids = load_real_trust_scores(seed=42)

    print(f"Loaded real trust scores for {len(df)} nodes (seed 42 simulation)")
    print(df[['trust_score', 'suspicious_flag']].describe())
    print()

    # --- Run multiple trials to get a stable mining-time figure ---
    # Proof-of-work time varies run to run (random nonce search), so a
    # single measurement isn't reportable -- average over several trials.
    N_TRIALS = 10
    mining_times_ms = []

    for trial in range(N_TRIALS):
        nodes = build_network(n_nodes=5, difficulty=2)
        proposer = nodes[0]
        for row in df.itertuples(index=False):
            proposer.add_trust_transaction(str(row.node_id), float(row.trust_score))

        start = time.time()
        block, accepted = proposer.propose_block()
        elapsed_ms = (time.time() - start) * 1000
        mining_times_ms.append(elapsed_ms)

        chains_match = all(n.chain[-1].hash == nodes[0].chain[-1].hash for n in nodes)
        print(f"  Trial {trial+1}: accepted={accepted}, time={elapsed_ms:.2f} ms, "
              f"chains_identical={chains_match}")

    avg_ms = sum(mining_times_ms) / len(mining_times_ms)
    print(f"\nAcross {N_TRIALS} trials, 500 transactions/block, difficulty=2:")
    print(f"  Mean mining+consensus time: {avg_ms:.2f} ms")
    print(f"  Min: {min(mining_times_ms):.2f} ms, Max: {max(mining_times_ms):.2f} ms")

    # --- Spot-check on the last trial's network ---
    print("\nSpot-check: comparing original vs. blockchain-retrieved trust scores "
          "(retrieved from a DIFFERENT node than the proposer, last trial's network)")
    sample_rows = df.head(5)
    for row in sample_rows.itertuples(index=False):
        original = round(float(row.trust_score), 4)
        retrieved = nodes[1].get_trust(str(row.node_id))
        match = abs(original - retrieved) < 1e-9 if retrieved is not None else False
        print(f"  node {row.node_id}: original={original:.4f}  "
              f"retrieved(peer)={retrieved}  match={match}")


if __name__ == "__main__":
    main()