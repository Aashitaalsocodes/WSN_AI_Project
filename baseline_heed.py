"""
baseline_heed.py
HEED (Hybrid Energy-Efficient Distributed clustering) baseline simulation
for comparison against TA-DT.

Same topology, energy decay model, attack injection ratios, and 20-round
structure as baseline_leach.py / digital_twin_sim.py, for a fair
comparison. Like LEACH, HEED has NO trust engine and NO attack
classifier -- it also routes via plain shortest path, blind to which
nodes are compromised.

The one thing that differs from LEACH: cluster-head selection. Instead
of pure random probability, HEED weighs residual energy (higher energy
= more likely to become CH) combined with node degree / communication
cost (nodes with more neighbors are cheaper CH candidates since they
can reach more of the cluster directly). This makes CH selection
energy-aware, which is HEED's actual contribution over LEACH -- but
it still has no concept of trust or attack avoidance, so routing
behavior (and therefore compromised-route rate) should land close to
LEACH's, while energy lifetime should improve somewhat since HEED
avoids repeatedly draining already-low-energy nodes as CHs.
"""

import json
import os
import random
import statistics

import networkx as nx

from trust_aware_routing import build_graph

NUM_ROUNDS = 20
OUTPUT_PATH = "outputs/baseline_heed_results.json"
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

# HEED cluster-head selection: a node's probability of becoming CH this
# round is proportional to its normalized residual energy times a
# 'cost' factor from its node degree (fewer neighbors = less desirable
# CH, since it can't cover as much of the cluster efficiently). Nodes
# below this energy floor are never selected as CH regardless of
# degree, matching HEED's real behavior of excluding near-dead nodes.
MIN_ENERGY_TO_BE_CH = 0.1
CH_ENERGY_PENALTY = 0.10  # same relative CH overhead cost as LEACH, for a fair comparison
TARGET_CH_COUNT_FRACTION = 0.05  # aim for ~5% of nodes as CH per round, same target as LEACH


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


def select_cluster_heads(node_ids, energy_state, node_degree, target_count):
    """
    HEED-style CH selection: eligible nodes (energy above floor) are
    ranked by a combined energy x degree score, and the top `target_count`
    become cluster heads this round. This is what actually differs from
    LEACH's pure-random selection.
    """
    eligible = [nid for nid in node_ids if energy_state[nid] > MIN_ENERGY_TO_BE_CH]
    if not eligible:
        return []

    def heed_score(nid):
        # higher residual energy and higher degree both increase score
        return energy_state[nid] * (1.0 + 0.1 * node_degree.get(nid, 0))

    ranked = sorted(eligible, key=heed_score, reverse=True)
    return ranked[:target_count]


def simulate_round(round_num, node_ids, energy_state, mean_v, std_v, decay_multiplier,
                    node_degree, target_ch_count):
    attacked_nodes = []
    attacked_node_types = {}

    base_decay = 0.03 + (round_num * 0.004)

    cluster_heads = select_cluster_heads(node_ids, energy_state, node_degree, target_ch_count)
    ch_set = set(cluster_heads)

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
        if nid in ch_set:
            node_decay *= (1.0 + CH_ENERGY_PENALTY)
        energy_state[nid] = max(0.0, energy_state[nid] - node_decay + (jitter * 0.01))

    return attacked_nodes, attacked_node_types, cluster_heads


def main():
    random.seed(42)  # same seed as LEACH/digital twin for a fair comparison

    sim, energy_forecast = load_inputs()
    node_ids = sim["node_ids"]
    edges = sim["edges"]
    baseline_routes = sim["baseline_routes"]

    G = build_graph(node_ids, edges)
    mean_v, std_v = build_energy_trend(energy_forecast)

    # node degree from the actual topology -- used for HEED's CH cost function
    node_degree = {nid: G.degree(nid) for nid in node_ids}

    energy_state = {nid: 1.0 for nid in node_ids}
    decay_multiplier = {nid: random.uniform(0.5, 1.6) for nid in node_ids}

    target_ch_count = max(1, int(len(node_ids) * TARGET_CH_COUNT_FRACTION))

    results = {"protocol": "HEED", "num_rounds": NUM_ROUNDS, "rounds": []}

    total_nodes = len(node_ids)
    half_node_count = total_nodes // 2
    first_node_death_round = None
    half_node_death_round = None
    last_node_death_round = None

    for round_num in range(NUM_ROUNDS):
        attacked_nodes, attacked_node_types, cluster_heads = simulate_round(
            round_num, node_ids, energy_state, mean_v, std_v, decay_multiplier,
            node_degree, target_ch_count
        )
        true_attacked_set = set(attacked_nodes)

        hop_counts = []
        compromised = 0
        successful_routes = 0
        compromised_routes_detail = []

        for route in baseline_routes:
            src, dst = route["source"], route["destination"]
            try:
                path = nx.shortest_path(G, src, dst)
                path_found = True
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                path_found = False
                path = []

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
            "cluster_heads": cluster_heads,
            "num_cluster_heads": len(cluster_heads),
            "compromised_routes_pct": compromised_pct,
            "compromised_routes_detail": compromised_routes_detail,
            "packet_delivery_ratio_pct": pdr,
            "avg_hop_count": avg_hop_count,
            "avg_energy_remaining": avg_energy_remaining,
            "num_dead_nodes": num_dead_nodes,
        })

        print(f"[HEED] Round {round_num}: attacked={len(attacked_nodes)}  "
              f"CHs={len(cluster_heads)}  "
              f"compromised_routes={compromised_pct}%  pdr={pdr}%  "
              f"avg_hop={avg_hop_count}  avg_energy={avg_energy_remaining}  "
              f"dead_nodes={num_dead_nodes}")

    all_pdr = [r["packet_delivery_ratio_pct"] for r in results["rounds"]]
    all_compromised = [r["compromised_routes_pct"] for r in results["rounds"]]
    all_hops = [r["avg_hop_count"] for r in results["rounds"]]

    results["summary"] = {
        "avg_packet_delivery_ratio_pct": round(statistics.mean(all_pdr), 2),
        "avg_compromised_routes_pct": round(statistics.mean(all_compromised), 2),
        "avg_hop_count": round(statistics.mean(all_hops), 2),
        "avg_energy_remaining_final": results["rounds"][-1]["avg_energy_remaining"],
        "final_num_dead_nodes": results["rounds"][-1]["num_dead_nodes"],
        "detection_accuracy_pct": None,
        "note": (
            "HEED has no trust engine or attack classifier, so "
            "detection_accuracy_pct is not applicable (null). Unlike LEACH, "
            "HEED's cluster-head selection is energy- and degree-aware, "
            "which should improve energy lifetime (later FND/HND) but has "
            "no effect on compromised_routes_pct, since routing itself is "
            "still plain shortest-path with no attack-awareness."
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
          f"avg_hop={results['summary']['avg_hop_count']}  "
          f"FND={first_node_death_round}  HND={half_node_death_round}  LND={last_node_death_round}")


if __name__ == "__main__":
    main()