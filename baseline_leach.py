"""
baseline_leach.py
LEACH baseline simulation for comparison against TA-DT (this project's protocol).

Reuses the same topology, energy decay model, and real attack-type
injection ratios as digital_twin_sim.py, for a fair apples-to-apples
comparison. Unlike TA-DT, LEACH has NO trust engine, NO attack
classifier, and NO exclusion logic -- it routes via plain shortest
path, blind to which nodes are compromised. Cluster-head rotation
follows the classic LEACH probability model and adds an extra energy
cost to whichever node is CH each round (relaying overhead).

v2 (protocol-aware, per-round forwarding_count):
Unlike the v1 static patch (a single forwarding-centrality multiplier
computed once via protocol-blind plain shortest path -- which made
LEACH/HEED/TBR converge to identical FND/HND, since the multiplier was
topology-driven rather than protocol-driven), forwarding_count/
decay_multiplier is now recomputed INSIDE the round loop, using a
WEIGHTED shortest path where edge weights reflect LEACH's actual
per-round routing preference: edges touching this round's cluster-heads
(ch_set) get cost 0.3 vs 1.0 for non-CH edges, since LEACH's real-world
behavior routes cluster traffic through CHs preferentially. This mirrors
the same pattern used in baseline_heed.py's v2 patch, but driven by
LEACH's own per-round randomly-selected ch_set rather than HEED's
energy/degree-ranked one.

Same random seed (42) as digital_twin_sim.py is used so both baselines
see the exact same sequence of attacks and energy jitter -- differences
in the results are due to the routing/detection strategy, not luck.
"""

import json
import os
import random
import argparse
_parser = argparse.ArgumentParser()
_parser.add_argument("--seed", type=int, default=42)
_args, _ = _parser.parse_known_args()
SEED = _args.seed

import statistics

import networkx as nx

from trust_aware_routing import build_graph

NUM_ROUNDS = 23
OUTPUT_PATH = f"outputs/baseline_leach_results_seed{SEED}.json"
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
    with open(f"outputs/routing_simulation_seed{SEED}.json") as f:
        sim = json.load(f)
    with open("outputs/energy_forecast_ibrl.json") as f:
        energy = json.load(f)
    return sim, energy


def build_energy_trend(energy_forecast):
    voltages = list(energy_forecast["next_voltage_forecast_volts"].values())
    mean_v = statistics.mean(voltages)
    std_v = statistics.stdev(voltages)
    return mean_v, std_v


def simulate_round(round_num, node_ids, energy_state, mean_v, std_v, G, baseline_routes,
                    ch_set):
    """
    Decay energy and inject attacks using the same real ratios as the
    digital twin. LEACH has no detection mechanism at all -- attacked
    nodes are never identified or excluded, so every attack that lands
    on a routing path stays there.
    """
    attacked_nodes = []
    attacked_node_types = {}

    base_decay = 0.03 + (round_num * 0.004)

    # Protocol-aware forwarding_count: weight edges so shortest paths
    # preferentially route through this round's cluster-heads, the same
    # way LEACH itself would prefer CHs as relay points. Matches the
    # averaged-endpoint-cost weighting used in baseline_heed.py's v2 patch,
    # so forwarding pressure is computed the same way across protocols.
    for u, v in G.edges():
        cost_u = 0.3 if u in ch_set else 1.0
        cost_v = 0.3 if v in ch_set else 1.0
        G[u][v]['weight'] = (cost_u + cost_v) / 2

    forwarding_count = {nid: 0 for nid in node_ids}
    for route in baseline_routes:
        src, dst = route["source"], route["destination"]
        try:
            path = nx.shortest_path(G, src, dst, weight='weight')
            for nid in path[1:-1]:
                forwarding_count[nid] += 1
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            continue
    max_fc = max(forwarding_count.values()) if forwarding_count.values() else 1
    max_fc = max(max_fc, 1)
    decay_multiplier = {
        nid: 0.7 + 0.3 * min(forwarding_count[nid] / max_fc, 1.0) + random.uniform(-0.05, 0.05)
        for nid in node_ids
    }

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

    return attacked_nodes, attacked_node_types


def main():
    random.seed(SEED)  # same seed as digital_twin_sim.py for a fair comparison

    sim, energy_forecast = load_inputs()
    node_ids = sim["node_ids"]
    edges = sim["edges"]
    baseline_routes = sim["baseline_routes"]

    G = build_graph(node_ids, edges)
    mean_v, std_v = build_energy_trend(energy_forecast)

    energy_state = {nid: 1.0 for nid in node_ids}

    results = {"protocol": "LEACH", "num_rounds": NUM_ROUNDS, "rounds": []}

    total_nodes = len(node_ids)
    half_node_count = total_nodes // 2
    first_node_death_round = None
    half_node_death_round = None
    last_node_death_round = None

    for round_num in range(NUM_ROUNDS):
        # LEACH cluster-head rotation: independent probability per node
        # per round, no energy- or trust-awareness in the selection itself
        cluster_heads = [nid for nid in node_ids if random.random() < CH_PROBABILITY]
        ch_set = set(cluster_heads)

        attacked_nodes, attacked_node_types = simulate_round(
            round_num, node_ids, energy_state, mean_v, std_v, G, baseline_routes, ch_set
        )
        true_attacked_set = set(attacked_nodes)

        # --- routing: plain shortest path, NO trust/attack-awareness ---
        # (unweighted hop-count path, matching LEACH's real routing
        # behavior -- the CH-weighted graph above is only used to derive
        # forwarding_count/energy decay, not to route data traffic itself)
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
            "routing has no way to avoid it. v2: forwarding_count/"
            "decay_multiplier are recomputed each round from THIS round's "
            "CH-weighted shortest paths, so energy decay is protocol-aware "
            "(driven by LEACH's own per-round cluster-head set) rather than "
            "a static topology-only multiplier."
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