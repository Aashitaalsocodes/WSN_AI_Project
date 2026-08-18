"""
synthetic_trust_routing_grid_v3.py

EXPERIMENT 3 (separate from v2's standard/biconnected sweeps).

Tests: does adding extra "bridge" nodes at low-density regions of the
topology (placed BEFORE malicious nodes are chosen, with zero knowledge
of where attackers will end up) reduce the clustered-attacker compromise
rate seen in the v2 results?

This is a standalone copy of synthetic_trust_routing_grid_v2.py.
v2.py and its output files (synthetic_trust_routing_grid_results.json,
synthetic_trust_routing_grid_results_biconnected.json) are NOT touched
by this script. All new results go to a new file:
    outputs/synthetic_trust_routing_grid_results_v3.json

WHY IT'S ATTACKER-BLIND (important for the paper's honesty):
place_bridge_nodes() runs inside generate_topology(), which completes
and returns before pick_malicious_nodes() is ever called anywhere in
the pipeline. The placement function has no parameter, closure, or
global that could leak attacker locations -- structurally, not just by
convention. New nodes are added at low local-density grid cells only,
using node positions alone.

New bridge nodes are FULL participants: same starting trust score
(TRUST_HIGH_MEAN, i.e. treated as any other honest-until-scored node),
eligible to be selected as malicious by pick_malicious_nodes() like any
other node (not excluded from that pool), eligible for routing. Nothing
about them is special-cased downstream of generate_topology().
"""

import json
import random
import math
from pathlib import Path
from statistics import mean, stdev

import networkx as nx

from trust_aware_routing import (
    build_graph,
    get_excluded_nodes,
    route_with_trust,
    compute_cluster_density,
    route_with_trust_clustering_aware,
    route_with_soft_cost,
)

OUTPUTS_DIR = Path(__file__).resolve().parent / "outputs"
OUTPUTS_DIR.mkdir(exist_ok=True)

NUM_ROUTE_PAIRS = 50
TRUST_LOW = 0.15
TRUST_HIGH_MEAN = 0.9
TRUST_NOISE = 0.05
TARGET_AVG_DEGREE = 8

# --- NEW: bridge-node placement config ---
BRIDGE_GRID_CELLS_PER_SIDE = 6   # divide unit square into a 6x6 grid to find low-density cells


def radius_for_density(num_nodes, target_avg_degree=TARGET_AVG_DEGREE):
    return math.sqrt(target_avg_degree / (math.pi * num_nodes))


# ============================================================
# NEW FUNCTION: place_bridge_nodes()
#
# Attacker-blind by construction: only inputs are node_ids and
# positions of the topology as already generated. Called from inside
# generate_topology(), strictly before pick_malicious_nodes() exists
# anywhere in the call chain.
# ============================================================
def place_bridge_nodes(node_ids, positions, radius, rng, add_pct):
    """Add extra nodes in the lowest-density grid cells of the field.

    Density is measured purely from existing node positions (a defender
    doing strategic redundant deployment based on known coverage gaps,
    not attacker knowledge). Returns the extended node list, the new
    edges connecting bridge nodes into the graph (within `radius` of
    existing nodes), and the extended positions dict.
    """
    num_new = max(1, round(len(node_ids) * add_pct))

    # Bin existing nodes into a grid to find sparse cells.
    cells = {}
    cell_size = 1.0 / BRIDGE_GRID_CELLS_PER_SIDE
    for nid in node_ids:
        x, y = positions[nid]
        cx, cy = int(x / cell_size), int(y / cell_size)
        cells.setdefault((cx, cy), []).append(nid)

    all_cells = [
        (cx, cy)
        for cx in range(BRIDGE_GRID_CELLS_PER_SIDE)
        for cy in range(BRIDGE_GRID_CELLS_PER_SIDE)
    ]
    # Sort cells by node count ascending (sparsest first); empty cells
    # (count=0) naturally sort first.
    all_cells.sort(key=lambda c: len(cells.get(c, [])))

    new_ids = []
    new_positions = {}
    new_edges = []
    next_id_num = max(int(nid) for nid in node_ids) + 1

    for i in range(num_new):
        cx, cy = all_cells[i % len(all_cells)]
        # Place near the centroid of that cell, with small jitter so
        # repeated picks of the same sparse cell don't stack exactly.
        base_x = (cx + 0.5) * cell_size
        base_y = (cy + 0.5) * cell_size
        jitter = cell_size * 0.15
        x = min(1.0, max(0.0, base_x + rng.uniform(-jitter, jitter)))
        y = min(1.0, max(0.0, base_y + rng.uniform(-jitter, jitter)))

        new_id = str(next_id_num)
        next_id_num += 1
        new_ids.append(new_id)
        new_positions[new_id] = (x, y)

    # Connect new nodes into the graph using the same radius rule as
    # the rest of the topology, against BOTH existing and other new nodes.
    all_positions_so_far = dict(positions)
    all_positions_so_far.update(new_positions)
    all_ids_so_far = node_ids + new_ids

    for new_id in new_ids:
        nx_, ny_ = new_positions[new_id]
        for other_id in all_ids_so_far:
            if other_id == new_id:
                continue
            ox, oy = all_positions_so_far[other_id]
            dist = math.hypot(nx_ - ox, ny_ - oy)
            if dist <= radius:
                edge = tuple(sorted((new_id, other_id), key=int))
                if edge not in new_edges:
                    new_edges.append(edge)

    return new_ids, new_edges, new_positions


