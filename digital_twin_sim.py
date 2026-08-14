"""
digital_twin_sim.py
Digital Twin backend simulation for the WSN AI Security Pipeline.

Simulates the network over 23 discrete rounds: energy decay, probabilistic
attack injection (using real attack-type ratios), trust recalculation
(TrustEngine, unmodified), and routing recalculation (trust_aware_routing
logic, unmodified).

CHANGED for Task 6 feedback loop: now logs full per-node attacked/excluded
lists, per-node attack types, and compromised route paths (not just
aggregate counts/percentages), so feedback_loop.py can compute real
per-node risk and routing adjustments instead of approximating from
round-level stats.

CHANGED for Task 10 evaluation metrics: now exports avg_energy_remaining
and num_dead_nodes per round, plus a top-level "energy_summary" block with
First/Half/Last Node Death rounds -- energy_state was already tracked
internally every round but was never surfaced in the output JSON, so
FND/HND/LND and avg residual energy were previously uncomputable downstream.
A node is considered "dead" once its normalized energy hits 0.0.

CHANGED for energy-decay rebuild (cross-protocol consistency fix): replaced
the old per-node decay_multiplier (pure random.uniform(0.5, 1.6) noise,
uncorrelated with network role) with a static, one-time forwarding-centrality
multiplier computed from baseline_routes/G before trust/routing recalculation
begins each round. This makes the energy model protocol-agnostic and
consistent with the same fix already applied to baseline_leach.py,
baseline_heed.py, baseline_tbr.py, and baseline_ai_sr.py, so cross-protocol
comparisons in Section VIII reflect real topological differences rather than
independent random noise per file. NUM_ROUNDS bumped 20 -> 23 because LND was
frequently null at 20 rounds (node deaths follow a late-stage collapse
pattern, not gradual attrition).
"""

import json
import os
import random
import statistics

import networkx as nx
import pandas as pd

from trust_engine import TrustEngine
from config import TRUST_THRESHOLD
from trust_aware_routing import build_graph, route_with_trust

NUM_ROUNDS = 23
OUTPUT_PATH = "outputs/digital_twin_results.json"
DEAD_ENERGY_THRESHOLD = 0.0  # node considered dead once normalized energy hits this

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


# Attacked nodes burn extra energy from the attack behavior itself
# (intercepting/dropping packets for blackhole/grayhole, replaying for
# flooding, colliding for tdma). Values are relative multipliers applied
# on top of the node's own base decay for that round.
ATTACK_ENERGY_PENALTY = {
    "blackhole": 0.35,
    "grayhole": 0.25,
    "flooding": 0.45,
    "tdma": 0.15,
}


