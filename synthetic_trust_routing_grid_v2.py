"""
synthetic_trust_routing_grid.py

Statistical robustness study for Trust-Aware Routing (TA-DT), addressing
reviewer/professor feedback that a single 200-route-pair evaluation on one
real-data snapshot is not sufficient validation for a journal paper.

Reuses the project's existing, unmodified routing logic:
  - build_graph()        from trust_aware_routing.py
  - get_excluded_nodes() from trust_aware_routing.py
  - route_with_trust()   from trust_aware_routing.py

Connection radius is scaled with node count to keep average node degree
roughly constant across network sizes (see radius_for_density), so that
different "num_nodes" settings represent different network sizes at
comparable density, rather than accidentally testing different densities.

Output: outputs/synthetic_trust_routing_grid_results.json
"""

import json
import random
import math
from pathlib import Path
from statistics import mean, stdev

import networkx as nx

from trust_aware_routing import build_graph, get_excluded_nodes, route_with_trust

OUTPUTS_DIR = Path(__file__).resolve().parent / "outputs"
OUTPUTS_DIR.mkdir(exist_ok=True)

NUM_ROUTE_PAIRS = 50    # source/destination pairs sampled per run
TRUST_LOW = 0.15        # trust score assigned to malicious nodes
TRUST_HIGH_MEAN = 0.9   # mean trust score for honest nodes
TRUST_NOISE = 0.05      # noise added to honest-node trust scores
TARGET_AVG_DEGREE = 8   # aim for ~8 neighbors per node regardless of network size


def radius_for_density(num_nodes, target_avg_degree=TARGET_AVG_DEGREE):
    """Scale connection radius so avg node degree stays roughly constant
    across different network sizes (area = 1x1 unit square)."""
    return math.sqrt(target_avg_degree / (math.pi * num_nodes))


def generate_topology(num_nodes: int, seed: int):
    """Generate a synthetic random-geometric-style WSN topology."""
    rng = random.Random(seed)
    node_ids = [str(i) for i in range(num_nodes)]
    positions = {nid: (rng.uniform(0, 1), rng.uniform(0, 1)) for nid in node_ids}
    radius = radius_for_density(num_nodes)

    edges = []
    for i, a in enumerate(node_ids):
        for b in node_ids[i + 1:]:
            ax, ay = positions[a]
            bx, by = positions[b]
            dist = math.hypot(ax - bx, ay - by)
            if dist <= radius:
                edges.append((a, b))

    return node_ids, edges, positions


def pick_malicious_nodes(node_ids, positions, malicious_pct, distribution, seed):
    """Select which nodes are malicious, either uniformly at random or
    clustered spatially near a random 'attack center'."""
    rng = random.Random(seed + 9999)
    num_malicious = max(1, round(len(node_ids) * malicious_pct))

    if distribution == "random":
        return set(rng.sample(node_ids, num_malicious))

    elif distribution == "clustered":
        center = (rng.uniform(0, 1), rng.uniform(0, 1))
        ranked = sorted(
            node_ids,
            key=lambda nid: math.hypot(
                positions[nid][0] - center[0], positions[nid][1] - center[1]
            ),
        )
        return set(ranked[:num_malicious])

    else:
        raise ValueError(f"Unknown distribution type: {distribution}")


def build_classifier_and_trust(node_ids, malicious_set, seed):
    """Simulate imperfect detection: malicious nodes are usually (not always)
    flagged, and trust scores reflect malicious vs honest status with noise."""
    rng = random.Random(seed + 424242)
    classifier = {}
    trust_scores = {}

    DETECTION_RATE = 0.90
    FALSE_POSITIVE_RATE = 0.03

    for nid in node_ids:
        is_malicious = nid in malicious_set
        if is_malicious:
            detected = rng.random() < DETECTION_RATE
            trust = max(0.0, min(1.0, TRUST_LOW + rng.uniform(-0.1, 0.1)))
        else:
            detected = rng.random() < FALSE_POSITIVE_RATE
            trust = max(0.0, min(1.0, TRUST_HIGH_MEAN + rng.uniform(-TRUST_NOISE, TRUST_NOISE)))

        classifier[nid] = {"predicted_attacked": 1 if detected else 0}
        trust_scores[int(nid)] = trust

    return classifier, trust_scores


