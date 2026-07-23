"""
check_neighbor_feature_similarity.py
======================================
Tests hypothesis #3 directly: are KNN neighbors so numerically similar
that attention has nothing left to differentiate? Computes average
pairwise feature distance between each node and its graph neighbors,
compared to distance to a random sample of non-neighbor nodes.
"""
import json
import numpy as np
from sklearn.preprocessing import StandardScaler

GRAPH_PATH = "outputs/gnn_graph_data.json"

with open(GRAPH_PATH) as f:
    raw = json.load(f)

feature_names = [f for f in raw["feature_names"] if f != "pct_timesteps_attacked"]
nodes = raw["nodes"]
node_ids = list(nodes.keys())
id_to_idx = {nid: i for i, nid in enumerate(node_ids)}

X = np.array([[nodes[nid][f] for f in feature_names] for nid in node_ids])
X = StandardScaler().fit_transform(X)

# Build adjacency
neighbors = {nid: [] for nid in node_ids}
for a, b in raw["edges"]:
    neighbors[a].append(b)
    neighbors[b].append(a)

rng = np.random.default_rng(42)
neighbor_dists, random_dists = [], []

sample_ids = rng.choice(node_ids, size=min(500, len(node_ids)), replace=False)
for nid in sample_ids:
    idx = id_to_idx[nid]
    nbrs = neighbors[nid]
    if not nbrs:
        continue
    nbr_idxs = [id_to_idx[n] for n in nbrs]
    neighbor_dists.append(np.mean(np.linalg.norm(X[idx] - X[nbr_idxs], axis=1)))

    rand_idxs = rng.choice(len(node_ids), size=len(nbrs), replace=False)
    random_dists.append(np.mean(np.linalg.norm(X[idx] - X[rand_idxs], axis=1)))

print(f"Avg feature distance to GRAPH NEIGHBORS: {np.mean(neighbor_dists):.4f}")
print(f"Avg feature distance to RANDOM nodes:    {np.mean(random_dists):.4f}")
ratio = np.mean(neighbor_dists) / np.mean(random_dists)
print(f"Ratio (neighbor/random): {ratio:.3f}  "
      f"(closer to 0 = neighbors are much more similar than random -- "
      f"supports hypothesis #3; closer to 1 = neighbors aren't meaningfully "
      f"more similar than chance -- doesn't support #3)")