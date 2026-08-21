"""
build_seed42_anomaly_scores.py
Trains an Isolation Forest on seed42's own per-node, per-round energy
features (energy_remaining, delta, rolling avg) -- same ID space as the
trust reconstruction, so no ID-mapping problem. Uses config.py's own
ISOLATION_FOREST_CONTAMINATION/N_ESTIMATORS. Ground truth (attacked_nodes)
is used ONLY to evaluate the resulting anomaly scores, not for training
(this stays unsupervised, consistent with an Isolation Forest).
"""

import json
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from config import ISOLATION_FOREST_CONTAMINATION, ISOLATION_FOREST_N_ESTIMATORS

with open("outputs/digital_twin_results_packetmodel_seed42.json", encoding="utf-8") as f:
    data = json.load(f)

rounds = data["rounds"]
all_node_ids = list(rounds[0]["node_energy_snapshot"].keys())

# Build long-format feature table: one row per (node, round)
rows = []
energy_history = {n: [] for n in all_node_ids}
for t, r in enumerate(rounds):
    attacked_set = set(r["attacked_nodes"])
    snap = r["node_energy_snapshot"]
    for n in all_node_ids:
        e = snap.get(n, np.nan)
        energy_history[n].append(e)
        prev_e = energy_history[n][t-1] if t > 0 else e
        delta = e - prev_e
        window = energy_history[n][max(0, t-2):t+1]
        rolling_avg = sum(window) / len(window)
        rows.append({
            "node_id": n, "round": t, "energy_remaining": e,
            "energy_delta": delta, "rolling_avg": rolling_avg,
            "is_attacked": n in attacked_set
        })

df = pd.DataFrame(rows)
print("Feature table shape:", df.shape)
print("Attacked rows:", df["is_attacked"].sum(), "/", len(df))

FEATURES = ["energy_remaining", "energy_delta", "rolling_avg"]
X = df[FEATURES].fillna(0)

iso = IsolationForest(
    n_estimators=ISOLATION_FOREST_N_ESTIMATORS,
    contamination=ISOLATION_FOREST_CONTAMINATION,
    random_state=42
)
iso.fit(X)

# decision_function: higher = more normal. Convert to anomaly_score in [0,1]
raw = -iso.decision_function(X)  # higher = more anomalous now
anomaly_score = (raw - raw.min()) / (raw.max() - raw.min())
df["anomaly_score"] = anomaly_score

pred = iso.predict(X)  # -1 = anomaly, 1 = normal
df["predicted_anomaly"] = (pred == -1)

# Evaluate against real ground truth
tp = ((df["predicted_anomaly"]) & (df["is_attacked"])).sum()
fp = ((df["predicted_anomaly"]) & (~df["is_attacked"])).sum()
fn = ((~df["predicted_anomaly"]) & (df["is_attacked"])).sum()
tn = ((~df["predicted_anomaly"]) & (~df["is_attacked"])).sum()
precision = tp / (tp + fp) if (tp + fp) else 0
recall = tp / (tp + fn) if (tp + fn) else 0
print(f"\nUnsupervised IsolationForest vs real attack labels:")
print(f"  TP={tp} FP={fp} FN={fn} TN={tn}")
print(f"  precision={precision:.4f} recall={recall:.4f}")
print(f"\nanomaly_score by is_attacked group:")
print(df.groupby("is_attacked")["anomaly_score"].describe())

df.to_csv("outputs/seed42_reconstructed_anomaly_scores.csv", index=False)
print("\nSaved to outputs/seed42_reconstructed_anomaly_scores.csv")
