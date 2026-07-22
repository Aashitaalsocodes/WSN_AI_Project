"""
run_gat_v2.py
=============
Runs ONLY the GAT-for-attention path from gnn_model.py, but against the
ablation graph (outputs/gnn_graph_data_v2.json) instead of the original.

Does NOT touch gnn_model.py, does NOT retrain SAGE (unnecessary for this
ablation -- SAGE remains the production model either way), and writes to a
SEPARATE output file so your original attention weights are untouched.

Usage: place this file in the same directory as gnn_model.py, then:
    python run_gat_v2.py
"""

from pathlib import Path

# Import everything we need directly from the existing, working script --
# no duplication of model/training logic, so there's no risk of the two
# implementations drifting out of sync.
from gnn_model import (
    load_graph,
    make_masks,
    train_gat_for_attention,
    export_attention_sample,
    TEST_SIZE,
    SEED,
)

GRAPH_PATH_V2 = "outputs/gnn_graph_data_v2.json"
ATTENTION_OUTPUT_PATH_V2 = "outputs/gnn_attention_weights_v2.json"


def main():
    print("=" * 60)
    print("Ablation: GAT attention on multi-dimensional KNN graph (v2)")
    print("=" * 60)

    data, node_ids, feature_names = load_graph(GRAPH_PATH_V2)
    num_nodes = data.x.shape[0]
    in_channels = data.x.shape[1]

    train_mask, test_mask = make_masks(num_nodes, data.y, TEST_SIZE, SEED)

    gat_model = train_gat_for_attention(data, train_mask, test_mask, in_channels)
    export_attention_sample(gat_model, data, node_ids, ATTENTION_OUTPUT_PATH_V2)

    print("\nDone. Compare against the original:")
    print("  Original: outputs/gnn_attention_weights.json")
    print(f"  v2 (this run): {ATTENTION_OUTPUT_PATH_V2}")


if __name__ == "__main__":
    main()