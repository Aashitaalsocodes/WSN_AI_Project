"""
run_gat_no_dropout.py
======================
Tests hypothesis #2: is dropout=0.2 flattening attention scores?
Runs GAT on the ORIGINAL graph, 100 epochs (same as baseline), but with
dropout=0.0 instead of 0.2. If entropy still doesn't drop, dropout isn't
the cause either -- pointing more strongly at hypothesis #3.
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

ATTENTION_OUTPUT_PATH_NODROPOUT = "outputs/gnn_attention_weights_dropout0.json"


def main():
    print("=" * 60)
    print("Ablation: GAT attention with dropout=0.0 (vs. default 0.2)")
    print("Same ORIGINAL graph, same 100 epochs -- isolating dropout")
    print("as the variable.")
    print("=" * 60)

    data, node_ids, feature_names = load_graph(GRAPH_PATH)
    num_nodes = data.x.shape[0]
    in_channels = data.x.shape[1]

    train_mask, test_mask = make_masks(num_nodes, data.y, TEST_SIZE, SEED)

    gat_model = train_gat_for_attention(
        data, train_mask, test_mask, in_channels, epochs=100, dropout=0.0
    )
    export_attention_sample(gat_model, data, node_ids, ATTENTION_OUTPUT_PATH_NODROPOUT)

    print("\nDone. Compare against the dropout=0.2 baseline:")
    print("  dropout=0.2 (original): outputs/gnn_attention_weights.json")
    print(f"  dropout=0.0 (this run): {ATTENTION_OUTPUT_PATH_NODROPOUT}")


if __name__ == "__main__":
    main()