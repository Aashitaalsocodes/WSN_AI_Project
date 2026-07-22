"""
compare_attention_entropy.py
==============================
Computes attention entropy for every high-risk node in TWO attention
weight exports, and prints a side-by-side comparison table.

Entropy formula: -sum(w_i * log(w_i)) for each node's neighbor weights.
Lower entropy = more concentrated/differentiated attention (desirable).
Higher entropy = closer to uniform (the "under-differentiation" symptom).

Reports entropy as a RATIO of the theoretical max entropy for that node's
neighbor count (log(K)), so it's comparable across nodes with different
numbers of neighbors -- a ratio near 1.0 means "close to uniform", a ratio
near 0 means "very concentrated/sharp".

USAGE
-----
    python compare_attention_entropy.py <path_a> <path_b> [--label-a LABEL] [--label-b LABEL]

Examples:
    # Original graph construction ablation
    python compare_attention_entropy.py outputs/gnn_attention_weights.json outputs/gnn_attention_weights_v2.json ^
        --label-a "ORIGINAL GRAPH (1D sort-window)" --label-b "V2 GRAPH (multi-dimensional KNN)"

    # Epoch-count ablation (same graph, 100 vs 300 epochs)
    python compare_attention_entropy.py outputs/gnn_attention_weights.json outputs/gnn_attention_weights_300ep.json ^
        --label-a "ORIGINAL GRAPH, 100 epochs" --label-b "ORIGINAL GRAPH, 300 epochs"

If --label-a/--label-b are omitted, the filenames are used as labels.
"""
import argparse
import json
from pathlib import Path
import numpy as np


def load_attention(path):
    with open(path) as f:
        return json.load(f)


def node_entropy_ratio(neighbor_list):
    """neighbor_list: list of {"neighbor": ..., "attention_weight": ...}"""
    weights = np.array([n["attention_weight"] for n in neighbor_list], dtype=float)
    weights = weights[weights > 0]
    if len(weights) <= 1:
        return None  # can't compute entropy meaningfully with 0-1 neighbors
    # Normalize in case weights don't sum to exactly 1 (numerical drift)
    weights = weights / weights.sum()
    entropy = -np.sum(weights * np.log(weights))
    max_entropy = np.log(len(weights))
    if max_entropy == 0:
        return None
    return entropy / max_entropy


def summarize(path, label):
    data = load_attention(path)
    ratios = []
    degrees = []
    for node_id, neighbors in data.items():
        r = node_entropy_ratio(neighbors)
        if r is not None:
            ratios.append(r)
            degrees.append(len(neighbors))
    ratios = np.array(ratios)
    print(f"\n{label}")
    print(f"  Source file:           {path}")
    print(f"  Nodes analyzed:        {len(ratios)}")
    print(f"  Avg neighbors/node:    {np.mean(degrees):.1f}")
    print(f"  Mean entropy ratio:    {np.mean(ratios):.4f}  "
          f"(1.0 = perfectly uniform, 0.0 = fully concentrated on one neighbor)")
    print(f"  Median entropy ratio:  {np.median(ratios):.4f}")
    print(f"  Std of entropy ratio:  {np.std(ratios):.4f}")
    print(f"  Min / Max:             {np.min(ratios):.4f} / {np.max(ratios):.4f}")
    return ratios


def parse_args():
    p = argparse.ArgumentParser(
        description="Compare attention entropy between two GNN attention weight exports."
    )
    p.add_argument("path_a", type=Path, help="Path to first attention weights JSON (baseline)")
    p.add_argument("path_b", type=Path, help="Path to second attention weights JSON (comparison)")
    p.add_argument("--label-a", default=None, help="Display label for path_a")
    p.add_argument("--label-b", default=None, help="Display label for path_b")
    return p.parse_args()


def main():
    args = parse_args()

    if not args.path_a.exists():
        print(f"[!] Missing: {args.path_a}")
        return
    if not args.path_b.exists():
        print(f"[!] Missing: {args.path_b}")
        return

    label_a = args.label_a or f"A: {args.path_a.name}"
    label_b = args.label_b or f"B: {args.path_b.name}"

    print("=" * 70)
    print(f"ATTENTION ENTROPY COMPARISON — {label_a}  vs.  {label_b}")
    print("=" * 70)

    ratios_a = summarize(args.path_a, label_a)
    ratios_b = summarize(args.path_b, label_b)

    print("\n" + "=" * 70)
    print("VERDICT")
    print("=" * 70)

    mean_a = np.mean(ratios_a)
    mean_b = np.mean(ratios_b)
    diff = mean_a - mean_b
    pct_change = (diff / mean_a) * 100 if mean_a != 0 else float("nan")

    if diff > 0.02:
        print(f"B shows LOWER entropy ratio (more differentiated attention) "
              f"than A by {diff:.4f} ({pct_change:.1f}% reduction).")
    elif diff < -0.02:
        print(f"B shows HIGHER entropy ratio (more uniform attention) "
              f"than A by {abs(diff):.4f} ({abs(pct_change):.1f}% increase). "
              f"Attention differentiation got WORSE, not better, going from A to B.")
    else:
        print(f"Difference is small ({diff:.4f}, {pct_change:.1f}%) — no meaningful "
              f"change in attention differentiation between A and B.")

    print(f"\n(Std of entropy ratio: A={np.std(ratios_a):.4f}, B={np.std(ratios_b):.4f}. "
          f"A std near 0.0000 across all nodes is unusual and worth flagging on its own — "
          f"it means every node got essentially the same entropy value, not just a "
          f"similar one.)")


if __name__ == "__main__":
    main()