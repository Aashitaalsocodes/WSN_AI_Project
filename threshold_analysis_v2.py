import pandas as pd
from trust_engine import TrustEngine

df = pd.read_csv("outputs/seed42_reconstructed_anomaly_scores.csv")
engine = TrustEngine()

trust_rows = []
for (node, rnd), group in df.groupby(["node_id", "round"]):
    pass  # not needed, df already one row per node/round

work = df.copy()
work["historical_accuracy"] = 0.8
work["protocol_compliance"] = 0.8
work["neighbor_recommendation"] = 0.5
work = engine.update_trust(work)

legit_ids = work.loc[~work.groupby("node_id")["is_attacked"].transform("any"), "node_id"].unique()
print(f"Legitimate (never attacked) nodes: {len(legit_ids)}")

legit_deltas = []
for node in legit_ids:
    series = work[work["node_id"] == node].sort_values("round")["trust_score"].values
    for t in range(1, len(series)):
        legit_deltas.append(abs(series[t] - series[t-1]))

deltas = pd.Series(legit_deltas)
print(f"\nLegitimate round-to-round |delta trust_score| (n={len(deltas)}):")
print(deltas.describe())
for pct in [50, 90, 95, 99, 99.9, 100]:
    print(f"  p{pct}: {deltas.quantile(pct/100):.6f}")

print("\nFalse-reject rate on legitimate nodes at candidate thresholds:")
for thresh in [0.02, 0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5]:
    rate = (deltas > thresh).mean()
    print(f"  threshold={thresh}: false_reject_rate={rate:.6f} ({int((deltas>thresh).sum())}/{len(deltas)})")

# Attacked nodes: deltas at the round they get flagged attacked
attacked_ids = work.loc[work.groupby("node_id")["is_attacked"].transform("any"), "node_id"].unique()
attack_deltas = []
for node in attacked_ids:
    sub = work[work["node_id"] == node].sort_values("round")
    series = sub["trust_score"].values
    attacked_flags = sub["is_attacked"].values
    for t in range(1, len(series)):
        if attacked_flags[t] and not attacked_flags[t-1]:
            attack_deltas.append(abs(series[t] - series[t-1]))

if attack_deltas:
    ad = pd.Series(attack_deltas)
    print(f"\n|delta| when a node transitions into attacked state (n={len(ad)}):")
    print(ad.describe())
    print("\nDetection rate at candidate thresholds:")
    for thresh in [0.02, 0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5]:
        rate = (ad > thresh).mean()
        print(f"  threshold={thresh}: detect_rate={rate:.6f} ({int((ad>thresh).sum())}/{len(ad)})")
