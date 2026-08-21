import json

with open("outputs/digital_twin_results_packetmodel_seed42.json", encoding="utf-8") as f:
    data = json.load(f)

r0 = data["rounds"][0]
r5 = data["rounds"][5]

print("compromised_routes_detail sample:", r0["compromised_routes_detail"][:2])
print()
print("missed_detections sample:", r0["missed_detections"][:5])
print()
print("excluded_nodes sample:", r0["excluded_nodes"][:5])
print()
print("attacked_node_types sample:", dict(list(r0["attacked_node_types"].items())[:5]))

# check if node_energy_snapshot values change round to round for a given node
sample_node = list(r0["node_energy_snapshot"].keys())[0]
print(f"\nnode {sample_node} energy across first 5 rounds:")
for i in range(5):
    r = data["rounds"][i]
    print(f"  round {i}: {r['node_energy_snapshot'].get(sample_node)}")
