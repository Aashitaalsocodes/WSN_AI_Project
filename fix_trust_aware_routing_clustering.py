"""
fix_trust_aware_routing_clustering.py

Assertion-guarded patch: adds a clustering-aware density penalty on top of
the existing trust-aware exclusion routing in trust_aware_routing.py.

Addresses the paper's identified limitation: TA-DT's compromised-route rate
rises from 7.06% (random attackers) to 21.42% (spatially clustered attackers),
because the ~10% of attackers that evade detection concentrate at routing
chokepoints, limiting the trust mechanism's ability to find safe alternate
paths (Figure 8, Discussion).

Fix: instead of only hard-excluding flagged/low-trust nodes and taking the
shortest remaining path (which can still cut straight through a chokepoint
if that's the only/shortest surviving route), route with a WEIGHTED cost
that penalizes proximity to *observed* excluded-node density (flagged +
low-trust nodes -- the only signal a real system actually has, not oracle
knowledge of the true malicious set). This should route around dense
pockets even when it can't identify every individual malicious node in them.

Adds two new functions to trust_aware_routing.py:
  - compute_cluster_density(G, excluded, radius=2)
  - route_with_trust_clustering_aware(G, source, destination, excluded,
        classifier, density=None, density_penalty=3.0)

Does NOT modify get_excluded_nodes, route_with_trust, build_graph, or any
existing behavior -- purely additive, so existing results/outputs are
untouched and reproducible.

Usage:
    python fix_trust_aware_routing_clustering.py
"""

from pathlib import Path

TARGET = Path("trust_aware_routing.py")
BACKUP = Path("trust_aware_routing.py.bak_clustering")

ANCHOR = 'def route_with_trust(\n'

NEW_FUNCTIONS = '''def compute_cluster_density(G, excluded: set, radius: int = 2) -> dict:
    """
    For every node in G, estimate the local density of *observed* excluded
    nodes (flagged by classifier OR low trust) within `radius` hops.

    This is a proxy for "am I near a routing chokepoint that clustered
    attackers have concentrated around" -- built only from information a
    real deployed system actually has (which nodes got flagged / lost
    trust), not oracle knowledge of the true malicious set. Detected
    attackers are already excluded outright; this additionally penalizes
    routing *near* dense excluded regions, where undetected attackers in
    the same cluster are statistically more likely to be sitting on the
    only remaining path.

    Returns: {node_id: density_score in [0, 1]}
    """
    density = {}
    for node in G.nodes():
        try:
            neighborhood = nx.single_source_shortest_path_length(G, node, cutoff=radius)
        except nx.NodeNotFound:
            density[node] = 0.0
            continue
        neighborhood_nodes = set(neighborhood.keys())
        if len(neighborhood_nodes) <= 1:
            density[node] = 0.0
            continue
        excluded_nearby = len(neighborhood_nodes & excluded)
        density[node] = excluded_nearby / len(neighborhood_nodes)
    return density


def route_with_trust_clustering_aware(
    G: nx.Graph,
    source: str,
    destination: str,
    excluded: set,
    classifier: dict,
    density: dict = None,
    density_penalty: float = 8.0,
) -> dict:
    """
    Clustering-aware variant of route_with_trust: same hard exclusion of
    flagged/low-trust nodes, but routes via weighted Dijkstra instead of
    plain shortest_path. Edge weight rises with the excluded-node density
    near each endpoint, so paths bend away from cluster chokepoints instead
    of cutting straight through them when a shorter-but-riskier path exists.

    Falls back to baseline routing if no trust-aware path exists at all,
    same as route_with_trust.
    """
    nodes_to_remove = excluded - {source, destination}
    G_trusted = G.copy()
    G_trusted.remove_nodes_from(nodes_to_remove)

    if density is None:
        density = compute_cluster_density(G, excluded)

    def edge_weight(u, v, edge_attrs):
        du = density.get(u, 0.0)
        dv = density.get(v, 0.0)
        avg_density = (du + dv) / 2
        return 1.0 + density_penalty * avg_density

    try:
        path = nx.dijkstra_path(G_trusted, source=source, target=destination, weight=edge_weight)
        attacked_in_path = [
            n for n in path
            if classifier.get(n, {}).get("predicted_attacked", 0) == 1
            and n not in (source, destination)
        ]
        return {
            "path": path,
            "hop_count": len(path) - 1,
            "passes_through_attacked_node": len(attacked_in_path) > 0,
            "attacked_nodes_in_path": attacked_in_path,
            "routing_mode": "trust_aware_clustering",
            "path_found": True,
        }
    except nx.NetworkXNoPath:
        try:
            path = nx.shortest_path(G, source=source, target=destination)
            attacked_in_path = [
                n for n in path
                if classifier.get(n, {}).get("predicted_attacked", 0) == 1
            ]
            return {
                "path": path,
                "hop_count": len(path) - 1,
                "passes_through_attacked_node": len(attacked_in_path) > 0,
                "attacked_nodes_in_path": attacked_in_path,
                "routing_mode": "fallback_no_trusted_path",
                "path_found": True,
            }
        except nx.NetworkXNoPath:
            return {
                "path": [],
                "hop_count": -1,
                "passes_through_attacked_node": False,
                "attacked_nodes_in_path": [],
                "routing_mode": "no_path",
                "path_found": False,
            }


def route_with_trust(\n'''


def main():
    assert TARGET.exists(), f"{TARGET} not found -- run this from the project root"
    original = TARGET.read_text(encoding="utf-8")

    assert original.count(ANCHOR) == 1, (
        f"Expected exactly one occurrence of route_with_trust def, found {original.count(ANCHOR)} -- "
        "aborting, file may already be patched or structure changed"
    )
    assert "def compute_cluster_density" not in original, "Already patched -- aborting"
    assert "def route_with_trust_clustering_aware" not in original, "Already patched -- aborting"

    BACKUP.write_text(original, encoding="utf-8")
    print(f"Backup written to {BACKUP}")

    patched = original.replace(ANCHOR, NEW_FUNCTIONS, 1)

    assert "def compute_cluster_density" in patched
    assert "def route_with_trust_clustering_aware" in patched
    assert patched.count("def route_with_trust(") == 1
    # Original function body must still be fully intact and unmodified
    assert "def get_excluded_nodes(" in patched
    assert "def build_graph(" in patched

    TARGET.write_text(patched, encoding="utf-8")
    print(f"Patched {TARGET}: added compute_cluster_density() and route_with_trust_clustering_aware()")
    print("Original route_with_trust(), get_excluded_nodes(), build_graph() untouched.")


if __name__ == "__main__":
    main()