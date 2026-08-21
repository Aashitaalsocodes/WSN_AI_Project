import os
for f in ["data/processed/processed_data.csv", "outputs/attack_ground_truth.json"]:
    print(f, "exists:", os.path.exists(f))
