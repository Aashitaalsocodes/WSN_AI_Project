"""
Ablation: build_edges_v2.py
============================
Drop-in replacement for Step 4 of gnn_graph_builder.py's build_graph().

WHY: The original edge construction sorts all nodes by a single scalar
(distance_to_ch_norm) and connects each node to its +/-K window neighbors
in that sorted order. This produces something closer to a path/chain graph
than a true similarity graph -- and empirically causes a small number of
"anchor" nodes to become shared neighbors across huge numbers of unrelated
high-risk nodes (visible in the GAT attention exports, where the same 3
neighbor IDs kept reappearing across many different central nodes).

FIX: Build edges from true multi-dimensional K-nearest-neighbors, using
sklearn's NearestNeighbors over a feature vector. Deliberately EXCLUDE
attack_probability_mean/max and composite_risk_score_mean from the distance
metric used for edge construction -- those features are near-proxies for
the label itself, so using them to build edges would make the resulting
graph circularly "easy" (attacked nodes trivially neighboring attacked
nodes) rather than testing whether attention can find real structure.

Only behavioral/structural features are used for the edge metric:
  - distance_to_ch_norm
  - packet_delivery_ratio_mean
  - is_cluster_head

Usage: import build_edges_v2 and call it in place of the original Step 4
block in gnn_graph_builder.py, passing the same `nodes` dict.
"""

import numpy as np
from sklearn.neighbors import NearestNeighbors


def build_edges_v2(nodes, k=5):
    """
    nodes: dict of node_id -> feature dict (same structure as gnn_graph_builder.py)
    k: number of nearest neighbors per node

    Returns: list of [node_id_a, node_id_b] edges (deduplicated, undirected)
    """
    node_ids = list(nodes.keys())

    # Build feature matrix using ONLY structural/behavioral features --
    # deliberately excluding label-correlated features (see module docstring).
    feature_matrix = np.array([
        [
            nodes[nid]["distance_to_ch_norm"],
            nodes[nid]["packet_delivery_ratio_mean"],
            float(nodes[nid]["is_cluster_head"]),
        ]
        for nid in node_ids
    ])

    # Standardize so no single feature dominates the distance metric purely
    # due to scale (packet_delivery_ratio_mean and distance_to_ch_norm may
    # have very different ranges).
    means = feature_matrix.mean(axis=0)
    stds = feature_matrix.std(axis=0)
    stds[stds == 0] = 1.0  # avoid divide-by-zero for constant columns
    feature_matrix_scaled = (feature_matrix - means) / stds

    print(f"Building multi-dimensional KNN graph (k={k}) over "
          f"{len(node_ids):,} nodes using 3 structural features...")

    nbrs = NearestNeighbors(n_neighbors=k + 1, algorithm="auto")  # +1: includes self
    nbrs.fit(feature_matrix_scaled)
    distances, indices = nbrs.kneighbors(feature_matrix_scaled)

    edges = []
    for i, neighbor_idx_row in enumerate(indices):
        node_id = node_ids[i]
        for j in neighbor_idx_row:
            if j == i:
                continue  # skip self
            neighbor_id = node_ids[j]
            edges.append([node_id, neighbor_id])

    # Deduplicate (undirected)
    edge_set = set()
    unique_edges = []
    for e in edges:
        key = tuple(sorted(e))
        if key not in edge_set:
            edge_set.add(key)
            unique_edges.append(e)

    print(f"Built {len(unique_edges):,} unique edges (k={k} multi-dimensional KNN)")

    # Diagnostic: check for the "anchor node" problem from the old graph --
    # count how many times each node appears as a neighbor across all edges.
    # A healthy graph should have this fairly evenly distributed; a few
    # nodes appearing thousands of times would indicate the same structural
    # issue as before.
    from collections import Counter
    appearance_counts = Counter()
    for a, b in unique_edges:
        appearance_counts[a] += 1
        appearance_counts[b] += 1

    counts = list(appearance_counts.values())
    print(f"Neighbor-appearance distribution: mean={np.mean(counts):.1f}, "
          f"std={np.std(counts):.1f}, max={np.max(counts)}")
    print("(For comparison: the old distance-sort graph likely had a much "
          "higher max relative to mean -- a few 'anchor' nodes dominating.)")

    return unique_edges


if __name__ == "__main__":
    import json
    from pathlib import Path

    OUTPUTS = Path(__file__).parent / "outputs"

    # Load the existing nodes dict (already built by the original script's
    # Steps 1-3) rather than re-deriving it from scratch.
    with open(OUTPUTS / "gnn_graph_data.json") as f:
        existing = json.load(f)

    nodes = existing["nodes"]
    new_edges = build_edges_v2(nodes, k=5)

    # Write as a SEPARATE file so the original graph isn't overwritten --
    # you want both graphs available for the ablation comparison.
    graph_data_v2 = dict(existing)  # copy nodes, feature_names, etc.
    graph_data_v2["edges"] = new_edges
    graph_data_v2["num_edges"] = len(new_edges)
    graph_data_v2["edge_strategy"] = (
        "K=5 multi-dimensional KNN over [distance_to_ch_norm, "
        "packet_delivery_ratio_mean, is_cluster_head] (standardized), "
        "ablation vs. original single-feature sort-window graph"
    )

    out_path = OUTPUTS / "gnn_graph_data_v2.json"
    with open(out_path, "w") as f:
        json.dump(graph_data_v2, f)

    print(f"\nWrote ablation graph to {out_path}")
    print("Next: re-run gnn_model.py pointing GRAPH_PATH at this file, "
          "using a different output filename (e.g. gnn_attention_weights_v2.json), "
          "then compare attention entropy between the two.")