"""
apply_biconnectivity_patch.py

Adds a genuine topological-redundancy experiment to the existing sweep:
after generating each synthetic topology, optionally repair it so that
every node has at least 2 node-disjoint paths to the rest of the network
(i.e. no single cut vertex/bridge chokepoint). This is a real, honest
add-on -- it doesn't touch routing logic, trust scores, or the attacker
model. It only asks: "if we also engineer the network to avoid single
points of failure, does that change the clustered-attacker degradation?"

No UAVs, no dynamic thresholds, no assumed results. Just runs the same
750-config sweep on top of biconnected topologies and reports whatever
numbers come out.

Run from inside C:\\Users\\Admin\\WSN_AI_Project:
    python apply_biconnectivity_patch.py
"""

import shutil
from pathlib import Path

GRID_FILE = Path("synthetic_trust_routing_grid_v2.py")

TOPOLOGY_FUNC_OLD = '''def generate_topology(num_nodes: int, seed: int):
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

    return node_ids, edges, positions'''

TOPOLOGY_FUNC_NEW = '''def generate_topology(num_nodes: int, seed: int, enforce_biconnected: bool = False):
    """Generate a synthetic random-geometric-style WSN topology.

    If enforce_biconnected=True, repairs the graph after generation so
    that it has no single cut vertex: every node keeps at least 2
    node-disjoint paths to the rest of the network. This models a
    network operator deliberately engineering redundant links (e.g. two
    radios, mesh backhaul) rather than relying on whatever random
    geometric links happened to form. Repair is done by connecting
    articulation-point-adjacent components with additional nearest-
    neighbor edges (by Euclidean distance) until nx.is_biconnected(G)
    holds, or a repair-attempt cap is hit (very sparse/small graphs may
    not be fully biconnectable without excessive added edges).
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

    if not enforce_biconnected:
        return node_ids, edges, positions

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

    # Phase 1: fully connect the graph first (radius-based geometric
    # graphs can be disconnected outright, not just fragile). Stitch
    # separate components together via their closest node pair.
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

    # Phase 2: once connected, remove single points of failure
    # (articulation points) by adding a redundant link between the
    # components that would otherwise split off.
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

    return node_ids, edges, positions'''

RUN_SIM_SIG_OLD = "def run_single_simulation(num_nodes, malicious_pct, distribution, seed):"
RUN_SIM_SIG_NEW = "def run_single_simulation(num_nodes, malicious_pct, distribution, seed, enforce_biconnected=False):"

TOPOLOGY_CALL_OLD = "    node_ids, edges, positions = generate_topology(num_nodes, seed)"
TOPOLOGY_CALL_NEW = "    node_ids, edges, positions = generate_topology(num_nodes, seed, enforce_biconnected=enforce_biconnected)"

RETURN_ADD_FIELD_OLD = '''        "valid_route_pairs": valid_pairs,
        "num_edges": len(edges),
    }'''

RETURN_ADD_FIELD_NEW = '''        "valid_route_pairs": valid_pairs,
        "num_edges": len(edges),
        "enforce_biconnected": enforce_biconnected,
    }'''

MAIN_LOOP_OLD = '''def main():
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

    print(f"\\nSaved {len(all_results)} configuration summaries to {output_path}")'''

MAIN_LOOP_NEW = '''def run_sweep(enforce_biconnected, output_filename):
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
                tag = "biconnected" if enforce_biconnected else "standard"
                print(f"[{tag} {config_num}/{total_configs}] nodes={num_nodes} "
                      f"malicious={malicious_pct:.0%} dist={distribution}")

                runs = []
                for seed_offset in range(SEEDS_PER_CONFIG):
                    seed = 1000 * seed_offset + num_nodes + int(malicious_pct * 100)
                    result = run_single_simulation(
                        num_nodes, malicious_pct, distribution, seed,
                        enforce_biconnected=enforce_biconnected,
                    )
                    runs.append(result)

                summary = summarize_runs(runs)
                all_results.append({
                    "num_nodes": num_nodes,
                    "malicious_pct": malicious_pct,
                    "distribution": distribution,
                    **summary,
                })

    output_path = OUTPUTS_DIR / output_filename
    with open(output_path, "w") as f:
        json.dump({
            "description": "Statistical robustness sweep for Trust-Aware Routing "
                            "across network size, malicious node percentage, and "
                            "malicious node distribution, using synthetic topologies "
                            "with density-normalized connectivity and the project's "
                            "unmodified routing/trust logic."
                            + (" Topology repaired to be biconnected (no single cut "
                               "vertex) before routing/attacks are applied."
                               if enforce_biconnected else ""),
            "enforce_biconnected": enforce_biconnected,
            "seeds_per_config": SEEDS_PER_CONFIG,
            "node_counts_tested": NODE_COUNTS,
            "malicious_pcts_tested": MALICIOUS_PCTS,
            "distributions_tested": DISTRIBUTIONS,
            "target_avg_degree": TARGET_AVG_DEGREE,
            "results": all_results,
        }, f, indent=2)

    print(f"\\nSaved {len(all_results)} configuration summaries to {output_path}")
    return all_results


def main():
    import sys
    # Default: run the standard (non-biconnected) sweep, same as before.
    # Pass --biconnected to run the biconnected-topology variant instead.
    # Pass --both to run both and save two separate output files.
    if "--both" in sys.argv:
        run_sweep(False, "synthetic_trust_routing_grid_results.json")
        run_sweep(True, "synthetic_trust_routing_grid_results_biconnected.json")
    elif "--biconnected" in sys.argv:
        run_sweep(True, "synthetic_trust_routing_grid_results_biconnected.json")
    else:
        run_sweep(False, "synthetic_trust_routing_grid_results.json")'''


def patch():
    if not GRID_FILE.exists():
        raise SystemExit(f"ERROR: {GRID_FILE} not found in current directory")
    text = GRID_FILE.read_text(encoding="utf-8")

    if "enforce_biconnected" in text:
        print(f"[skip] {GRID_FILE} already has biconnectivity support")
        return

    shutil.copy(GRID_FILE, str(GRID_FILE) + ".bak_biconnect")

    checks = [
        (TOPOLOGY_FUNC_OLD, TOPOLOGY_FUNC_NEW, "generate_topology()"),
        (RUN_SIM_SIG_OLD, RUN_SIM_SIG_NEW, "run_single_simulation signature"),
        (TOPOLOGY_CALL_OLD, TOPOLOGY_CALL_NEW, "generate_topology call"),
        (RETURN_ADD_FIELD_OLD, RETURN_ADD_FIELD_NEW, "run_single_simulation return dict"),
        (MAIN_LOOP_OLD, MAIN_LOOP_NEW, "main() sweep loop"),
    ]
    for old, new, label in checks:
        if old not in text:
            raise SystemExit(f"ERROR: could not find '{label}' block -- file may differ from expected")
        text = text.replace(old, new, 1)

    GRID_FILE.write_text(text, encoding="utf-8")
    print(f"[ok] added biconnectivity option to {GRID_FILE}")


if __name__ == "__main__":
    patch()
    print("\nDone. Backup saved as *.bak_biconnect")
    print("\nUsage:")
    print("  python synthetic_trust_routing_grid_v2.py                # standard sweep (unchanged, as before)")
    print("  python synthetic_trust_routing_grid_v2.py --biconnected  # biconnected-topology sweep")
    print("  python synthetic_trust_routing_grid_v2.py --both         # run both, save two files")