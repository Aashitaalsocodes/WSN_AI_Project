import json

with open("outputs/digital_twin_results_packetmodel_seed42.json", encoding="utf-8") as f:
    data = json.load(f)

r0 = data["rounds"][0]
for k, v in r0.items():
    t = type(v).__name__
    if isinstance(v, (list, dict)):
        print(f"{k}: {t}, len={len(v)}")
    else:
        print(f"{k}: {t} = {v}")
