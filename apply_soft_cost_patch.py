"""
apply_soft_cost_patch.py

Run this from inside C:\\Users\\Admin\\WSN_AI_Project (same folder as
trust_aware_routing.py and synthetic_trust_routing_grid_v2.py).

It will:
  1. Back up both files (.bak_softcost)
  2. Add route_with_soft_cost() to trust_aware_routing.py
  3. Wire a fourth "soft_cost" mode into synthetic_trust_routing_grid_v2.py

Usage:
    python apply_soft_cost_patch.py
"""

import shutil
from pathlib import Path

ROUTING_FILE = Path("trust_aware_routing.py")
GRID_FILE = Path("synthetic_trust_routing_grid_v2.py")

SOFT_COST_FUNCTION = '''

def route_with_soft_cost(
    G: nx.Graph,
    source: str,
    destination: str,
    classifier: dict,
    trust_scores: dict,
    malicious_penalty: float = 15.0,
    trust_weight: float = 10.0,
) -> dict:
    """
    Full cost-based routing: no hard exclusion of any node. Every node
    stays in the graph, but edge cost rises for edges touching nodes that
    are flagged by the classifier and/or have low trust scores. This never
    fragments the graph (a path is found whenever one topologically
    exists), and it honestly reports when a route was forced through
    confirmed-malicious territory rather than hiding that behind a
    disconnected component or a blind unweighted fallback.

    Cost model per node n:
        node_cost(n) = 1.0
                       + malicious_penalty * predicted_attacked(n)
                       + trust_weight * max(0, TRUST_MIDPOINT - trust(n))

    Edge (u, v) weight = average of node_cost(u) and node_cost(v).

    Adapted from the teammate's cost model in routing_cost.py, but omits
    attack_type-specific weighting since this pipeline's classifier dict
    only carries a binary predicted_attacked flag, not an attack-type
    label (unlike the routing_cost.py pipeline used for the main paper
    results).
    """
    TRUST_MIDPOINT = 0.5

    def node_cost(n):
        pred = classifier.get(n, {})
        flagged = 1.0 if pred.get("predicted_attacked", 0) == 1 else 0.0
        trust = trust_scores.get(int(n), trust_scores.get(n, 1.0))
        trust_penalty = max(0.0, TRUST_MIDPOINT - trust)
        return 1.0 + malicious_penalty * flagged + trust_weight * trust_penalty

    def edge_weight(u, v, edge_attrs):
        return (node_cost(u) + node_cost(v)) / 2

    try:
        path = nx.dijkstra_path(G, source=source, target=destination, weight=edge_weight)
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
            "routing_mode": "soft_cost",
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
'''

GRID_IMPORT_OLD = """from trust_aware_routing import (
    build_graph,
    get_excluded_nodes,
    route_with_trust,
    compute_cluster_density,
    route_with_trust_clustering_aware,
)"""

GRID_IMPORT_NEW = """from trust_aware_routing import (
    build_graph,
    get_excluded_nodes,
    route_with_trust,
    compute_cluster_density,
    route_with_trust_clustering_aware,
    route_with_soft_cost,
)"""

RUN_SIM_OLD = """    clustering_compromised = 0
    clustering_hops = []
    valid_pairs = 0"""

RUN_SIM_NEW = """    clustering_compromised = 0
    clustering_hops = []
    soft_cost_compromised = 0
    soft_cost_hops = []
    valid_pairs = 0"""

LOOP_OLD = """        clustering_result = route_with_trust_clustering_aware(
            G, source, destination, excluded, classifier, density=density,
        )
        if clustering_result["path_found"]:
            clustering_attacked = [
                n for n in clustering_result["path"]
                if n in malicious_set and n not in (source, destination)
            ]
            if clustering_attacked:
                clustering_compromised += 1
            clustering_hops.append(clustering_result["hop_count"])"""

LOOP_NEW = """        clustering_result = route_with_trust_clustering_aware(
            G, source, destination, excluded, classifier, density=density,
        )
        if clustering_result["path_found"]:
            clustering_attacked = [
                n for n in clustering_result["path"]
                if n in malicious_set and n not in (source, destination)
            ]
            if clustering_attacked:
                clustering_compromised += 1
            clustering_hops.append(clustering_result["hop_count"])

        soft_cost_result = route_with_soft_cost(
            G, source, destination, classifier, trust_scores,
        )
        if soft_cost_result["path_found"]:
            soft_cost_attacked = [
                n for n in soft_cost_result["path"]
                if n in malicious_set and n not in (source, destination)
            ]
            if soft_cost_attacked:
                soft_cost_compromised += 1
            soft_cost_hops.append(soft_cost_result["hop_count"])"""

