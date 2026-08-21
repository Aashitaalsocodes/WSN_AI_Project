"""
Phase 1 sanity check for threshold-adaptive trust (Mitigation 5).
Run this BEFORE touching synthetic_trust_routing_grid_v2.py.
Does not modify any existing file.
"""

from synthetic_trust_routing_grid_v2 import (
    generate_topology,
    pick_malicious_nodes,
    build_classifier_and_trust,
    radius_for_density,
)
from trust_aware_routing import build_graph, get_excluded_nodes
from trust_aware_routing_threshold import (
    compute_spatial_density_from_positions,
    compute_density_percentile_breakpoints,
    build_excluded_with_adaptive_trust,
)

NUM_NODES = 500
MALICIOUS_PCT = 0.25
SEED = 42

node_ids, edges, positions = generate_topology(NUM_NODES, SEED)
G = build_graph(node_ids, edges)
radius = radius_for_density(NUM_NODES)

malicious_set = pick_malicious_nodes(node_ids, positions, MALICIOUS_PCT, "clustered", SEED)
classifier, trust_scores = build_classifier_and_trust(node_ids, malicious_set, SEED)

# old fixed-threshold exclusion (for comparison)
excluded_fixed = get_excluded_nodes(node_ids, classifier, trust_scores)

# new adaptive-threshold exclusion
spatial_density = compute_spatial_density_from_positions(node_ids, positions, radius)
dens_low, dens_high = compute_density_percentile_breakpoints(spatial_density, 30, 70)
excluded_adaptive, threshold_used = build_excluded_with_adaptive_trust(
    node_ids, classifier, trust_scores, spatial_density,
    dens_low=dens_low, dens_high=dens_high,
)

density_values = sorted(spatial_density.values())
print("Density distribution:")
print("  min:", round(density_values[0], 4))
print("  max:", round(density_values[-1], 4))
print("  dens_low (30th pct):", round(dens_low, 4))
print("  dens_high (70th pct):", round(dens_high, 4))

thresh_counts = {}
for t in threshold_used.values():
    thresh_counts[t] = thresh_counts.get(t, 0) + 1
print("\nThreshold assignment counts (None = excluded via classifier):")
for t, c in sorted(thresh_counts.items(), key=lambda x: (x[0] is None, x[0])):
    print(f"  threshold={t}: {c} nodes")

newly_excluded = excluded_adaptive - excluded_fixed
print(f"\nFixed-threshold excluded: {len(excluded_fixed)}")
print(f"Adaptive-threshold excluded: {len(excluded_adaptive)}")
print(f"Newly excluded by adaptive (not by fixed): {len(newly_excluded)}")

print("\nTrust scores of newly-excluded nodes (should mostly be 0.25-0.4):")
for nid in list(newly_excluded)[:15]:
    ts = trust_scores.get(int(nid), trust_scores.get(nid, 1.0))
    print(f"  node {nid}: trust={round(ts,3)}, density={round(spatial_density.get(nid,0),4)}")