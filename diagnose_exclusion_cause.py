"""
diagnose_exclusion_cause.py

Before building soft-exclusion, check WHICH criterion is actually driving
the exclusion of nodes in the fragmenting pocket: classifier flag
(predicted_attacked=1, hard to soften without hurting detection) vs trust
threshold alone (soft to relax). If it's almost entirely classifier-driven,
softening the trust threshold won't open new bridges.
"""

import networkx as nx

from synthetic_trust_routing_grid_v2 import (
    generate_topology, pick_malicious_nodes, build_classifier_and_trust,
)
from trust_aware_routing import build_graph, TRUST_THRESHOLD

NUM_NODES = 750
MALICIOUS_PCT = 0.25
SEED = 750 + 25


def main():
    node_ids, edges, positions = generate_topology(NUM_NODES, SEED)
    G = build_graph(node_ids, edges)
    malicious_set = pick_malicious_nodes(node_ids, positions, MALICIOUS_PCT, "clustered", SEED)
    classifier, trust_scores = build_classifier_and_trust(node_ids, malicious_set, SEED)

    classifier_flagged = {n for n in node_ids if classifier.get(n, {}).get("predicted_attacked", 0) == 1}
    trust_low = {n for n in node_ids if trust_scores.get(int(n), 1.0) < TRUST_THRESHOLD}

    excluded = classifier_flagged | trust_low
    only_classifier = classifier_flagged - trust_low
    only_trust = trust_low - classifier_flagged
    both = classifier_flagged & trust_low

    print(f"Total excluded: {len(excluded)}")
    print(f"  Flagged by classifier only (trust was OK):  {len(only_classifier)}")
    print(f"  Flagged by trust threshold only (classifier missed): {len(only_trust)}")
    print(f"  Flagged by BOTH: {len(both)}")

    # Check the small stranded components specifically
    G_trusted = G.copy()
    G_trusted.remove_nodes_from(excluded)
    components = sorted(nx.connected_components(G_trusted), key=len)
    small_components = [c for c in components if len(c) < 20]
    print(f"\nSmall stranded components (<20 nodes): {len(small_components)}")

    # For nodes bordering the small components, check what's keeping the
    # bridge closed: are the bridge nodes classifier-only, trust-only, or both?
    for comp in small_components[:3]:
        comp_neighbors = set()
        for n in comp:
            comp_neighbors.update(G.neighbors(n))
        bridge_nodes = comp_neighbors - comp
        bridge_excluded = bridge_nodes & excluded
        print(f"\nStranded component (size {len(comp)}): {comp}")
        print(f"  Bridge (boundary) nodes: {bridge_nodes}")
        for b in bridge_excluded:
            reason = []
            if b in classifier_flagged:
                reason.append("classifier-flagged")
            if b in trust_low:
                reason.append(f"trust={trust_scores.get(int(b), 1.0):.3f}<{TRUST_THRESHOLD}")
            print(f"    {b}: excluded because {' AND '.join(reason)}")


if __name__ == "__main__":
    main()