def simulate_round(round_num, node_ids, energy_state, mean_v, std_v, decay_multiplier):
    """
    Decay each node's energy for this round and inject probabilistic
    attacks based on the real attack-type distribution. Models imperfect
    attack detection (false negatives) so trust-aware routing occasionally
    has to route through an undetected compromised node.

    Energy decay varies per node via two mechanisms so deaths spread out
    across rounds instead of happening in lockstep: (1) decay_multiplier,
    a fixed per-node forwarding-centrality factor assigned once at
    simulation start, and (2) an attack-exposure penalty applied only in
    rounds where a node is actively attacked.

    Returns:
        attacked_nodes: list of node ids attacked this round (ground truth)
        attacked_node_types: {node_id: attack_type} for attacked nodes only
        classifier: {node_id: {"attack_probability": float, "predicted_attacked": int}}
        row_ids: node_id order matching `rows`
        rows: list of dicts with the 4 trust-input columns, in row_ids order
    """
    attacked_nodes = []
    attacked_node_types = {}
    classifier = {}
    row_ids = []
    rows = []

    # steeper, accelerating decay so nodes visibly cross the low-energy
    # threshold within the round window
    base_decay = 0.03 + (round_num * 0.004)

    # real classifiers aren't perfect — model a false-negative rate so some
    # attacks go undetected, which is what actually produces compromised
    # routes in a trust-aware system
    DETECTION_MISS_RATE_BY_TYPE = {
        "blackhole": 0.2469,
        "grayhole": 0.1038,
        "flooding": 0.0103,
        "tdma": 0.1343,
    }

    for nid in node_ids:
        # probabilistic attack injection using real ratios (moved ahead of
        # the energy-decay step so that step can apply the attack-exposure
        # penalty in the same pass)
        attack_type = random.choices(ATTACK_TYPES, weights=ATTACK_WEIGHTS, k=1)[0]
        is_attacked = attack_type != "none"
        if is_attacked:
            attacked_nodes.append(nid)
            attacked_node_types[nid] = attack_type

        # energy decay: base rate * this node's fixed forwarding-centrality
        # factor, plus jitter from the real voltage distribution, plus an
        # extra penalty if the node is actively attacked this round
        jitter = random.gauss(0, std_v) / mean_v  # normalized noise
        node_decay = base_decay * decay_multiplier[nid]
        if is_attacked:
            node_decay *= (1.0 + ATTACK_ENERGY_PENALTY[attack_type])
        energy_state[nid] = max(0.0, energy_state[nid] - node_decay + (jitter * 0.01))

        # simulate detection: attacked nodes are usually but not always caught
        if is_attacked:
            detected = random.random() > DETECTION_MISS_RATE_BY_TYPE[attack_type]
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

    return attacked_nodes, attacked_node_types, classifier, row_ids, rows


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

    # Static, one-time forwarding-centrality multiplier: computed once from
    # the fixed baseline_routes/graph G (built once per protocol run, not
    # regenerated per round), so it's a legitimate static per-node factor
    # rather than noise. Nodes that sit on more shortest paths between
    # baseline source/destination pairs carry more forwarding load and burn
    # energy faster; nodes that forward little are more efficient. Computed
    # before trust/routing recalculation begins so it's independent of
    # route_with_trust()'s per-round path choices, keeping the comparison
    # protocol-agnostic and fair across LEACH/HEED/TBR/AI-SR/TA-DT.
    forwarding_count = {nid: 0 for nid in node_ids}
    for route in baseline_routes:
        src, dst = route["source"], route["destination"]
        try:
            path = nx.shortest_path(G, src, dst)
            for nid in path[1:-1]:
                forwarding_count[nid] += 1
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            continue
    max_forwarding_count = max(forwarding_count.values()) if forwarding_count.values() else 1
    max_forwarding_count = max(max_forwarding_count, 1)

    decay_multiplier = {
        nid: 0.7 + 0.3 * min(forwarding_count[nid] / max_forwarding_count, 1.0) + random.uniform(-0.05, 0.05)
        for nid in node_ids
    }

    results = {"num_rounds": NUM_ROUNDS, "rounds": []}

    # FND/HND/LND tracking
    total_nodes = len(node_ids)
    half_node_count = total_nodes // 2
    first_node_death_round = None
    half_node_death_round = None
    last_node_death_round = None

    for round_num in range(NUM_ROUNDS):
        attacked_nodes, attacked_node_types, classifier, row_ids, rows = simulate_round(
            round_num, node_ids, energy_state, mean_v, std_v, decay_multiplier
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

        # attacked nodes the pipeline failed to exclude this round
        true_attacked_set = set(attacked_nodes)
        missed_detections = sorted(true_attacked_set - excluded)

        # --- routing recalculation (trust_aware_routing, unmodified) ---
        hop_counts = []
        compromised = 0
        compromised_routes_detail = []
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
                attacked_intermediates = [nid for nid in intermediate_nodes if nid in true_attacked_set]
                if attacked_intermediates:
                    compromised += 1
                    compromised_routes_detail.append({
                        "source": route["source"],
                        "destination": route["destination"],
                        "path": path,
                        "attacked_intermediate_nodes": attacked_intermediates,
                        "attack_types": [attacked_node_types.get(nid, "unknown") for nid in attacked_intermediates],
                    })

        avg_hop_count = round(sum(hop_counts) / len(hop_counts), 2) if hop_counts else 0.0
        compromised_pct = round((compromised / len(baseline_routes)) * 100, 2)

        # --- energy state for this round (Task 10 addition) ---
        avg_energy_remaining = round(sum(energy_state.values()) / total_nodes, 4)
        dead_nodes = [nid for nid, e in energy_state.items() if e <= DEAD_ENERGY_THRESHOLD]
        num_dead_nodes = len(dead_nodes)

        if num_dead_nodes >= 1 and first_node_death_round is None:
            first_node_death_round = round_num
        if num_dead_nodes >= half_node_count and half_node_death_round is None:
            half_node_death_round = round_num
        if num_dead_nodes >= total_nodes and last_node_death_round is None:
            last_node_death_round = round_num

        results["rounds"].append({
            "round": round_num,
            "attacked_nodes": attacked_nodes,  # full list now, not [:5] sample
            "attacked_node_types": attacked_node_types,
            "attacked_count": len(attacked_nodes),
            "excluded_nodes": sorted(excluded),  # full set now, not just count
            "excluded_node_count": len(excluded),
            "missed_detections": missed_detections,  # attacked but not excluded
            "avg_trust_score": avg_trust,
            "compromised_routes_pct": compromised_pct,
            "compromised_routes_detail": compromised_routes_detail,
            "avg_hop_count": avg_hop_count,
            "avg_energy_remaining": avg_energy_remaining,
            "num_dead_nodes": num_dead_nodes,
        })

        print(f"Round {round_num}: attacked={len(attacked_nodes)}  "
              f"avg_trust={avg_trust}  excluded={len(excluded)}  "
              f"missed={len(missed_detections)}  "
              f"compromised_routes={compromised_pct}%  avg_hop={avg_hop_count}  "
              f"avg_energy={avg_energy_remaining}  dead_nodes={num_dead_nodes}")

    results["energy_summary"] = {
        "total_nodes": total_nodes,
        "half_node_count": half_node_count,
        "first_node_death_round": first_node_death_round,
        "half_node_death_round": half_node_death_round,
        "last_node_death_round": last_node_death_round,
        "final_avg_energy_remaining": results["rounds"][-1]["avg_energy_remaining"],
        "final_num_dead_nodes": results["rounds"][-1]["num_dead_nodes"],
        "note": (
            "FND/HND/LND are the round index (0-based) at which the first node, "
            "50% of nodes, and all nodes respectively first reached "
            f"energy <= {DEAD_ENERGY_THRESHOLD}. A null value means that threshold "
            f"was not reached within the simulation's {NUM_ROUNDS} rounds."
        ),
    }

    os.makedirs("outputs", exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nWrote {NUM_ROUNDS} rounds to {OUTPUT_PATH}")
    print(f"Energy summary: FND={first_node_death_round}  HND={half_node_death_round}  "
          f"LND={last_node_death_round}  final_avg_energy={results['rounds'][-1]['avg_energy_remaining']}")


if __name__ == "__main__":
    main()