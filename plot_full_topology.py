"""
plot_full_topology.py

Regenerates the network topology figure (Figure 8) using the REAL
500-node routing simulation data, fixing the mismatch where the old
figure only showed 80 nodes.

Reads: outputs/routing_simulation.json
Writes: outputs/figure8_network_topology_500nodes.png
"""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx

OUTPUTS_DIR = Path("outputs")

with open(OUTPUTS_DIR / "routing_simulation.json", encoding="utf-8") as f:
    sim = json.load(f)

node_ids = sim["node_ids"]
edges = sim["edges"]

# Try to find which nodes are attacked/malicious - check common key names
attacked_nodes = set()
for key in ["attacked_nodes", "malicious_nodes", "compromised_nodes"]:
    if key in sim:
        attacked_nodes = set(sim[key])
        print(f"Found attacked nodes under key: '{key}'")
        break

if not attacked_nodes:
    # Fall back: check if baseline_routes has attacked node info
    if "baseline_routes" in sim:
        for route in sim["baseline_routes"]:
            attacked_nodes.update(route.get("attacked_nodes_in_path", []))
    if attacked_nodes:
        print("Found attacked nodes inside baseline_routes[].attacked_nodes_in_path")

print(f"Total nodes: {len(node_ids)}")
print(f"Attacked nodes found: {len(attacked_nodes)}")
if not attacked_nodes:
    print("WARNING: No attacked nodes found automatically - check routing_simulation.json's keys manually:")
    print(list(sim.keys()))

# Build graph
G = nx.Graph()
G.add_nodes_from(node_ids)
G.add_edges_from([tuple(e) for e in edges])

# Layout - spring layout works well for this size, may take a few seconds for 500 nodes
pos = nx.spring_layout(G, seed=42, k=0.15, iterations=50)

fig, ax = plt.subplots(figsize=(12, 10))
fig.patch.set_facecolor("#0a0a12")
ax.set_facecolor("#0a0a12")

normal_nodes = [n for n in node_ids if n not in attacked_nodes]

# Draw edges
nx.draw_networkx_edges(G, pos, ax=ax, edge_color="#2b6cff", alpha=0.25, width=0.5)

# Draw normal nodes
nx.draw_networkx_nodes(
    G, pos, nodelist=normal_nodes, ax=ax,
    node_color="white", node_size=20, alpha=0.85
)

# Draw attacked nodes
if attacked_nodes:
    nx.draw_networkx_nodes(
        G, pos, nodelist=list(attacked_nodes), ax=ax,
        node_color="#ff3b5c", node_size=45, alpha=0.95
    )

ax.set_title(
    f"NETWORK TOPOLOGY  ({len(node_ids)} nodes)",
    color="white", fontsize=14, fontweight="bold", loc="left", pad=15
)
ax.axis("off")

# Legend text
legend_text = f"Normal ({len(normal_nodes)})   Attacked ({len(attacked_nodes)})"
fig.text(0.5, 0.03, legend_text, ha="center", color="white", fontsize=11)

plt.tight_layout()
out_path = OUTPUTS_DIR / "figure8_network_topology_500nodes.png"
plt.savefig(out_path, dpi=200, facecolor=fig.get_facecolor())
print(f"\nSaved to {out_path}")