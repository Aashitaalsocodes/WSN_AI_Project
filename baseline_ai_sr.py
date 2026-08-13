"""
baseline_ai_sr.py
AI-SR (AI-based Secure Routing) baseline simulation for comparison against TA-DT.

Same topology, energy decay model, attack injection ratios, and 20-round
structure as baseline_leach.py / baseline_heed.py / baseline_tbr.py /
digital_twin_sim.py, for a fair comparison.

AI-SR represents "AI-based but simpler than TA-DT": it uses a plain
XGBoost binary classifier trained on the SAME 4 input features TA-DT's
own TrustEngine consumes (historical_accuracy, protocol_compliance,
neighbor_recommendation, anomaly_score) -- so the inputs are directly
comparable -- but with two things TA-DT has that AI-SR deliberately
lacks:

  1. No graph-structure enrichment. TA-DT's GraphSAGE/GAT layers let the
     model reason about a node's position and neighborhood in the
     topology; AI-SR's XGBoost model sees each node's 4 features in
     isolation, with no awareness of the graph at all.
  2. No persistent trust memory. Unlike baseline_tbr.py, which
     accumulates a smoothed trust score across rounds, AI-SR makes a
     fresh, stateless classification every round from that round's
     features alone -- it has no memory of a node's history beyond what
     this round's features happen to encode.

This is what keeps AI-SR meaningfully different from both TBR (memory,
no ML) and TA-DT (ML + graph enrichment + memory via TrustEngine) rather
than re-implementing either.

Because there's no historical detector to reuse, the classifier is
trained once up front on a synthetic labeled dataset generated with the
exact same feature-generation logic digital_twin_sim.py uses per node
per round (historical_accuracy=0.8, protocol_compliance=0.8,
neighbor_recommendation=0.5 as constants, anomaly_score varying with
detection outcome) -- so the classifier is learning from a realistic,
if narrow, feature distribution. This training data is drawn from a
SEPARATE random.Random instance so it doesn't consume from the same
global random sequence the 20 test rounds use (seed 42, shared with
LEACH/HEED/TBR/digital_twin_sim for a fair comparison) -- otherwise the
attack sequence in the test rounds would silently diverge from the other
three baselines.

Energy decay: decay_multiplier is a static, per-node forwarding-centrality
score computed once from the fixed baseline_routes/graph G, matching the
patch applied to baseline_leach.py / baseline_heed.py / baseline_tbr.py,
for a fair cross-protocol comparison.
"""

import json
import os
import random
import statistics

import networkx as nx
import numpy as np
from xgboost import XGBClassifier

from trust_aware_routing import build_graph

NUM_ROUNDS = 23
OUTPUT_PATH = "outputs/baseline_ai_sr_results.json"
DEAD_ENERGY_THRESHOLD = 0.0

ATTACK_TYPE_WEIGHTS = {
    "none": 90.8,
    "blackhole": 2.7,
    "grayhole": 3.9,
    "tdma": 1.8,
    "flooding": 0.9,
}
ATTACK_TYPES = list(ATTACK_TYPE_WEIGHTS.keys())
ATTACK_WEIGHTS = list(ATTACK_TYPE_WEIGHTS.values())

ATTACK_ENERGY_PENALTY = {
    "blackhole": 0.35,
    "grayhole": 0.25,
    "flooding": 0.45,
    "tdma": 0.15,
}

# Same real detection-miss rates as digital_twin_sim.py / baseline_tbr.py,
# used only to generate a realistic anomaly_score feature -- the
# classifier's OWN prediction is what determines detection here, not this
# miss-rate table directly (that would defeat the point of training a
# classifier at all).
DETECTION_MISS_RATE_BY_TYPE = {
    "blackhole": 0.2098,
    "grayhole": 0.1094,
    "flooding": 0.023,
    "tdma": 0.1765,
}

TRAINING_SEED = 1337          # separate RNG so training data generation
TRAINING_SAMPLES = 8000       # doesn't disturb the seed-42 test sequence
CLASSIFIER_THRESHOLD = 0.5    # predicted_attacked if predicted probability >= this


def load_inputs():
    with open("outputs/routing_simulation.json") as f:
        sim = json.load(f)
    with open("outputs/energy_forecast_ibrl.json") as f:
        energy = json.load(f)
    return sim, energy


def build_energy_trend(energy_forecast):
    voltages = list(energy_forecast["next_voltage_forecast_volts"].values())
    mean_v = statistics.mean(voltages)
    std_v = statistics.stdev(voltages)
    return mean_v, std_v


def generate_training_row(rng, is_attacked, attack_type):
    """
    Same 4-feature generation logic as digital_twin_sim.py's
    simulate_round: historical_accuracy/protocol_compliance/
    neighbor_recommendation are held at their simulation-constant values
    (0.8, 0.8, 0.5), and anomaly_score is generated from the same
    detection-miss model, so the classifier trains on a distribution
    that matches what it will see at inference time.
    """
    if is_attacked:
        detected = rng.random() > DETECTION_MISS_RATE_BY_TYPE[attack_type]
    else:
        detected = rng.random() < 0.03

    base_anomaly = rng.uniform(0.75, 1.0) if detected else rng.uniform(0.0, 0.2)
    features = {
        "historical_accuracy": 0.8,
        "protocol_compliance": 0.8,
        "neighbor_recommendation": 0.5,
        "anomaly_score": base_anomaly,
    }
    return features, int(is_attacked)


