"""
tune_density_penalty.py

The full sweep showed trust_aware_clustering_compromised_pct IDENTICAL to
trust_aware_compromised_pct at density_penalty=8.0 across all 25 clustered
configs -- meaning paths shifted slightly (hop count +0.282 avg) but never
enough to actually avoid an undetected attacker. This mirrors the earlier
isolated test, where penalty needed to reach ~20 before the router chose
the longer, safer path over a shorter risky one.

This script re-runs a SMALL subset (just distribution="clustered", a few
node counts, fewer seeds) across several density_penalty values to find
where the improvement actually kicks in, before committing to a full
750-config re-run with a new default.

Does not modify any project files -- pure read + in-memory experiment.

Usage:
    python tune_density_penalty.py
"""

import random
from statistics import mean

import networkx as nx

from synthetic_trust_routing_grid_v2 import (
    generate_topology,
    pick_malicious_nodes,
    build_classifier_and_trust,
    sample_route_pairs,
    NUM_ROUTE_PAIRS,
)
from trust_aware_routing import (
    build_graph,
    get_excluded_nodes,
    route_with_trust_clustering_aware,
    compute_cluster_density,
)

NODE_COUNTS = [250, 750]
MALICIOUS_PCTS = [0.15, 0.25]
SEEDS_PER_CONFIG = 8
PENALTIES_TO_TEST = [8.0, 15.0, 25.0, 40.0, 60.0, 90.0]


def run_one(num_nodes, malicious_pct, seed, penalty):
    node_ids, edges, positions = generate_topology(num_nodes, seed)
    G = build_graph(node_ids, edges)
    malicious_set = pick_malicious_nodes(node_ids, positions, malicious_pct, "clustered", seed)
    classifier, trust_scores = build_classifier_and_trust(node_ids, malicious_set, seed)
    route_pairs = sample_route_pairs(node_ids, NUM_ROUTE_PAIRS, seed)
    excluded = get_excluded_nodes(node_ids, classifier, trust_scores)
    density = compute_cluster_density(G, excluded, radius=2)

    compromised = 0
    valid = 0
    hops = []
    for source, destination in route_pairs:
        if not nx.has_path(G, source, destination):
            continue
        valid += 1
        result = route_with_trust_clustering_aware(
            G, source, destination, excluded, classifier, density=density, density_penalty=penalty
        )
        if result["path_found"]:
            attacked = [n for n in result["path"] if n in malicious_set and n not in (source, destination)]
            if attacked:
                compromised += 1
            hops.append(result["hop_count"])
    if valid == 0:
        return None
    return 100 * compromised / valid, mean(hops) if hops else 0


def main():
    print(f"{'penalty':>8} | {'avg_compromised_pct':>20} | {'avg_hops':>10}")
    print("-" * 46)
    for penalty in PENALTIES_TO_TEST:
        all_pct = []
        all_hops = []
        for num_nodes in NODE_COUNTS:
            for malicious_pct in MALICIOUS_PCTS:
                for seed_offset in range(SEEDS_PER_CONFIG):
                    seed = 1000 * seed_offset + num_nodes + int(malicious_pct * 100)
                    r = run_one(num_nodes, malicious_pct, seed, penalty)
                    if r is not None:
                        all_pct.append(r[0])
                        all_hops.append(r[1])
        print(f"{penalty:>8.1f} | {mean(all_pct):>20.2f} | {mean(all_hops):>10.2f}")


if __name__ == "__main__":
    main()