"""
baseline_leach.py
LEACH baseline simulation for comparison against TA-DT (this project's protocol).

Reuses the same topology, energy decay model, and real attack-type
injection ratios as digital_twin_sim.py, for a fair apples-to-apples
comparison. Unlike TA-DT, LEACH has NO trust engine, NO attack
classifier, and NO exclusion logic -- it routes via plain shortest
path, blind to which nodes are compromised. Cluster-head rotation
follows the classic LEACH probability model and adds an extra energy
cost to whichever node is CH each round (relaying overhead), but does
not affect routing decisions themselves, since this project's routing
graph is fixed rather than cluster-based.

Same random seed (42) as digital_twin_sim.py is used so both baselines
see the exact same sequence of attacks and energy jitter -- differences
in the results are due to the routing/detection strategy, not luck.
"""

import json
import os
import random
import statistics

import networkx as nx

from trust_aware_routing import build_graph

NUM_ROUNDS = 20
OUTPUT_PATH = "outputs/baseline_leach_results.json"
DEAD_ENERGY_THRESHOLD = 0.0

# Same real attack-type ratios as digital_twin_sim.py, for a fair comparison
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

# Classic LEACH: each node has this probability of becoming a cluster
# head in a given round (typical literature value is 5%)
CH_PROBABILITY = 0.05
CH_ENERGY_PENALTY = 0.10  # extra relative energy cost for being CH this round


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


def simulate_round(round_num, node_ids, energy_state, mean_v, std_v, decay_multiplier):
    """
    Decay energy and inject attacks using the same real ratios as the
    digital twin. LEACH has no detection mechanism at all -- attacked
    nodes are never identified or excluded, so every attack that lands
    on a routing path stays there.
    """
    attacked_nodes = []
    attacked_node_types = {}
    cluster_heads = []

    base_decay = 0.03 + (round_num * 0.004)

    for nid in node_ids:
        attack_type = random.choices(ATTACK_TYPES, weights=ATTACK_WEIGHTS, k=1)[0]
        is_attacked = attack_type != "none"
        if is_attacked:
            attacked_nodes.append(nid)
            attacked_node_types[nid] = attack_type

        # LEACH cluster-head rotation: independent probability per node
        # per round, no energy- or trust-awareness in the selection itself
        is_ch = random.random() < CH_PROBABILITY
        if is_ch:
            cluster_heads.append(nid)

        jitter = random.gauss(0, std_v) / mean_v
        node_decay = base_decay * decay_multiplier[nid]
        if is_attacked:
            node_decay *= (1.0 + ATTACK_ENERGY_PENALTY[attack_type])
        if is_ch:
            node_decay *= (1.0 + CH_ENERGY_PENALTY)
        energy_state[nid] = max(0.0, energy_state[nid] - node_decay + (jitter * 0.01))

    return attacked_nodes, attacked_node_types, cluster_heads


def main():
    random.seed(42)  # same seed as digital_twin_sim.py for a fair comparison

    sim, energy_forecast = load_inputs()
    node_ids = sim["node_ids"]
    edges = sim["edges"]
    baseline_routes = sim["baseline_routes"]

    G = build_graph(node_ids, edges)
    mean_v, std_v = build_energy_trend(energy_forecast)

    energy_state = {nid: 1.0 for nid in node_ids}
    decay_multiplier = {nid: random.uniform(0.5, 1.6) for nid in node_ids}

    results = {"protocol": "LEACH", "num_rounds": NUM_ROUNDS, "rounds": []}

    total_nodes = len(node_ids)
    half_node_count = total_nodes // 2
    first_node_death_round = None
    half_node_death_round = None
    last_node_death_round = None

    for round_num in range(NUM_ROUNDS):
        attacked_nodes, attacked_node_types, cluster_heads = simulate_round(
            round_num, node_ids, energy_state, mean_v, std_v, decay_multiplier
        )
        true_attacked_set = set(attacked_nodes)

        # --- routing: plain shortest path, NO trust/attack-awareness ---
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

        print(f"[LEACH] Round {round_num}: attacked={len(attacked_nodes)}  "
              f"CHs={len(cluster_heads)}  "
              f"compromised_routes={compromised_pct}%  pdr={pdr}%  "
              f"avg_hop={avg_hop_count}  avg_energy={avg_energy_remaining}  "
              f"dead_nodes={num_dead_nodes}")

    # --- summary metrics, matching the format your comparison table needs ---
    all_pdr = [r["packet_delivery_ratio_pct"] for r in results["rounds"]]
    all_compromised = [r["compromised_routes_pct"] for r in results["rounds"]]
    all_hops = [r["avg_hop_count"] for r in results["rounds"]]
    all_energy = [r["avg_energy_remaining"] for r in results["rounds"]]

    results["summary"] = {
        "avg_packet_delivery_ratio_pct": round(statistics.mean(all_pdr), 2),
        "avg_compromised_routes_pct": round(statistics.mean(all_compromised), 2),
        "avg_hop_count": round(statistics.mean(all_hops), 2),
        "avg_energy_remaining_final": results["rounds"][-1]["avg_energy_remaining"],
        "final_num_dead_nodes": results["rounds"][-1]["num_dead_nodes"],
        "detection_accuracy_pct": None,  # LEACH has no detection mechanism -- N/A, not 0
        "note": (
            "LEACH has no trust engine or attack classifier, so "
            "detection_accuracy_pct is not applicable (null) rather than "
            "zero -- there is no detection to measure accuracy of. "
            "compromised_routes_pct reflects routes that passed through "
            "an attacked node purely because LEACH's shortest-path "
            "routing has no way to avoid it."
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