def generate_topology(num_nodes: int, seed: int, enforce_biconnected: bool = False,
                       add_bridge_pct: float = 0.0):
    """Same as v2, plus optional bridge-node addition (NEW: add_bridge_pct).

    add_bridge_pct=0.0 (default) reproduces v2 behavior exactly.
    add_bridge_pct=0.10 adds +10% extra nodes at low-density cells
    BEFORE returning -- i.e. before any malicious-node logic runs.
    """
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

    # --- NEW: bridge-node insertion hook ---
    # Runs before enforce_biconnected repair and, critically, before
    # pick_malicious_nodes() is called anywhere (that happens later, in
    # run_single_simulation, using the node_ids this function returns).
    if add_bridge_pct > 0.0:
        new_ids, new_edges, new_positions = place_bridge_nodes(
            node_ids, positions, radius, rng, add_bridge_pct
        )
        node_ids = node_ids + new_ids
        positions.update(new_positions)
        edges = edges + new_edges

    if not enforce_biconnected:
        return node_ids, edges, positions

    # (unchanged biconnectivity repair logic from v2, operates on the
    # already-extended node/edge set if bridges were added)
    G = nx.Graph()
    G.add_nodes_from(node_ids)
    G.add_edges_from(edges)

    def closest_pair(set_a, set_b):
        best = None
        best_dist = float("inf")
        for na in set_a:
            for nb in set_b:
                ax, ay = positions[na]
                bx, by = positions[nb]
                d = math.hypot(ax - bx, ay - by)
                if d < best_dist:
                    best_dist = d
                    best = (na, nb)
        return best

    max_repair_attempts = num_nodes * 6
    attempts = 0

    while attempts < max_repair_attempts and not nx.is_connected(G):
        components = list(nx.connected_components(G))
        if len(components) < 2:
            break
        comp_a, comp_b = components[0], components[1]
        pair = closest_pair(comp_a, comp_b)
        if pair is None:
            break
        u, v = pair
        if not G.has_edge(u, v):
            G.add_edge(u, v)
            edges.append((u, v))
        attempts += 1

    while attempts < max_repair_attempts:
        if G.number_of_nodes() < 3:
            break
        try:
            if nx.is_biconnected(G):
                break
        except nx.NetworkXPointlessConcept:
            break

        cut_vertices = list(nx.articulation_points(G))
        if not cut_vertices:
            break

        articulation = cut_vertices[0]
        G_minus = G.copy()
        G_minus.remove_node(articulation)
        components = list(nx.connected_components(G_minus))
        if len(components) < 2:
            attempts += 1
            continue

        comp_a, comp_b = components[0], components[1]
        pair = closest_pair(comp_a, comp_b)
        if pair is None:
            attempts += 1
            continue
        u, v = pair
        if not G.has_edge(u, v):
            G.add_edge(u, v)
            edges.append((u, v))
        attempts += 1

    return node_ids, edges, positions


