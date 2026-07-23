"""
check_topology_fields.py
=========================
Checks whether the dataset/graph outputs contain any topology or routing
information (as opposed to purely feature-based similarity), which would be
needed to build a non-KNN, connectivity-based graph.

Looks in three places:
1. outputs/gnn_graph_data.json -- the feature_names list and a sample node's
   raw fields (in case fields exist but weren't used in graph construction)
2. data/processed/processed_data.csv -- the full preprocessed dataset, which
   may have columns not carried into the graph JSON at all
3. outputs/preprocessed_nodes.json -- Task 1's per-node output, another
   place routing-relevant fields might live

Flags any column/field name that looks routing/topology-related, based on
common WSN-DS / WSN-simulation naming patterns.
"""
import json
import os

ROUTING_KEYWORDS = [
    "cluster", "ch_id", "cluster_id", "hop", "route", "routing", "parent",
    "child", "neighbor_id", "neighbor_list", "rank", "depth", "level",
    "sender", "receiver", "src", "dst", "next_hop", "path", "topology",
    "adjacency", "x_coord", "y_coord", "position", "location", "coord",
    "dist_to_bs", "dist_to_ch", "energy_level", "round", "is_ch"
]


def flag_fields(field_names, source_label):
    print(f"\n--- {source_label} ---")
    if not field_names:
        print("  (not found / empty)")
        return
    hits = [f for f in field_names if any(kw in f.lower() for kw in ROUTING_KEYWORDS)]
    print(f"  Total fields: {len(field_names)}")
    if hits:
        print(f"  Possible topology/routing fields found: {hits}")
    else:
        print("  No topology/routing-looking fields found.")
    print(f"  All fields: {field_names}")


def check_graph_json(path="outputs/gnn_graph_data.json"):
    if not os.path.exists(path):
        print(f"\n--- {path} ---\n  File not found.")
        return
    with open(path) as f:
        raw = json.load(f)
    feature_names = raw.get("feature_names", [])
    flag_fields(feature_names, f"{path} (feature_names used in graph)")

    nodes = raw.get("nodes", {})
    if nodes:
        sample_node_id = next(iter(nodes))
        sample_fields = list(nodes[sample_node_id].keys())
        flag_fields(sample_fields, f"{path} (ALL raw per-node fields, sample node {sample_node_id})")


def check_csv(path="data/processed/processed_data.csv"):
    if not os.path.exists(path):
        print(f"\n--- {path} ---\n  File not found.")
        return
    with open(path) as f:
        header = f.readline().strip()
    columns = [c.strip() for c in header.split(",")]
    flag_fields(columns, f"{path} (CSV columns)")


def check_preprocessed_nodes(path="outputs/preprocessed_nodes.json"):
    if not os.path.exists(path):
        print(f"\n--- {path} ---\n  File not found.")
        return
    with open(path) as f:
        raw = json.load(f)
    if isinstance(raw, dict) and raw:
        sample_id = next(iter(raw))
        sample_fields = list(raw[sample_id].keys())
        flag_fields(sample_fields, f"{path} (sample node {sample_id})")
    elif isinstance(raw, list) and raw:
        sample_fields = list(raw[0].keys())
        flag_fields(sample_fields, f"{path} (sample record)")
    else:
        print(f"\n--- {path} ---\n  Unexpected format or empty.")


def main():
    print("=" * 70)
    print("CHECKING FOR TOPOLOGY / ROUTING FIELDS ACROSS DATASET FILES")
    print("=" * 70)
    check_graph_json()
    check_csv()
    check_preprocessed_nodes()
    print("\n" + "=" * 70)
    print("If any 'possible topology/routing fields' were flagged above, a")
    print("connectivity-based graph (instead of feature-KNN) may be feasible.")
    print("If none were found, the dataset likely only supports feature-")
    print("similarity graphs (like the current KNN/sort-window approach),")
    print("and a topology-based rebuild would require re-simulating routing")
    print("data that doesn't currently exist in the pipeline.")
    print("=" * 70)


if __name__ == "__main__":
    main()