"""
trust_aware_routing.py

Implements trust-aware adaptive routing on top of Person B's baseline
routing simulation. Re-runs the same 200 source→destination pairs but
excludes nodes where predicted_attacked=1 OR trust_score < threshold,
then compares against the baseline to measure improvement.

Inputs:
  outputs/routing_simulation.json              -> topology + baseline routes
  outputs/attack_classifier_predictions.json   -> predicted_attacked per node
  outputs/final_pipeline_result.json           -> trust scores per node (from TrustEngine)

Output:
  outputs/trust_aware_routing_results.json
"""

import json
import argparse
_parser = argparse.ArgumentParser()
_parser.add_argument("--seed", type=int, default=42)
_args, _ = _parser.parse_known_args()
SEED = _args.seed

from pathlib import Path

import networkx as nx

OUTPUTS_DIR = Path(__file__).resolve().parent / "outputs"
TRUST_THRESHOLD = 0.4   # matches config.py TRUST_THRESHOLD
ATTACK_PROB_THRESHOLD = 0.5  # supervised classifier: >50% = predicted attacked


def load_inputs():
    with open(OUTPUTS_DIR / f"routing_simulation_seed{SEED}.json", encoding="utf-8") as f:
        sim = json.load(f)
    with open(OUTPUTS_DIR / "attack_classifier_predictions.json", encoding="utf-8") as f:
        classifier = json.load(f)
    with open(OUTPUTS_DIR / "final_pipeline_result.json", encoding="utf-8") as f:
        pipeline = json.load(f)
    return sim, classifier, pipeline


def build_graph(node_ids: list, edges: list) -> nx.Graph:
    G = nx.Graph()
    G.add_nodes_from(node_ids)
    G.add_edges_from([tuple(e) for e in edges])
    return G


def get_excluded_nodes(
    node_ids: list,
    classifier: dict,
    trust_scores: dict,
) -> set:
    """
    Returns set of node IDs to exclude from trust-aware routing:
    - predicted_attacked = 1 by supervised classifier, OR
    - trust_score < TRUST_THRESHOLD from TrustEngine
    """
    excluded = set()
    for nid in node_ids:
        # Check classifier prediction
        pred = classifier.get(nid, {})
        if pred.get("predicted_attacked", 0) == 1:
            excluded.add(nid)
            continue
        # Check trust score (stored as int key in pipeline result)
        ts = trust_scores.get(int(nid), 1.0)
        if ts < TRUST_THRESHOLD:
            excluded.add(nid)
    return excluded


def compute_cluster_density(G, excluded: set, radius: int = 2) -> dict:
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

def route_with_trust(
    G: nx.Graph,
    source: str,
    destination: str,
    excluded: set,
    classifier: dict,
) -> dict:
    """
    Attempt to route from source to destination avoiding excluded nodes.
    Falls back to baseline routing if no trust-aware path exists.
    """
    # Remove excluded nodes (keep source/dest even if excluded — can't avoid endpoints)
    nodes_to_remove = excluded - {source, destination}
    G_trusted = G.copy()
    G_trusted.remove_nodes_from(nodes_to_remove)

    try:
        path = nx.shortest_path(G_trusted, source=source, target=destination)
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
            "routing_mode": "trust_aware",
            "path_found": True,
        }
    except nx.NetworkXNoPath:
        # No path exists avoiding excluded nodes — fall back to baseline
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


