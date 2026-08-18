"""
confirm_fallback_hypothesis.py

Checks whether the 17 frozen compromised pairs are hitting
routing_mode == "fallback_no_trusted_path" -- i.e. excluding ~27% of the
network partitions the graph so no trusted path exists at all, forcing a
fallback to the raw unfiltered shortest path (which bypasses exclusion
AND the density penalty entirely). This would explain why no penalty
value changes the outcome for these specific pairs.
"""

import networkx as nx

from synthetic_trust_routing_grid_v2 import (
    generate_topology, pick_malicious_nodes, build_classifier_and_trust,
    sample_route_pairs, NUM_ROUTE_PAIRS,
)
from trust_aware_routing import (
    build_graph, get_excluded_nodes, route_with_trust_clustering_aware,
    compute_cluster_density,
)

NUM_NODES = 750
MALICIOUS_PCT = 0.25
SEED = 750 + 25


def main():
    node_ids, edges, positions = generate_topology(NUM_NODES, SEED)
    G = build_graph(node_ids, edges)
    malicious_set = pick_malicious_nodes(node_ids, positions, MALICIOUS_PCT, "clustered", SEED)
    classifier, trust_scores = build_classifier_and_trust(node_ids, malicious_set, SEED)
    route_pairs = sample_route_pairs(node_ids, NUM_ROUTE_PAIRS, SEED)
    excluded = get_excluded_nodes(node_ids, classifier, trust_scores)
    density = compute_cluster_density(G, excluded, radius=2)

    print(f"Total nodes: {len(node_ids)}, Excluded: {len(excluded)} ({100*len(excluded)/len(node_ids):.1f}%)")

    G_trusted_check = G.copy()
    G_trusted_check.remove_nodes_from(excluded)
    print(f"Connected components after exclusion: {nx.number_connected_components(G_trusted_check)}")
    comp_sizes = sorted([len(c) for c in nx.connected_components(G_trusted_check)], reverse=True)
    print(f"Component sizes (top 10): {comp_sizes[:10]}")

    mode_counts = {}
    fallback_examples = []
    for source, destination in route_pairs:
        if not nx.has_path(G, source, destination):
            continue
        result = route_with_trust_clustering_aware(
            G, source, destination, excluded, classifier, density=density, density_penalty=90.0
        )
        mode = result["routing_mode"]
        mode_counts[mode] = mode_counts.get(mode, 0) + 1
        if mode == "fallback_no_trusted_path":
            fallback_examples.append((source, destination))

    print(f"\nRouting mode breakdown: {mode_counts}")
    print(f"Fallback pairs (bypass exclusion + weighting entirely): {len(fallback_examples)}")
    print(f"Sample: {fallback_examples[:5]}")


if __name__ == "__main__":
    main()