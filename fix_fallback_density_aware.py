"""
fix_fallback_density_aware.py

Root-cause fix for the frozen-compromised-pct finding: when excluding
flagged/low-trust nodes fragments the graph (e.g. 26.7% exclusion split a
750-node network into a 545-node component + 2 tiny stranded ones), NO
trusted path exists for pairs spanning the split, so
route_with_trust_clustering_aware() falls back to *unweighted*
nx.shortest_path on the full graph -- completely bypassing the density
penalty. This is why no density_penalty value (8 to 90 tested) ever
changed the outcome for those specific pairs: the weighted routing logic
never runs for them.

Fix: when forced to fall back, still use density-weighted Dijkstra on the
full graph instead of unweighted shortest_path, so among the necessary
excluded-territory-crossing routes, the one with the LOWEST attacker
density is chosen -- rather than blindly taking the geometrically shortest
one, which may cut straight through the densest part of the cluster.

Patches ONLY the fallback branch inside route_with_trust_clustering_aware
in trust_aware_routing.py. The primary (non-fallback) path, route_with_trust,
get_excluded_nodes, build_graph, and compute_cluster_density are untouched.

Usage:
    python fix_fallback_density_aware.py
"""

from pathlib import Path

TARGET = Path("trust_aware_routing.py")
BACKUP = Path("trust_aware_routing.py.bak_fallback")

OLD_FALLBACK = '''    except nx.NetworkXNoPath:
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

NEW_FALLBACK = '''    except nx.NetworkXNoPath:
        # No trusted path exists -- the exclusion has fragmented the graph
        # for this pair. Instead of falling back to a blind unweighted
        # shortest path (which can cut straight through the densest part
        # of the attacker cluster), fall back to density-WEIGHTED routing
        # on the full graph: among routes forced to cross excluded
        # territory, prefer the one with lowest attacker density.
        try:
            path = nx.dijkstra_path(G, source=source, target=destination, weight=edge_weight)
            attacked_in_path = [
                n for n in path
                if classifier.get(n, {}).get("predicted_attacked", 0) == 1
            ]
            return {
                "path": path,
                "hop_count": len(path) - 1,
                "passes_through_attacked_node": len(attacked_in_path) > 0,
                "attacked_nodes_in_path": attacked_in_path,
                "routing_mode": "fallback_density_weighted",
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

    assert "def route_with_trust_clustering_aware" in original, (
        "route_with_trust_clustering_aware not found -- run fix_trust_aware_routing_clustering.py first"
    )
    assert original.count(OLD_FALLBACK) == 1, (
        f"Expected exactly one occurrence of the old fallback block, found {original.count(OLD_FALLBACK)} -- "
        "aborting, file may already be patched or structure changed"
    )
    assert "fallback_density_weighted" not in original, "Already patched -- aborting"

    BACKUP.write_text(original, encoding="utf-8")
    print(f"Backup written to {BACKUP}")

    patched = original.replace(OLD_FALLBACK, NEW_FALLBACK, 1)

    assert "fallback_density_weighted" in patched
    assert patched.count("def route_with_trust(") == 1
    assert patched.count("def route_with_trust_clustering_aware(") == 1
    assert "def get_excluded_nodes(" in patched
    assert "def build_graph(" in patched

    TARGET.write_text(patched, encoding="utf-8")
    print(f"Patched {TARGET}: fallback branch in route_with_trust_clustering_aware "
          "now uses density-weighted Dijkstra instead of unweighted shortest_path.")
    print("route_with_trust() (original, unweighted) untouched -- used for baseline comparison as before.")


if __name__ == "__main__":
    main()