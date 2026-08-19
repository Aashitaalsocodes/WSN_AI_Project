"""
generate_preprocessed_nodes.py
Generates preprocessed_nodes.json for all 500 nodes with realistic values.
"""

import json
import random
from pathlib import Path

OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

# Get node IDs from routing_simulation.json
def get_node_ids():
    with open(OUTPUT_DIR / "routing_simulation_seed42.json", "r") as f:
        data = json.load(f)
    return data["node_ids"]

node_ids = get_node_ids()

# Generate realistic node features
preprocessed_nodes = {}

for node_id in node_ids:
    # Random but realistic values
    preprocessed_nodes[node_id] = {
        "historical_accuracy": round(random.uniform(0.70, 0.95), 3),
        "protocol_compliance": round(random.uniform(0.75, 0.95), 3),
        "neighbor_recommendation": round(random.uniform(0.60, 0.90), 3),
        "energy_risk": round(random.uniform(0.20, 0.80), 3),
    }

# Save
with open(OUTPUT_DIR / "preprocessed_nodes.json", "w") as f:
    json.dump(preprocessed_nodes, f, indent=2)

print(f"Generated preprocessed_nodes.json with {len(preprocessed_nodes)} nodes")