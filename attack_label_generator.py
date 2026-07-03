import pandas as pd, json, os

df = pd.read_csv('data/processed/processed_data.csv')

ground_truth = {}
for i, row in df.iterrows():
    attack = row['attack_type']
    if attack == 'Normal':
        ground_truth[str(i)] = {"attack_type": "none", "is_attacked": 0}
    else:
        ground_truth[str(i)] = {"attack_type": attack.lower(), "is_attacked": 1}

os.makedirs("outputs", exist_ok=True)
with open("outputs/attack_ground_truth.json", "w") as f:
    json.dump(ground_truth, f)

attacked = [v for v in ground_truth.values() if v["is_attacked"] == 1]
print(f"Total nodes: {len(ground_truth)}")
print(f"Attacked: {len(attacked)}")
print(f"Sample entries:")
for k in ["0", "1", "2"]:
    print(f"  {k}: {ground_truth[k]}")