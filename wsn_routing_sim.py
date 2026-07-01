import json
import random
import math
import networkx as nx

# Load real row indices from attack_classifier_predictions.json
print("Loading attack predictions...")
with open('outputs/attack_classifier_predictions.json') as f:
    attack_preds = json.load(f)

# Sample 500 real row indices
all_ids = list(attack_preds.keys())
random.seed(42)
sampled_ids = random.sample(all_ids, 500)
sampled_ids_set = set(sampled_ids)

# Assign each node a random 2D position
print("Building topology...")
positions = {nid: (random.uniform(0, 1), random.uniform(0, 1)) for nid in sampled_ids}

# Connect nodes within communication radius
RADIUS = 0.15
edges = []
id_list = sampled_ids

for i in range(len(id_list)):
    for j in range(i + 1, len(id_list)):
        a, b = id_list[i], id_list[j]
        ax, ay = positions[a]
        bx, by = positions[b]
        dist = math.sqrt((ax - bx)**2 + (ay - by)**2)
        if dist <= RADIUS:
            edges.append((a, b))

print(f"Nodes: {len(sampled_ids)}, Edges: {len(edges)}")

# Build graph
G = nx.Graph()
G.add_nodes_from(sampled_ids)
G.add_edges_from(edges)

# Check connectivity
largest_cc = max(nx.connected_components(G), key=len)
print(f"Largest connected component: {len(largest_cc)} nodes")
connected_ids = list(largest_cc)

# Baseline routing — 200 random source→destination pairs
print("Running baseline routing...")
NUM_ROUTES = 200
routes = []
attempts = 0

while len(routes) < NUM_ROUTES and attempts < 2000:
    src, dst = random.sample(connected_ids, 2)
    attempts += 1
    try:
        path = nx.shortest_path(G, source=src, target=dst)
        attacked_in_path = [
            n for n in path
            if attack_preds.get(n, {}).get('predicted_attacked', 0) == 1
        ]
        routes.append({
            "route_id": len(routes),
            "source": src,
            "destination": dst,
            "path": path,
            "hop_count": len(path) - 1,
            "passes_through_attacked_node": len(attacked_in_path) > 0,
            "attacked_nodes_in_path": attacked_in_path
        })
    except nx.NetworkXNoPath:
        continue

# Summary
avg_hops = sum(r['hop_count'] for r in routes) / len(routes)
compromised = sum(1 for r in routes if r['passes_through_attacked_node'])
pct_compromised = round((compromised / len(routes)) * 100, 1)

print(f"\nRoutes computed: {len(routes)}")
print(f"Avg hop count: {avg_hops:.2f}")
print(f"Compromised routes: {compromised} ({pct_compromised}%)")

# Save output
output = {
    "num_nodes": len(connected_ids),
    "num_edges": len(edges),
    "communication_radius": RADIUS,
    "node_ids": connected_ids,
    "edges": edges,
    "baseline_routes": routes,
    "baseline_summary": {
        "total_routes": len(routes),
        "avg_hop_count": round(avg_hops, 2),
        "routes_through_attacked_node": compromised,
        "pct_compromised_routes": pct_compromised
    }
}

with open('outputs/routing_simulation.json', 'w') as f:
    json.dump(output, f)

print("Saved to outputs/routing_simulation.json")