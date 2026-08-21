import json

with open("outputs/digital_twin_results_packetmodel_seed42.json", encoding="utf-8") as f:
    data = json.load(f)

print("num_rounds:", data["num_rounds"])
print("num_nodes:", data["num_nodes"])

rounds = data["rounds"]
print(f"rounds type={type(rounds).__name__} len={len(rounds)}")

r0 = rounds[0]
print(f"round[0] type={type(r0).__name__}")
if isinstance(r0, dict):
    print("round[0] keys:", list(r0.keys()))
    for k in list(r0.keys())[:5]:
        v = r0[k]
        print(f"  {k}: type={type(v).__name__}, sample={str(v)[:200]}")

es = data["energy_summary"]
print("energy_summary type:", type(es).__name__)
if isinstance(es, dict):
    print("energy_summary keys:", list(es.keys())[:10])