def train_classifier():
    """
    Trains a plain XGBoost binary classifier on a synthetic dataset
    generated with the real attack-type ratios, using a separate RNG
    (TRAINING_SEED) so this doesn't touch the seed-42 sequence the 20
    test rounds depend on for a fair comparison against LEACH/HEED/TBR.
    """
    rng = random.Random(TRAINING_SEED)
    X, y = [], []

    for _ in range(TRAINING_SAMPLES):
        attack_type = rng.choices(ATTACK_TYPES, weights=ATTACK_WEIGHTS, k=1)[0]
        is_attacked = attack_type != "none"
        features, label = generate_training_row(rng, is_attacked, attack_type)
        X.append([
            features["historical_accuracy"],
            features["protocol_compliance"],
            features["neighbor_recommendation"],
            features["anomaly_score"],
        ])
        y.append(label)

    X = np.array(X)
    y = np.array(y)

    model = XGBClassifier(
        n_estimators=100,
        max_depth=3,
        learning_rate=0.1,
        eval_metric="logloss",
        random_state=TRAINING_SEED,
    )
    model.fit(X, y)
    return model


def simulate_round(round_num, node_ids, energy_state, mean_v, std_v, decay_multiplier,
                    model):
    """
    Decay energy, inject attacks using the real ratios, generate each
    node's 4-feature row, and classify with the trained XGBoost model
    (stateless -- no memory of prior rounds, unlike TBR's trust score).
    """
    attacked_nodes = []
    attacked_node_types = {}
    predicted_attacked = {}

    base_decay = 0.03 + (round_num * 0.004)

    row_ids = []
    rows = []

    for nid in node_ids:
        attack_type = random.choices(ATTACK_TYPES, weights=ATTACK_WEIGHTS, k=1)[0]
        is_attacked = attack_type != "none"
        if is_attacked:
            attacked_nodes.append(nid)
            attacked_node_types[nid] = attack_type

        jitter = random.gauss(0, std_v) / mean_v
        node_decay = base_decay * decay_multiplier[nid]
        if is_attacked:
            node_decay *= (1.0 + ATTACK_ENERGY_PENALTY[attack_type])
        energy_state[nid] = max(0.0, energy_state[nid] - node_decay + (jitter * 0.01))

        # ground-truth-correlated anomaly signal (same generation logic
        # as digital_twin_sim.py), which becomes a FEATURE the classifier
        # sees -- the classifier's own output is the detection decision,
        # not this miss-rate table directly
        if is_attacked:
            underlying_detectable = random.random() > DETECTION_MISS_RATE_BY_TYPE[attack_type]
        else:
            underlying_detectable = random.random() < 0.03
        anomaly_score = random.uniform(0.75, 1.0) if underlying_detectable else random.uniform(0.0, 0.2)

        row_ids.append(nid)
        rows.append([0.8, 0.8, 0.5, anomaly_score])

    X = np.array(rows)
    predictions = model.predict(X)
    for nid, pred in zip(row_ids, predictions):
        predicted_attacked[nid] = bool(pred)

    return attacked_nodes, attacked_node_types, predicted_attacked


def route_avoiding_excluded(G, src, dst, excluded):
    """
    AI-SR routing: shortest path with classifier-flagged nodes removed,
    falling back to unrestricted shortest path if no route survives
    exclusion.
    """
    if src in excluded or dst in excluded:
        excluded = excluded - {src, dst}

    if excluded:
        H = G.copy()
        H.remove_nodes_from(n for n in excluded if n in H)
        try:
            return nx.shortest_path(H, src, dst), True
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            pass

    try:
        return nx.shortest_path(G, src, dst), True
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return [], False


