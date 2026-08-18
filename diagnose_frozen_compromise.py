"""
diagnose_frozen_compromise.py

The tuning sweep showed compromised_pct frozen at exactly 30.23% from
penalty=8 to penalty=90, while hop count kept rising. This checks WHETHER
the same specific (source, destination) pairs are compromised at every
penalty level (cut-vertex / no-alternate-path hypothesis), versus whether
the count just coincidentally stayed the same while different pairs
flipped in and out (which would suggest a different bug).

For each compromised pair at penalty=90, checks:
  1. Is the malicious node on EVERY simple path between source and dest
     (true cut vertex / unavoidable)?
  2. Or does an alternate path exist that the router just isn't choosing?

Usage:
    python diagnose_frozen_compromise.py
"""

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

NUM_NODES = 750
MALICIOUS_PCT = 0.25
SEED = 750 + 25  # matches seed_offset=0 case from the tuning script


def main():
    node_ids, edges, positions = generate_topology(NUM_NODES, SEED)
    G = build_graph(node_ids, edges)
    malicious_set = pick_malicious_nodes(node_ids, positions, MALICIOUS_PCT, "clustered", SEED)
    classifier, trust_scores = build_classifier_and_trust(node_ids, malicious_set, SEED)
    route_pairs = sample_route_pairs(node_ids, NUM_ROUTE_PAIRS, SEED)
    excluded = get_excluded_nodes(node_ids, classifier, trust_scores)
    density = compute_cluster_density(G, excluded, radius=2)

    print(f"Malicious set size: {len(malicious_set)}, Excluded (flagged) size: {len(excluded)}")
    undetected = malicious_set - excluded
    print(f"Undetected malicious nodes (evaded detection): {len(undetected)}")

    results_by_penalty = {}
    for penalty in [8.0, 90.0]:
        compromised_pairs = []
        for source, destination in route_pairs:
            if not nx.has_path(G, source, destination):
                continue
            result = route_with_trust_clustering_aware(
                G, source, destination, excluded, classifier, density=density, density_penalty=penalty
            )
            if result["path_found"]:
                attacked = [n for n in result["path"] if n in malicious_set and n not in (source, destination)]
                if attacked:
                    compromised_pairs.append((source, destination, tuple(attacked), tuple(result["path"])))
        results_by_penalty[penalty] = compromised_pairs

    low = {(s, d) for s, d, _, _ in results_by_penalty[8.0]}
    high = {(s, d) for s, d, _, _ in results_by_penalty[90.0]}
    print(f"\nCompromised pairs at penalty=8:  {len(low)}")
    print(f"Compromised pairs at penalty=90: {len(high)}")
    print(f"Identical pair set: {low == high}")
    print(f"Pairs fixed by higher penalty (in low, not high): {low - high}")
    print(f"New pairs broken by higher penalty (in high, not low): {high - low}")

    G_excl = G.copy()
    G_excl.remove_nodes_from(excluded)

    print("\n--- Cut-vertex check on still-compromised pairs (penalty=90) ---")
    checked = 0
    for source, destination, attacked, path in results_by_penalty[90.0][:8]:
        checked += 1
        attacker = attacked[0]
        G_without_attacker = G_excl.copy()
        if attacker in G_without_attacker:
            G_without_attacker.remove_node(attacker)
        if source in G_without_attacker and destination in G_without_attacker:
            has_alt = nx.has_path(G_without_attacker, source, destination)
        else:
            has_alt = None
        print(f"  {source}->{destination} via attacker {attacker}: "
              f"alternate path exists if this node removed = {has_alt}")

    print(f"\n(Checked {checked} sample compromised pairs)")


if __name__ == "__main__":
    main()