def main():
    sim, classifier, pipeline = load_inputs()

    # Build full graph
    G = build_graph(sim["node_ids"], sim["edges"])

    # Extract trust scores from pipeline result network_state
    # trust_scores stored as {node_id(int): trust_score} in pipeline
    # Re-run TrustEngine to get per-node trust scores properly
    from trust_engine import TrustEngine
    import pandas as pd

    node_ids = sim["node_ids"]

    # Build minimal trust DataFrame for the 500 simulation nodes
    df = pd.DataFrame({
        "node_id": [int(nid) for nid in node_ids],
        "historical_accuracy": 0.8,
        "protocol_compliance": 0.8,
        "neighbor_recommendation": 0.5,
        "anomaly_score": [
            float(classifier.get(nid, {}).get("attack_probability", 0.2))
            for nid in node_ids
        ],
    })
    df = TrustEngine().update_trust(df)
    trust_scores = {int(row.node_id): float(row.trust_score) for row in df.itertuples(index=False)}

    # Determine excluded nodes
    excluded = get_excluded_nodes(node_ids, classifier, trust_scores)
    print(f"Total simulation nodes:   {len(node_ids)}")
    print(f"Excluded (attacked/low-trust): {len(excluded)} ({100*len(excluded)/len(node_ids):.1f}%)")

    # Re-run all 200 baseline routes with trust-aware routing
    trust_aware_routes = []
    for route in sim["baseline_routes"]:
        src = route["source"]
        dst = route["destination"]
        result = route_with_trust(G, src, dst, excluded, classifier)
        trust_aware_routes.append({
            "route_id": route["route_id"],
            "source": src,
            "destination": dst,
            **result,
        })

    # Summary statistics
    total = len(trust_aware_routes)
    found = sum(1 for r in trust_aware_routes if r["path_found"])
    compromised = sum(1 for r in trust_aware_routes if r["passes_through_attacked_node"])
    fallback = sum(1 for r in trust_aware_routes if r["routing_mode"] == "fallback_no_trusted_path")
    trust_aware_only = sum(1 for r in trust_aware_routes if r["routing_mode"] == "trust_aware")
    avg_hops = sum(r["hop_count"] for r in trust_aware_routes if r["hop_count"] >= 0) / max(found, 1)

    baseline_compromised = sim["baseline_summary"]["pct_compromised_routes"]
    trust_aware_compromised = round(100.0 * compromised / total, 1)
    improvement = round(baseline_compromised - trust_aware_compromised, 1)

    trust_aware_summary = {
        "total_routes": total,
        "routes_found": found,
        "avg_hop_count": round(avg_hops, 2),
        "routes_through_attacked_node": compromised,
        "pct_compromised_routes": trust_aware_compromised,
        "routes_fully_trust_aware": trust_aware_only,
        "routes_forced_fallback": fallback,
        "routes_no_path": total - found,
    }

    comparison = {
        "baseline_pct_compromised": baseline_compromised,
        "trust_aware_pct_compromised": trust_aware_compromised,
        "improvement_percentage_points": improvement,
        "baseline_avg_hops": sim["baseline_summary"]["avg_hop_count"],
        "trust_aware_avg_hops": round(avg_hops, 2),
        "hop_count_tradeoff": round(avg_hops - sim["baseline_summary"]["avg_hop_count"], 2),
        "excluded_nodes": len(excluded),
        "excluded_pct": round(100 * len(excluded) / len(node_ids), 1),
    }

    results = {
        "trust_threshold_used": TRUST_THRESHOLD,
        "attack_prob_threshold_used": ATTACK_PROB_THRESHOLD,
        "excluded_nodes": list(excluded),
        "trust_aware_routes": trust_aware_routes,
        "trust_aware_summary": trust_aware_summary,
        "comparison_vs_baseline": comparison,
    }

    output_path = OUTPUTS_DIR / f"trust_aware_routing_results_seed{SEED}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("\n=== Trust-Aware Routing Results ===")
    print(f"Baseline compromised routes:     {baseline_compromised}%")
    print(f"Trust-aware compromised routes:  {trust_aware_compromised}%")
    print(f"Improvement:                     -{improvement} percentage points")
    print(f"Baseline avg hops:               {sim['baseline_summary']['avg_hop_count']}")
    print(f"Trust-aware avg hops:            {round(avg_hops, 2)}")
    print(f"Hop count tradeoff:              +{comparison['hop_count_tradeoff']}")
    print(f"Routes forced to fallback:       {fallback}")
    print(f"Routes with no path at all:      {total - found}")
    print(f"\nResults written to {output_path}")


if __name__ == "__main__":
    main()