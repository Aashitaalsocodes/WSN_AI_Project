"""
fix_synthetic_grid_clustering.py

Assertion-guarded patch: adds the new clustering-aware routing mode
(route_with_trust_clustering_aware, from trust_aware_routing.py) into the
robustness sweep in synthetic_trust_routing_grid_v2.py, alongside the
existing baseline and trust-aware modes.

Produces a 3-way comparison (baseline / trust-aware / trust-aware+clustering)
at every (num_nodes, malicious_pct, distribution) config, so the paper can
report the clustering-aware improvement specifically under "clustered"
distribution -- directly addressing the 21.42% limitation in Figure 8.

Does NOT change NODE_COUNTS, MALICIOUS_PCTS, DISTRIBUTIONS, SEEDS_PER_CONFIG,
or any existing baseline/trust-aware computation -- purely additive.

Usage:
    python fix_synthetic_grid_clustering.py
    python synthetic_trust_routing_grid_v2.py
"""

from pathlib import Path

TARGET = Path("synthetic_trust_routing_grid_v2.py")
BACKUP = Path("synthetic_trust_routing_grid_v2.py.bak_clustering")

IMPORT_ANCHOR = "from trust_aware_routing import build_graph, get_excluded_nodes, route_with_trust\n"
NEW_IMPORT = (
    "from trust_aware_routing import (\n"
    "    build_graph,\n"
    "    get_excluded_nodes,\n"
    "    route_with_trust,\n"
    "    compute_cluster_density,\n"
    "    route_with_trust_clustering_aware,\n"
    ")\n"
)

LOOP_ANCHOR = '''    excluded = get_excluded_nodes(node_ids, classifier, trust_scores)

    baseline_compromised = 0
    baseline_hops = []
    trust_compromised = 0
    trust_hops = []
    valid_pairs = 0

    for source, destination in route_pairs:
        if not nx.has_path(G, source, destination):
            continue
        valid_pairs += 1

        base_path = nx.shortest_path(G, source=source, target=destination)
        base_attacked = [
            n for n in base_path
            if n in malicious_set and n not in (source, destination)
        ]
        if base_attacked:
            baseline_compromised += 1
        baseline_hops.append(len(base_path) - 1)

        result = route_with_trust(G, source, destination, excluded, classifier)
        if result["path_found"]:
            path_attacked = [
                n for n in result["path"]
                if n in malicious_set and n not in (source, destination)
            ]
            if path_attacked:
                trust_compromised += 1
            trust_hops.append(result["hop_count"])

    if valid_pairs == 0:
        return None

    return {
        "baseline_compromised_pct": round(100 * baseline_compromised / valid_pairs, 2),
        "trust_aware_compromised_pct": round(100 * trust_compromised / valid_pairs, 2),
        "baseline_avg_hops": round(mean(baseline_hops), 3) if baseline_hops else 0,
        "trust_aware_avg_hops": round(mean(trust_hops), 3) if trust_hops else 0,
        "valid_route_pairs": valid_pairs,
        "num_edges": len(edges),
    }'''

NEW_LOOP = '''    excluded = get_excluded_nodes(node_ids, classifier, trust_scores)
    density = compute_cluster_density(G, excluded, radius=2)

    baseline_compromised = 0
    baseline_hops = []
    trust_compromised = 0
    trust_hops = []
    clustering_compromised = 0
    clustering_hops = []
    valid_pairs = 0

    for source, destination in route_pairs:
        if not nx.has_path(G, source, destination):
            continue
        valid_pairs += 1

        base_path = nx.shortest_path(G, source=source, target=destination)
        base_attacked = [
            n for n in base_path
            if n in malicious_set and n not in (source, destination)
        ]
        if base_attacked:
            baseline_compromised += 1
        baseline_hops.append(len(base_path) - 1)

        result = route_with_trust(G, source, destination, excluded, classifier)
        if result["path_found"]:
            path_attacked = [
                n for n in result["path"]
                if n in malicious_set and n not in (source, destination)
            ]
            if path_attacked:
                trust_compromised += 1
            trust_hops.append(result["hop_count"])

        clustering_result = route_with_trust_clustering_aware(
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

    if valid_pairs == 0:
        return None

    return {
        "baseline_compromised_pct": round(100 * baseline_compromised / valid_pairs, 2),
        "trust_aware_compromised_pct": round(100 * trust_compromised / valid_pairs, 2),
        "trust_aware_clustering_compromised_pct": round(100 * clustering_compromised / valid_pairs, 2),
        "baseline_avg_hops": round(mean(baseline_hops), 3) if baseline_hops else 0,
        "trust_aware_avg_hops": round(mean(trust_hops), 3) if trust_hops else 0,
        "trust_aware_clustering_avg_hops": round(mean(clustering_hops), 3) if clustering_hops else 0,
        "valid_route_pairs": valid_pairs,
        "num_edges": len(edges),
    }'''

SUMMARY_KEYS_ANCHOR = '''    keys = ["baseline_compromised_pct", "trust_aware_compromised_pct",
            "baseline_avg_hops", "trust_aware_avg_hops", "valid_route_pairs"]'''
NEW_SUMMARY_KEYS = '''    keys = ["baseline_compromised_pct", "trust_aware_compromised_pct",
            "trust_aware_clustering_compromised_pct",
            "baseline_avg_hops", "trust_aware_avg_hops",
            "trust_aware_clustering_avg_hops", "valid_route_pairs"]'''


def main():
    assert TARGET.exists(), f"{TARGET} not found -- run this from the project root"
    original = TARGET.read_text(encoding="utf-8")

    assert original.count(IMPORT_ANCHOR) == 1, (
        f"Expected exactly one matching import line, found {original.count(IMPORT_ANCHOR)} -- aborting"
    )
    assert original.count(LOOP_ANCHOR) == 1, (
        f"Expected exactly one matching route-pair loop block, found {original.count(LOOP_ANCHOR)} -- aborting"
    )
    assert original.count(SUMMARY_KEYS_ANCHOR) == 1, (
        f"Expected exactly one matching summary keys block, found {original.count(SUMMARY_KEYS_ANCHOR)} -- aborting"
    )
    assert "trust_aware_clustering" not in original, "Already patched -- aborting"

    BACKUP.write_text(original, encoding="utf-8")
    print(f"Backup written to {BACKUP}")

    patched = original.replace(IMPORT_ANCHOR, NEW_IMPORT, 1)
    patched = patched.replace(LOOP_ANCHOR, NEW_LOOP, 1)
    patched = patched.replace(SUMMARY_KEYS_ANCHOR, NEW_SUMMARY_KEYS, 1)

    assert "route_with_trust_clustering_aware" in patched
    assert "compute_cluster_density" in patched
    assert "trust_aware_clustering_compromised_pct" in patched
    assert patched.count("def run_single_simulation") == 1
    assert patched.count("def summarize_runs") == 1

    TARGET.write_text(patched, encoding="utf-8")
    print(f"Patched {TARGET}: added trust_aware_clustering mode to the sweep.")
    print("Existing baseline/trust_aware computation and config grid untouched.")


if __name__ == "__main__":
    main()