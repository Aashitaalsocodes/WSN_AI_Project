"""
digital_twin_sim.py
Digital Twin backend simulation for the WSN AI Security Pipeline.

Simulates the network over 20 discrete rounds: energy decay, probabilistic
attack injection (using real attack-type ratios), trust recalculation
(TrustEngine, unmodified), and routing recalculation (trust_aware_routing
logic, unmodified). Only lightweight aggregate per-round metrics are
written — not full route paths — to keep the output file small.
"""

import json
import os
import random
import statistics

import pandas as pd

from trust_engine import TrustEngine
from config import TRUST_THRESHOLD
from trust_aware_routing import build_graph, route_with_trust

NUM_ROUNDS = 20
OUTPUT_PATH = "outputs/digital_twin_results.json"

# Real attack-type ratios, taken from attack_ground_truth.json
ATTACK_TYPE_WEIGHTS = {
    "none": 90.8,
    "blackhole": 2.7,
    "grayhole": 3.9,
    "tdma": 1.8,
    "flooding": 0.9,
}
ATTACK_TYPES = list(ATTACK_TYPE_WEIGHTS.keys())
ATTACK_WEIGHTS = list(ATTACK_TYPE_WEIGHTS.values())


def load_inputs():
    with open("outputs/routing_simulation.json") as f:
        sim = json.load(f)
    with open("outputs/energy_forecast_ibrl.json") as f:
        energy = json.load(f)
    return sim, energy


def build_energy_trend(energy_forecast):
    """Derive a decay noise profile from the real LSTM voltage forecast."""
    voltages = list(energy_forecast["next_voltage_forecast_volts"].values())
    mean_v = statistics.mean(voltages)
    std_v = statistics.stdev(voltages)
    return mean_v, std_v


def simulate_round(round_num, node_ids, energy_state, mean_v, std_v):
    """
    Decay each node's energy for this round and inject probabilistic
    attacks based on the real attack-type distribution. Models imperfect
    attack detection (false negatives) so trust-aware routing occasionally
    has to route through an undetected compromised node.

    Returns:
        attacked_nodes: list of node ids attacked this round (ground truth)
        classifier: {node_id: {"attack_probability": float, "predicted_attacked": int}}
        row_ids: node_id order matching `rows`
        rows: list of dicts with the 4 trust-input columns, in row_ids order
    """
    attacked_nodes = []
    classifier = {}
    row_ids = []
    rows = []

    # steeper, accelerating decay so nodes visibly cross the low-energy
    # threshold within the 20-round window
    base_decay = 0.03 + (round_num * 0.004)

    # real classifiers aren't perfect — model a false-negative rate so some
    # attacks go undetected, which is what actually produces compromised
    # routes in a trust-aware system
    DETECTION_MISS_RATE = 0.18

    for nid in node_ids:
        # energy decay with jitter drawn from the real voltage distribution
        jitter = random.gauss(0, std_v) / mean_v  # normalized noise
        energy_state[nid] = max(0.0, energy_state[nid] - base_decay + (jitter * 0.01))

        # probabilistic attack injection using real ratios
        attack_type = random.choices(ATTACK_TYPES, weights=ATTACK_WEIGHTS, k=1)[0]
        is_attacked = attack_type != "none"
        if is_attacked:
            attacked_nodes.append(nid)

        # simulate detection: attacked nodes are usually but not always caught
        if is_attacked:
            detected = random.random() > DETECTION_MISS_RATE
        else:
            detected = False

        # anomaly score: elevated if detected, further elevated if energy is critically low
        base_anomaly = random.uniform(0.75, 1.0) if detected else random.uniform(0.0, 0.2)
        energy_penalty = 0.15 if energy_state[nid] < 0.2 else 0.0
        anomaly_score = min(1.0, base_anomaly + energy_penalty)

        classifier[nid] = {
            "attack_probability": anomaly_score,
            "predicted_attacked": 1 if detected else 0,
        }

        row_ids.append(nid)
        rows.append({
            "historical_accuracy": 0.8,
            "protocol_compliance": 0.8,
            "neighbor_recommendation": 0.5,
            "anomaly_score": anomaly_score,
        })

    return attacked_nodes, classifier, row_ids, rows


def main():
    random.seed(42)  # reproducible simulation across runs

    sim, energy_forecast = load_inputs()
    node_ids = sim["node_ids"]
    edges = sim["edges"]
    baseline_routes = sim["baseline_routes"]

    G = build_graph(node_ids, edges)
    mean_v, std_v = build_energy_trend(energy_forecast)

    energy_state = {nid: 1.0 for nid in node_ids}  # normalized 0-1, start full
    engine = TrustEngine()

    results = {"num_rounds": NUM_ROUNDS, "rounds": []}

    for round_num in range(NUM_ROUNDS):
        attacked_nodes, classifier, row_ids, rows = simulate_round(
            round_num, node_ids, energy_state, mean_v, std_v
        )

        # --- trust recalculation (TrustEngine.update_trust, unmodified) ---
        df = pd.DataFrame(rows)
        trust_df = engine.update_trust(df)
        trust_scores = dict(zip(row_ids, trust_df["trust_score"].values))
        avg_trust = round(float(trust_df["trust_score"].mean()), 4)

        # excluded nodes: predicted attacked OR trust below threshold
        excluded = {
            nid for nid in node_ids
            if classifier[nid]["predicted_attacked"] == 1
            or trust_scores.get(nid, 1.0) < TRUST_THRESHOLD
        }

        # --- routing recalculation (trust_aware_routing, unmodified) ---
        true_attacked_set = set(attacked_nodes)  # ground truth for this round
        hop_counts = []
        compromised = 0
        for route in baseline_routes:
            result = route_with_trust(
                G, route["source"], route["destination"], excluded, classifier
            )
            if result.get("path_found"):
                hop_counts.append(result["hop_count"])
                path = result.get("path", [])
                # only count a route as "compromised" if an attacked node
                # sits in the middle of the path (a hop the router could
                # have chosen to avoid) — not the source/destination, which
                # can't be rerouted away from
                intermediate_nodes = path[1:-1] if len(path) > 2 else []
                if any(nid in true_attacked_set for nid in intermediate_nodes):
                    compromised += 1

        avg_hop_count = round(sum(hop_counts) / len(hop_counts), 2) if hop_counts else 0.0
        compromised_pct = round((compromised / len(baseline_routes)) * 100, 2)

        results["rounds"].append({
            "round": round_num,
            "attacked_nodes": attacked_nodes[:5],  # sample only, for viz
            "attacked_count": len(attacked_nodes),
            "avg_trust_score": avg_trust,
            "compromised_routes_pct": compromised_pct,
            "avg_hop_count": avg_hop_count,
            "excluded_node_count": len(excluded),
        })

        print(f"Round {round_num}: attacked={len(attacked_nodes)}  "
              f"avg_trust={avg_trust}  excluded={len(excluded)}  "
              f"compromised_routes={compromised_pct}%  avg_hop={avg_hop_count}")

    os.makedirs("outputs", exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nWrote {NUM_ROUNDS} rounds to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()