def sample_route_pairs(node_ids, num_pairs, seed):
    rng = random.Random(seed + 13)
    pairs = []
    attempts = 0
    while len(pairs) < num_pairs and attempts < num_pairs * 20:
        s, d = rng.sample(node_ids, 2)
        pairs.append((s, d))
        attempts += 1
    return pairs


def run_single_simulation(num_nodes, malicious_pct, distribution, seed):
    node_ids, edges, positions = generate_topology(num_nodes, seed)
    G = build_graph(node_ids, edges)

    malicious_set = pick_malicious_nodes(node_ids, positions, malicious_pct, distribution, seed)
    classifier, trust_scores = build_classifier_and_trust(node_ids, malicious_set, seed)
    route_pairs = sample_route_pairs(node_ids, NUM_ROUTE_PAIRS, seed)

    excluded = get_excluded_nodes(node_ids, classifier, trust_scores)

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
    }


def summarize_runs(runs):
    keys = ["baseline_compromised_pct", "trust_aware_compromised_pct",
            "baseline_avg_hops", "trust_aware_avg_hops", "valid_route_pairs"]
    summary = {}
    for k in keys:
        vals = [r[k] for r in runs if r is not None]
        summary[f"{k}_mean"] = round(mean(vals), 3) if vals else None
        summary[f"{k}_std"] = round(stdev(vals), 3) if len(vals) > 1 else 0.0
    summary["num_runs"] = len(runs)
    valid_vals = [r["valid_route_pairs"] for r in runs if r is not None]
    summary["min_valid_route_pairs"] = min(valid_vals) if valid_vals else None
    return summary


def main():
    NODE_COUNTS = [100, 250, 500, 750, 1000]
    MALICIOUS_PCTS = [0.05, 0.10, 0.15, 0.20, 0.25]
    DISTRIBUTIONS = ["random", "clustered"]
    SEEDS_PER_CONFIG = 15
    all_results = []
    total_configs = len(NODE_COUNTS) * len(MALICIOUS_PCTS) * len(DISTRIBUTIONS)
    config_num = 0

    for distribution in DISTRIBUTIONS:
        for num_nodes in NODE_COUNTS:
            for malicious_pct in MALICIOUS_PCTS:
                config_num += 1
                print(f"[{config_num}/{total_configs}] nodes={num_nodes} "
                      f"malicious={malicious_pct:.0%} dist={distribution}")

                runs = []
                for seed_offset in range(SEEDS_PER_CONFIG):
                    seed = 1000 * seed_offset + num_nodes + int(malicious_pct * 100)
                    result = run_single_simulation(num_nodes, malicious_pct, distribution, seed)
                    runs.append(result)

                summary = summarize_runs(runs)
                all_results.append({
                    "num_nodes": num_nodes,
                    "malicious_pct": malicious_pct,
                    "distribution": distribution,
                    **summary,
                })

    output_path = OUTPUTS_DIR / "synthetic_trust_routing_grid_results.json"
    with open(output_path, "w") as f:
        json.dump({
            "description": "Statistical robustness sweep for Trust-Aware Routing "
                            "across network size, malicious node percentage, and "
                            "malicious node distribution, using synthetic topologies "
                            "with density-normalized connectivity and the project's "
                            "unmodified routing/trust logic.",
            "seeds_per_config": SEEDS_PER_CONFIG,
            "node_counts_tested": NODE_COUNTS,
            "malicious_pcts_tested": MALICIOUS_PCTS,
            "distributions_tested": DISTRIBUTIONS,
            "target_avg_degree": TARGET_AVG_DEGREE,
            "results": all_results,
        }, f, indent=2)

    print(f"\nSaved {len(all_results)} configuration summaries to {output_path}")


if __name__ == "__main__":
    main()
