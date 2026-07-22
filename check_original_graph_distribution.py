"""
check_original_graph_distribution.py
======================================
Computes the same neighbor-appearance diagnostic that build_edges_v2.py
prints, but against the ORIGINAL gnn_graph_data.json edges -- so we have
a real, direct, apples-to-apples baseline number instead of a guess.
"""

import json
from pathlib import Path
from collections import Counter
import numpy as np

OUTPUTS = Path(__file__).parent / "outputs"

with open(OUTPUTS / "gnn_graph_data.json") as f:
    original = json.load(f)

edges = original["edges"]
appearance_counts = Counter()
for a, b in edges:
    appearance_counts[a] += 1
    appearance_counts[b] += 1

counts = list(appearance_counts.values())
print(f"ORIGINAL graph (1D sort-window, K=5):")
print(f"  Total edges: {len(edges):,}")
print(f"  Neighbor-appearance distribution: mean={np.mean(counts):.1f}, "
      f"std={np.std(counts):.1f}, max={np.max(counts)}")
print(f"  Max / mean ratio: {np.max(counts) / np.mean(counts):.1f}x")

# Also show how many nodes appear more than, say, 3x the mean --
# a rough proxy for "how many anchor nodes are there"
threshold = 3 * np.mean(counts)
num_anchors = sum(1 for c in counts if c > threshold)
print(f"  Nodes appearing >3x the mean (rough 'anchor node' count): {num_anchors}")