RETURN_OLD = """    return {
        "baseline_compromised_pct": round(100 * baseline_compromised / valid_pairs, 2),
        "trust_aware_compromised_pct": round(100 * trust_compromised / valid_pairs, 2),
        "trust_aware_clustering_compromised_pct": round(100 * clustering_compromised / valid_pairs, 2),
        "baseline_avg_hops": round(mean(baseline_hops), 3) if baseline_hops else 0,
        "trust_aware_avg_hops": round(mean(trust_hops), 3) if trust_hops else 0,
        "trust_aware_clustering_avg_hops": round(mean(clustering_hops), 3) if clustering_hops else 0,
        "valid_route_pairs": valid_pairs,
        "num_edges": len(edges),
    }"""

RETURN_NEW = """    return {
        "baseline_compromised_pct": round(100 * baseline_compromised / valid_pairs, 2),
        "trust_aware_compromised_pct": round(100 * trust_compromised / valid_pairs, 2),
        "trust_aware_clustering_compromised_pct": round(100 * clustering_compromised / valid_pairs, 2),
        "soft_cost_compromised_pct": round(100 * soft_cost_compromised / valid_pairs, 2),
        "baseline_avg_hops": round(mean(baseline_hops), 3) if baseline_hops else 0,
        "trust_aware_avg_hops": round(mean(trust_hops), 3) if trust_hops else 0,
        "trust_aware_clustering_avg_hops": round(mean(clustering_hops), 3) if clustering_hops else 0,
        "soft_cost_avg_hops": round(mean(soft_cost_hops), 3) if soft_cost_hops else 0,
        "valid_route_pairs": valid_pairs,
        "num_edges": len(edges),
    }"""

SUMMARY_OLD = """    keys = ["baseline_compromised_pct", "trust_aware_compromised_pct",
            "trust_aware_clustering_compromised_pct",
            "baseline_avg_hops", "trust_aware_avg_hops",
            "trust_aware_clustering_avg_hops", "valid_route_pairs"]"""

SUMMARY_NEW = """    keys = ["baseline_compromised_pct", "trust_aware_compromised_pct",
            "trust_aware_clustering_compromised_pct", "soft_cost_compromised_pct",
            "baseline_avg_hops", "trust_aware_avg_hops",
            "trust_aware_clustering_avg_hops", "soft_cost_avg_hops", "valid_route_pairs"]"""


def patch_routing_file():
    if not ROUTING_FILE.exists():
        raise SystemExit(f"ERROR: {ROUTING_FILE} not found in current directory")
    text = ROUTING_FILE.read_text(encoding="utf-8")
    if "route_with_soft_cost" in text:
        print(f"[skip] {ROUTING_FILE} already has route_with_soft_cost()")
        return
    shutil.copy(ROUTING_FILE, str(ROUTING_FILE) + ".bak_softcost")
    marker = "\ndef route_with_trust(\n"
    if marker not in text:
        raise SystemExit("ERROR: could not find insertion point in trust_aware_routing.py")
    text = text.replace(marker, SOFT_COST_FUNCTION + marker, 1)
    ROUTING_FILE.write_text(text, encoding="utf-8")
    print(f"[ok] added route_with_soft_cost() to {ROUTING_FILE}")


def patch_grid_file():
    if not GRID_FILE.exists():
        raise SystemExit(f"ERROR: {GRID_FILE} not found in current directory")
    text = GRID_FILE.read_text(encoding="utf-8")
    if "soft_cost_compromised_pct" in text:
        print(f"[skip] {GRID_FILE} already wired for soft_cost")
        return
    shutil.copy(GRID_FILE, str(GRID_FILE) + ".bak_softcost")

    replacements = [
        (GRID_IMPORT_OLD, GRID_IMPORT_NEW, "import"),
        (RUN_SIM_OLD, RUN_SIM_NEW, "counters init"),
        (LOOP_OLD, LOOP_NEW, "per-pair loop"),
        (RETURN_OLD, RETURN_NEW, "run_single_simulation return"),
        (SUMMARY_OLD, SUMMARY_NEW, "summarize_runs keys"),
    ]
    for old, new, label in replacements:
        if old not in text:
            raise SystemExit(f"ERROR: could not find '{label}' block in {GRID_FILE} (file may differ from expected)")
        text = text.replace(old, new, 1)

    GRID_FILE.write_text(text, encoding="utf-8")
    print(f"[ok] wired soft_cost mode into {GRID_FILE}")


if __name__ == "__main__":
    patch_routing_file()
    patch_grid_file()
    print("\nDone. Backups saved as *.bak_softcost")
    print("Next: python synthetic_trust_routing_grid_v2.py")