def pick_malicious_nodes(node_ids, positions, malicious_pct, distribution, seed):
    """UNCHANGED from v2. Operates on whatever node_ids it's given --
    including bridge nodes, if any were added -- with no special-casing.
    This is what makes bridge-node eligibility for malicious selection
    automatic rather than something we have to remember to wire in."""
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
    """UNCHANGED from v2. Bridge nodes get the same TRUST_HIGH_MEAN
    starting trust as any honest node -- no special value."""
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


def run_single_simulation(num_nodes, malicious_pct, distribution, seed,
                           enforce_biconnected=False, add_bridge_pct=0.0):
    node_ids, edges, positions = generate_topology(
        num_nodes, seed, enforce_biconnected=enforce_biconnected,
        add_bridge_pct=add_bridge_pct,
    )
    G = build_graph(node_ids, edges)

    malicious_set = pick_malicious_nodes(node_ids, positions, malicious_pct, distribution, seed)
    classifier, trust_scores = build_classifier_and_trust(node_ids, malicious_set, seed)
    route_pairs = sample_route_pairs(node_ids, NUM_ROUTE_PAIRS, seed)

    excluded = get_excluded_nodes(node_ids, classifier, trust_scores)
    density = compute_cluster_density(G, excluded, radius=2)

    baseline_compromised = 0
    baseline_hops = []
    trust_compromised = 0
    trust_hops = []
    clustering_compromised = 0
    clustering_hops = []
    soft_cost_compromised = 0
    soft_cost_hops = []
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
            soft_cost_hops.append(soft_cost_result["hop_count"])

    if valid_pairs == 0:
        return None

    return {
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
        "num_nodes_actual": len(node_ids),   # NEW: reflects base+bridge count
        "enforce_biconnected": enforce_biconnected,
        "add_bridge_pct": add_bridge_pct,     # NEW
    }


def summarize_runs(runs):
    keys = ["baseline_compromised_pct", "trust_aware_compromised_pct",
            "trust_aware_clustering_compromised_pct", "soft_cost_compromised_pct",
            "baseline_avg_hops", "trust_aware_avg_hops",
            "trust_aware_clustering_avg_hops", "soft_cost_avg_hops", "valid_route_pairs"]
    summary = {}
    for k in keys:
        vals = [r[k] for r in runs if r is not None]
        summary[f"{k}_mean"] = round(mean(vals), 3) if vals else None
        summary[f"{k}_std"] = round(stdev(vals), 3) if len(vals) > 1 else 0.0
    summary["num_runs"] = len(runs)
    valid_vals = [r["valid_route_pairs"] for r in runs if r is not None]
    summary["min_valid_route_pairs"] = min(valid_vals) if valid_vals else None
    return summary


