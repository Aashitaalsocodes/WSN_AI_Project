import json

with open("outputs/digital_twin_results_packetmodel_seed42.json", encoding="utf-8") as f:
    data = json.load(f)

r0 = data["rounds"][0]
snap = r0["node_energy_snapshot"]
print("node_energy_snapshot type:", type(snap).__name__)
if isinstance(snap, dict):
    k0 = list(snap.keys())[0]
    print("first key:", k0, "-> value:", snap[k0])
elif isinstance(snap, list):
    print("len:", len(snap))
    print("item[0]:", snap[0])

print()
print("avg_trust_score across all rounds:")
for r in data["rounds"]:
    print(f"  round {r['round']}: avg_trust_score={r['avg_trust_score']}")
