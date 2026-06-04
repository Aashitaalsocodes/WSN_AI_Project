import json

data = json.load(open('outputs/energy_forecast_ibrl.json'))
items = list(data.items())
print(f"Total nodes: {len(items)}")
print(f"First 3 nodes:")
for k, v in items[:3]:
    print(f"  Node {k}: {v}")