def run_sweep(add_bridge_pct, output_filename, node_counts=None, malicious_pcts=None):
    """NEW signature vs v2: takes add_bridge_pct instead of
    enforce_biconnected (this experiment doesn't touch biconnectivity),
    and lets the pilot call in main() restrict node_counts/malicious_pcts
    to a cheap subset before committing to the full grid."""
    NODE_COUNTS = node_counts or [100, 250, 500, 750, 1000]
    MALICIOUS_PCTS = malicious_pcts or [0.05, 0.10, 0.15, 0.20, 0.25]
    DISTRIBUTIONS = ["random", "clustered"]
    SEEDS_PER_CONFIG = 15
    all_results = []
    per_seed_rows = []  # NEW: raw per-seed results for auditability
    total_configs = len(NODE_COUNTS) * len(MALICIOUS_PCTS) * len(DISTRIBUTIONS)
    config_num = 0

    for distribution in DISTRIBUTIONS:
        for num_nodes in NODE_COUNTS:
            for malicious_pct in MALICIOUS_PCTS:
                config_num += 1
                print(f"[bridge+{add_bridge_pct:.0%} {config_num}/{total_configs}] "
                      f"nodes={num_nodes} malicious={malicious_pct:.0%} dist={distribution}")

                runs = []
                for seed_offset in range(SEEDS_PER_CONFIG):
                    seed = 1000 * seed_offset + num_nodes + int(malicious_pct * 100)
                    result = run_single_simulation(
                        num_nodes, malicious_pct, distribution, seed,
                        enforce_biconnected=False,
                        add_bridge_pct=add_bridge_pct,
                    )
                    runs.append(result)
                    # NEW: retain per-seed rows for CSV logging (does not
                    # affect existing summary/JSON behavior below).
                    per_seed_rows.append({
                        "seed_offset": seed_offset,
                        "seed": seed,
                        "num_nodes_base": num_nodes,
                        "malicious_pct": malicious_pct,
                        "distribution": distribution,
                        "result": result,
                    })

                summary = summarize_runs(runs)
                all_results.append({
                    "num_nodes_base": num_nodes,
                    "malicious_pct": malicious_pct,
                    "distribution": distribution,
                    **summary,
                })

    # NEW: write per-seed CSV alongside the existing JSON summary.
    # Uses the metric that matters for the random-vs-clustered gap
    # analysis: trust_aware_clustering_compromised_pct (also includes
    # the other three compromised_pct metrics for completeness).
    csv_path = OUTPUTS_DIR / (Path(output_filename).stem + "_per_seed.csv")
    with open(csv_path, "w", newline="") as f:
        import csv as _csv
        writer = _csv.writer(f)
        writer.writerow([
            "seed_offset", "seed", "num_nodes_base", "malicious_pct", "distribution",
            "baseline_compromised_pct", "trust_aware_compromised_pct",
            "trust_aware_clustering_compromised_pct", "soft_cost_compromised_pct",
            "valid_route_pairs",
        ])
        for row in per_seed_rows:
            r = row["result"]
            assert r is not None, (
                f"seed_offset={row['seed_offset']} produced no valid route pairs "
                f"(run_single_simulation returned None) -- cannot log this row. "
                f"Investigate before trusting aggregate stats for this config."
            )
            writer.writerow([
                row["seed_offset"], row["seed"], row["num_nodes_base"],
                row["malicious_pct"], row["distribution"],
                r["baseline_compromised_pct"], r["trust_aware_compromised_pct"],
                r["trust_aware_clustering_compromised_pct"], r["soft_cost_compromised_pct"],
                r["valid_route_pairs"],
            ])
    print(f"Saved {len(per_seed_rows)} per-seed rows to {csv_path}")

    output_path = OUTPUTS_DIR / output_filename
    with open(output_path, "w") as f:
        json.dump({
            "description": "EXPERIMENT 3: attacker-blind bridge-node deployment. "
                            f"+{add_bridge_pct:.0%} extra nodes placed at the lowest-"
                            "density grid cells of the topology BEFORE malicious "
                            "nodes are chosen (zero knowledge of attacker locations). "
                            "Bridge nodes are full participants: normal starting "
                            "trust, eligible to be selected as malicious, eligible "
                            "for routing/CH election. Compare against the standard-"
                            "topology results in synthetic_trust_routing_grid_results.json "
                            "(v2) for the same num_nodes_base/malicious_pct/distribution.",
            "add_bridge_pct": add_bridge_pct,
            "seeds_per_config": SEEDS_PER_CONFIG,
            "node_counts_tested": NODE_COUNTS,
            "malicious_pcts_tested": MALICIOUS_PCTS,
            "distributions_tested": DISTRIBUTIONS,
            "target_avg_degree": TARGET_AVG_DEGREE,
            "results": all_results,
        }, f, indent=2)

    print(f"\nSaved {len(all_results)} configuration summaries to {output_path}")
    return all_results


def main():
    import sys
    if "--pilot" in sys.argv:
        # Cheap sanity check: just 500 base nodes, 25% malicious,
        # both distributions, 15 seeds each -- minutes, not the full grid.
        run_sweep(
            add_bridge_pct=0.10,
            output_filename="synthetic_trust_routing_grid_results_v3_pilot.json",
            node_counts=[500],
            malicious_pcts=[0.25],
        )
    else:
        run_sweep(
            add_bridge_pct=0.10,
            output_filename="synthetic_trust_routing_grid_results_v3.json",
        )


if __name__ == "__main__":
    main()