def main():
    print("Training AI-SR classifier (plain XGBoost, no GNN enrichment)...")
    model = train_classifier()
    print("Classifier trained.\n")

    random.seed(42)  # same seed as LEACH/HEED/TBR/digital twin for a fair comparison

    sim, energy_forecast = load_inputs()
    node_ids = sim["node_ids"]
    edges = sim["edges"]
    baseline_routes = sim["baseline_routes"]

    G = build_graph(node_ids, edges)
    mean_v, std_v = build_energy_trend(energy_forecast)

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

    energy_state = {nid: 1.0 for nid in node_ids}
    decay_multiplier = {
        nid: 0.7 + 0.3 * min(forwarding_count[nid] / max_forwarding_count, 1.0) + random.uniform(-0.05, 0.05)
        for nid in node_ids
    }

    results = {"protocol": "AI-SR", "num_rounds": NUM_ROUNDS, "rounds": []}

    total_nodes = len(node_ids)
    half_node_count = total_nodes // 2
    first_node_death_round = None
    half_node_death_round = None
    last_node_death_round = None

    total_attack_events = 0
    total_correct_detections = 0

    for round_num in range(NUM_ROUNDS):
        attacked_nodes, attacked_node_types, predicted_attacked = simulate_round(
            round_num, node_ids, energy_state, mean_v, std_v, decay_multiplier, model
        )
        true_attacked_set = set(attacked_nodes)

        excluded = {nid for nid in node_ids if predicted_attacked.get(nid)}

        for nid in true_attacked_set:
            total_attack_events += 1
            if predicted_attacked.get(nid):
                total_correct_detections += 1

        hop_counts = []
        compromised = 0
        successful_routes = 0
        compromised_routes_detail = []

        for route in baseline_routes:
            src, dst = route["source"], route["destination"]
            path, path_found = route_avoiding_excluded(G, src, dst, excluded)

            if path_found:
                successful_routes += 1
                hop_counts.append(len(path) - 1)
                intermediate_nodes = path[1:-1] if len(path) > 2 else []
                attacked_intermediates = [nid for nid in intermediate_nodes if nid in true_attacked_set]
                if attacked_intermediates:
                    compromised += 1
                    compromised_routes_detail.append({
                        "source": src,
                        "destination": dst,
                        "path": path,
                        "attacked_intermediate_nodes": attacked_intermediates,
                        "attack_types": [attacked_node_types.get(nid, "unknown") for nid in attacked_intermediates],
                    })

        avg_hop_count = round(sum(hop_counts) / len(hop_counts), 2) if hop_counts else 0.0
        compromised_pct = round((compromised / len(baseline_routes)) * 100, 2)
        pdr = round((successful_routes / len(baseline_routes)) * 100, 2)

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
            "attacked_nodes": attacked_nodes,
            "attacked_node_types": attacked_node_types,
            "attacked_count": len(attacked_nodes),
            "excluded_nodes": sorted(excluded),
            "excluded_node_count": len(excluded),
            "compromised_routes_pct": compromised_pct,
            "compromised_routes_detail": compromised_routes_detail,
            "packet_delivery_ratio_pct": pdr,
            "avg_hop_count": avg_hop_count,
            "avg_energy_remaining": avg_energy_remaining,
            "num_dead_nodes": num_dead_nodes,
        })

        print(f"[AI-SR] Round {round_num}: attacked={len(attacked_nodes)}  "
              f"excluded={len(excluded)}  "
              f"compromised_routes={compromised_pct}%  pdr={pdr}%  "
              f"avg_hop={avg_hop_count}  avg_energy={avg_energy_remaining}  "
              f"dead_nodes={num_dead_nodes}")

    all_pdr = [r["packet_delivery_ratio_pct"] for r in results["rounds"]]
    all_compromised = [r["compromised_routes_pct"] for r in results["rounds"]]
    all_hops = [r["avg_hop_count"] for r in results["rounds"]]

    detection_accuracy_pct = (
        round((total_correct_detections / total_attack_events) * 100, 2)
        if total_attack_events else None
    )

    results["summary"] = {
        "avg_packet_delivery_ratio_pct": round(statistics.mean(all_pdr), 2),
        "avg_compromised_routes_pct": round(statistics.mean(all_compromised), 2),
        "avg_hop_count": round(statistics.mean(all_hops), 2),
        "avg_energy_remaining_final": results["rounds"][-1]["avg_energy_remaining"],
        "final_num_dead_nodes": results["rounds"][-1]["num_dead_nodes"],
        "detection_accuracy_pct": detection_accuracy_pct,
        "note": (
            "AI-SR uses a plain XGBoost classifier on the same 4 input "
            "features as TA-DT's TrustEngine, but with no graph-structure "
            "enrichment (no GraphSAGE/GAT) and no persistent trust memory "
            "across rounds (unlike TBR's smoothed trust score) -- each "
            "round's classification is a fresh, stateless decision from "
            "that round's features alone. This should land AI-SR closer to "
            "TA-DT than TBR on detection quality (real learned classifier "
            "vs a threshold rule) but still behind TA-DT overall, since "
            "TA-DT also has topology awareness and cross-round memory that "
            "AI-SR lacks."
        ),
    }

    results["energy_summary"] = {
        "total_nodes": total_nodes,
        "half_node_count": half_node_count,
        "first_node_death_round": first_node_death_round,
        "half_node_death_round": half_node_death_round,
        "last_node_death_round": last_node_death_round,
    }

    os.makedirs("outputs", exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nWrote {NUM_ROUNDS} rounds to {OUTPUT_PATH}")
    print(f"Summary: avg_PDR={results['summary']['avg_packet_delivery_ratio_pct']}%  "
          f"avg_compromised={results['summary']['avg_compromised_routes_pct']}%  "
          f"detection_accuracy={detection_accuracy_pct}%  "
          f"avg_hop={results['summary']['avg_hop_count']}  "
          f"FND={first_node_death_round}  HND={half_node_death_round}  LND={last_node_death_round}")


if __name__ == "__main__":
    main()