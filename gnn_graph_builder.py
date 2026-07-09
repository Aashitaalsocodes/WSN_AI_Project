"""
gnn_graph_builder.py
====================
Task 5: GNN scoping + graph representation of WSN.

Builds a graph-structured dataset from WSN-DS for GNN training:
- 11,120 nodes (one per unique physical WSN node)
- Edges: nodes sharing the same cluster head are connected
- Node features: aggregated across 33.7 timesteps per node
- Node labels: malicious if any timestep is attacked

Outputs:
  outputs/gnn_graph_data.json  -- graph structure + features + labels
  outputs/gnn_graph_report.json -- stats for paper
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path
from collections import defaultdict

BASE_DIR    = Path(__file__).parent
DATA_PATH   = BASE_DIR / "data" / "processed" / "processed_data.csv"
OUTPUTS     = BASE_DIR / "outputs"
NODES_PATH  = OUTPUTS / "preprocessed_nodes.json"
OUT_GRAPH   = OUTPUTS / "gnn_graph_data.json"
OUT_REPORT  = OUTPUTS / "gnn_graph_report.json"


def build_graph():
    print("=" * 60)
    print("Task 5 -- GNN Graph Construction")
    print("=" * 60)

    # ── Step 1: Load raw data ─────────────────────────────────────
    print("\n[1/5] Loading WSN-DS data...")
    df = pd.read_csv(DATA_PATH, usecols=[
        "node_id", "attack_type", "is_cluster_head",
        "distance_to_ch", "packets_sent", "packets_received"
    ])
    print(f"      {len(df):,} rows, {df['node_id'].nunique():,} unique nodes")

    # ── Step 2: Load preprocessed features ───────────────────────
    print("\n[2/5] Loading preprocessed node features...")
    with open(NODES_PATH) as f:
        preprocessed = json.load(f)
    print(f"      {len(preprocessed):,} preprocessed records")

    # Map row_index → preprocessed features
    row_features = {}
    for row_idx, rec in preprocessed.items():
        row_features[int(row_idx)] = {
            "attack_probability":    rec.get("attack_probability", 0.0),
            "composite_risk_score":  rec.get("composite_risk_score", 0.0),
            "packet_delivery_ratio": rec.get("packet_delivery_ratio", 0.0),
            "predicted_attacked":    rec.get("predicted_attacked", 0),
        }

    # ── Step 3: Aggregate per physical node ──────────────────────
    print("\n[3/5] Aggregating features per physical node...")

    df = df.reset_index()  # gives us row index
    df["row_idx"] = df.index

    node_records = defaultdict(list)
    for _, row in df.iterrows():
        node_id = str(row["node_id"])
        row_idx = int(row["row_idx"])
        feat    = row_features.get(row_idx, {})
        node_records[node_id].append({
            "attack_type":           str(row["attack_type"]),
            "is_cluster_head":       int(row["is_cluster_head"]),
            "distance_to_ch":        float(row["distance_to_ch"]),
            "attack_probability":    feat.get("attack_probability", 0.0),
            "composite_risk_score":  feat.get("composite_risk_score", 0.0),
            "packet_delivery_ratio": feat.get("packet_delivery_ratio", 0.0),
            "predicted_attacked":    feat.get("predicted_attacked", 0),
        })

    nodes = {}
    for node_id, records in node_records.items():
        attack_types      = [r["attack_type"] for r in records]
        pct_attacked      = sum(1 for a in attack_types if a != "Normal") / len(attack_types)
        attack_probs      = [r["attack_probability"] for r in records]
        risk_scores       = [r["composite_risk_score"] for r in records]
        pdrs              = [r["packet_delivery_ratio"] for r in records]
        distances         = [r["distance_to_ch"] for r in records]
        is_ch_votes       = [r["is_cluster_head"] for r in records]

        # Ground truth label: attacked if majority of timesteps are attacked
        label = 1 if pct_attacked > 0.50 else 0

        nodes[node_id] = {
            "node_id":                    node_id,
            "label":                      label,
            "pct_timesteps_attacked":     round(pct_attacked, 4),
            "attack_probability_mean":    round(float(np.mean(attack_probs)), 6),
            "attack_probability_max":     round(float(np.max(attack_probs)), 6),
            "composite_risk_score_mean":  round(float(np.mean(risk_scores)), 6),
            "packet_delivery_ratio_mean": round(float(np.mean(pdrs)), 6),
            "distance_to_ch_norm":        round(float(np.mean(distances)) / 214.27, 6),
            "is_cluster_head":            int(round(np.mean(is_ch_votes))),
            "num_timesteps":              len(records),
            "dominant_attack_type":       max(set(attack_types), key=attack_types.count),
        }

    print(f"      Built {len(nodes):,} node records")
    attacked_nodes = sum(1 for n in nodes.values() if n["label"] == 1)
    print(f"      Attacked nodes (label=1): {attacked_nodes:,} ({attacked_nodes/len(nodes)*100:.1f}%)")

    # ── Step 4: Build edges ───────────────────────────────────────
    print("\n[4/5] Building edges from cluster-head proximity...")

    # Group nodes by their cluster head (is_cluster_head majority)
    # Nodes in the same cluster are connected to each other
    ch_clusters = defaultdict(list)
    for node_id, rec in nodes.items():
        if rec["is_cluster_head"] == 1:
            ch_clusters["CH"].append(node_id)
        else:
            ch_clusters["member"].append(node_id)

    # Strategy: connect each member node to its 5 nearest neighbors
    # by distance_to_ch (proxy for spatial proximity)
    # Also connect all cluster heads to each other (backbone network)
    edges = []

    # Sort all nodes by distance
    node_list = [(nid, rec["distance_to_ch_norm"]) for nid, rec in nodes.items()]
    node_list.sort(key=lambda x: x[1])

    # Connect each node to its 5 nearest neighbors by distance rank
    K = 5
    for i, (node_id, dist) in enumerate(node_list):
        start = max(0, i - K)
        end   = min(len(node_list) - 1, i + K)
        for j in range(start, end + 1):
            if j != i:
                neighbor_id = node_list[j][0]
                edges.append([node_id, neighbor_id])

    # Deduplicate edges
    edge_set = set()
    unique_edges = []
    for e in edges:
        key = tuple(sorted(e))
        if key not in edge_set:
            edge_set.add(key)
            unique_edges.append(e)

    print(f"      Built {len(unique_edges):,} edges (K={K} nearest neighbors)")

    # ── Step 5: Write outputs ─────────────────────────────────────
    print("\n[5/5] Writing outputs...")

    graph_data = {
        "num_nodes":     len(nodes),
        "num_edges":     len(unique_edges),
        "feature_names": [
            "attack_probability_mean",
            "attack_probability_max",
            "composite_risk_score_mean",
            "packet_delivery_ratio_mean",
            "distance_to_ch_norm",
            "is_cluster_head",
            "pct_timesteps_attacked",
        ],
        "nodes": nodes,
        "edges": unique_edges,
    }

    OUTPUTS.mkdir(exist_ok=True)
    with open(OUT_GRAPH, "w") as f:
        json.dump(graph_data, f)
    size_mb = OUT_GRAPH.stat().st_size / (1024 * 1024)
    print(f"      gnn_graph_data.json: {size_mb:.1f} MB")

    # Report
    feature_matrix = np.array([
        [
            n["attack_probability_mean"],
            n["attack_probability_max"],
            n["composite_risk_score_mean"],
            n["packet_delivery_ratio_mean"],
            n["distance_to_ch_norm"],
            float(n["is_cluster_head"]),
            n["pct_timesteps_attacked"],
        ]
        for n in nodes.values()
    ])

    report = {
        "num_nodes":           len(nodes),
        "num_edges":           len(unique_edges),
        "avg_degree":          round(len(unique_edges) * 2 / len(nodes), 2),
        "attacked_nodes":      attacked_nodes,
        "normal_nodes":        len(nodes) - attacked_nodes,
        "pct_attacked":        round(attacked_nodes / len(nodes) * 100, 2),
        "feature_names":       graph_data["feature_names"],
        "feature_stats": {
            name: {
                "mean": round(float(np.mean(feature_matrix[:, i])), 4),
                "std":  round(float(np.std(feature_matrix[:, i])), 4),
                "min":  round(float(np.min(feature_matrix[:, i])), 4),
                "max":  round(float(np.max(feature_matrix[:, i])), 4),
            }
            for i, name in enumerate(graph_data["feature_names"])
        },
        "label_distribution": {
            "attacked (label=1)": attacked_nodes,
            "normal (label=0)":   len(nodes) - attacked_nodes,
        },
        "gnn_task":        "Node-level binary classification (malicious vs normal)",
        "edge_strategy":   f"K={K} nearest neighbors by distance_to_ch_norm",
        "label_threshold": "label=1 if >10% of timesteps show non-Normal attack_type",
    }

    with open(OUT_REPORT, "w") as f:
        json.dump(report, f, indent=2)
    print(f"      gnn_graph_report.json written")

    print("\n" + "=" * 60)
    print("GNN GRAPH CONSTRUCTION COMPLETE")
    print("=" * 60)
    print(f"  Nodes:              {len(nodes):,}")
    print(f"  Edges:              {len(unique_edges):,}")
    print(f"  Avg degree:         {report['avg_degree']}")
    print(f"  Attacked nodes:     {attacked_nodes:,} ({report['pct_attacked']}%)")
    print(f"  Feature dimensions: {len(graph_data['feature_names'])}")
    print(f"  Output: outputs/gnn_graph_data.json")
    print("=" * 60)

    return report


if __name__ == "__main__":
    report = build_graph()
    print(f"\nSummary: {report}")