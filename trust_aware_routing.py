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
from pathlib import Path

import networkx as nx

OUTPUTS_DIR = Path(__file__).resolve().parent / "outputs"
TRUST_THRESHOLD = 0.4   # matches config.py TRUST_THRESHOLD
ATTACK_PROB_THRESHOLD = 0.5  # supervised classifier: >50% = predicted attacked


def load_inputs():
    with open(OUTPUTS_DIR / "routing_simulation.json", encoding="utf-8") as f:
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

    output_path = OUTPUTS_DIR / "trust_aware_routing_results.json"
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