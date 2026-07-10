import json
import collections

d = json.load(open("outputs/anomaly_explanations_shap.json"))["explanations"]
seen = collections.defaultdict(int)

for e in d:
    t = e["attack_type_ground_truth"]
    if t != "Normal" and seen[t] < 2:
        seen[t] += 1
        print(t, "-", e["row_index"], ":", e["explanation"])