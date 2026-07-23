"""
run_gat_more_epochs.py
=======================
Runs ONLY the GAT-for-attention path from gnn_model.py, on the ORIGINAL
graph (outputs/gnn_graph_data.json), but with 300 epochs instead of the
default 100 -- to test whether near-uniform attention entropy is a
training-time (under-training) issue rather than a graph-structure issue.

Does NOT touch gnn_model.py, does NOT retrain SAGE, and writes to a
SEPARATE output file so the original 100-epoch attention weights are
untouched.

Usage: place this file in the same directory as gnn_model.py, then:
    python run_gat_more_epochs.py
"""

from gnn_model import (
    load_graph,
    make_masks,
    train_gat_for_attention,
    export_attention_sample,
    GRAPH_PATH,
    TEST_SIZE,
    SEED,
)

ATTENTION_OUTPUT_PATH_300EP = "outputs/gnn_attention_weights_300epoch.json"
EPOCHS_EXTENDED = 300


def main():
    print("=" * 60)
    print("Ablation: GAT attention with 300 epochs (vs. default 100)")
    print("Same ORIGINAL graph as the baseline -- isolating training time")
    print("as the variable, not graph structure.")
    print("=" * 60)

    data, node_ids, feature_names = load_graph(GRAPH_PATH)
    num_nodes = data.x.shape[0]
    in_channels = data.x.shape[1]

    train_mask, test_mask = make_masks(num_nodes, data.y, TEST_SIZE, SEED)

    gat_model = train_gat_for_attention(
        data, train_mask, test_mask, in_channels, epochs=EPOCHS_EXTENDED
    )
    export_attention_sample(gat_model, data, node_ids, ATTENTION_OUTPUT_PATH_300EP)

    print("\nDone. Compare against the 100-epoch baseline:")
    print("  100 epochs (original): outputs/gnn_attention_weights.json")
    print(f"  300 epochs (this run): {ATTENTION_OUTPUT_PATH_300EP}")


if __name__ == "__main__":
    main()