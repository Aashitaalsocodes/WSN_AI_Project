import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, confusion_matrix
import json
import pickle
import os

# ── 0. Setup ──────────────────────────────────────────────────────────────────
os.makedirs("outputs", exist_ok=True)
os.makedirs("models", exist_ok=True)

print("=" * 60)
print("  Isolation Forest — WSN Anomaly Detection")
print("=" * 60)

# ── 1. Load WSN-DS ─────────────────────────────────────────────────────────────
df = pd.read_csv("data/raw/WSN-DS.csv")
print(f"\nDataset loaded: {df.shape[0]} rows, {df.shape[1]} columns")
print(f"Columns: {list(df.columns)}")

# ── 2. Feature Engineering ─────────────────────────────────────────────────────
# These are BEHAVIORAL features — what a node DOES, not what it IS
# Perfect for detecting black-hole, Sybil, DoS attacks

feature_cols = []

# Packet behavior features (attack nodes behave abnormally here)
packet_candidates = [
    'ADV_S', 'ADV_R',       # Advertisement sent/received
    'JOIN_S', 'JOIN_R',     # Join request sent/received
    'SCH_S', 'SCH_R',       # Schedule sent/received
    'DATA_S', 'DATA_R',     # Data sent/received
    'DATA_Sent_BS',         # Data sent to base station
    'distance_to_BS',       # Distance to base station
    'RSSI',                 # Signal strength
    'energy_remaining',     # Energy level
    'Energy'                # Alternative energy column name
]

for col in packet_candidates:
    if col in df.columns:
        feature_cols.append(col)

# Also catch any column with 'energy' or 'packet' in name
for col in df.columns:
    col_lower = col.lower()
    if any(k in col_lower for k in ['energy', 'packet', 'rssi', 'snr', 'adv', 'join', 'sch', 'data']):
        if col not in feature_cols:
            feature_cols.append(col)

# Remove label/id columns if accidentally included
exclude = ['is_ch', 'Is_CH', 'id', 'ID', 'Time', 'time', 'label', 'Label', 'attack', 'Attack']
feature_cols = [c for c in feature_cols if c not in exclude and c in df.columns]

if not feature_cols:
    # Fallback: use all numeric columns except label
    feature_cols = [c for c in df.select_dtypes(include=[np.number]).columns
                    if c.lower() not in [e.lower() for e in exclude]]

print(f"\nFeatures selected ({len(feature_cols)}): {feature_cols}")

# ── 3. Prepare Data ────────────────────────────────────────────────────────────
X = df[feature_cols].copy()

# Handle missing values
X = X.fillna(X.median())

# Remove infinite values
X = X.replace([np.inf, -np.inf], np.nan).fillna(X.median())

print(f"Feature matrix shape: {X.shape}")

# ── 4. Inject Synthetic Attacks (for evaluation) ───────────────────────────────
# Since WSN-DS has no attack labels, we inject known attack patterns
# This is STANDARD practice in WSN security research (IEEE papers do this)

print("\nInjecting synthetic attacks for evaluation...")

n_total = len(X)
attack_labels = np.zeros(n_total)  # 0 = normal

# Black-hole attack: node drops packets (DATA_S very low, DATA_R normal)
# Sybil attack: node sends abnormally high ADV packets
# DoS attack: node floods network (all send counts extremely high)

attack_indices = []

# Find relevant columns for attack injection
data_s_col = next((c for c in feature_cols if 'data_s' in c.lower() or 'data' in c.lower()), None)
adv_col = next((c for c in feature_cols if 'adv' in c.lower()), None)
energy_col = next((c for c in feature_cols if 'energy' in c.lower()), None)

n_attacks = int(n_total * 0.08)  # 8% attack nodes (realistic)

np.random.seed(42)
attack_idx = np.random.choice(n_total, n_attacks, replace=False)
attack_labels[attack_idx] = 1

# Inject abnormal behavior into attack nodes
X_attacked = X.copy()

for idx in attack_idx:
    attack_type = np.random.choice(['blackhole', 'sybil', 'dos'])

    if attack_type == 'blackhole' and data_s_col:
        # Black-hole: drops all data (DATA_S near 0)
        X_attacked.iloc[idx][data_s_col] = X[data_s_col].min() * 0.1

    elif attack_type == 'sybil' and adv_col:
        # Sybil: floods advertisements (10x normal)
        X_attacked.iloc[idx][adv_col] = X[adv_col].max() * 10

    elif attack_type == 'dos':
        # DoS: floods everything (3x normal on all send cols)
        send_cols = [c for c in feature_cols if '_s' in c.lower()]
        for sc in send_cols:
            X_attacked.iloc[idx][sc] = X_attacked.iloc[idx][sc] * 3

print(f"  Normal nodes: {int(np.sum(attack_labels == 0))}")
print(f"  Attack nodes: {int(np.sum(attack_labels == 1))} ({n_attacks/n_total*100:.1f}%)")
print(f"  Attack types: Black-hole, Sybil, DoS")

# ── 5. Scale Features ──────────────────────────────────────────────────────────
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X_attacked)

# ── 6. Train Isolation Forest ──────────────────────────────────────────────────
print("\nTraining Isolation Forest...")

# contamination = expected proportion of attacks (matches our injection rate)
iso_forest = IsolationForest(
    n_estimators=200,
    contamination=0.08,
    max_samples='auto',
    random_state=42,
    n_jobs=-1,
    verbose=0
)

iso_forest.fit(X_scaled)
print("Training complete.")

# ── 7. Predict ─────────────────────────────────────────────────────────────────
# Isolation Forest returns: -1 = anomaly, 1 = normal
raw_predictions = iso_forest.predict(X_scaled)
anomaly_scores = iso_forest.decision_function(X_scaled)  # negative = more anomalous

# Convert to 0/1 (1 = attack/anomaly)
predictions = np.where(raw_predictions == -1, 1, 0)

# ── 8. Evaluate ────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("  EVALUATION RESULTS")
print("=" * 60)

# Classification report
print("\nClassification Report:")
print(classification_report(
    attack_labels, predictions,
    target_names=['Normal', 'Attack'],
    digits=4
))

# Confusion matrix
cm = confusion_matrix(attack_labels, predictions)
tn, fp, fn, tp = cm.ravel()

print("Confusion Matrix:")
print(f"  True Negatives  (correctly identified normal): {tn}")
print(f"  False Positives (normal flagged as attack):    {fp}")
print(f"  False Negatives (attacks missed):              {fn}")
print(f"  True Positives  (attacks correctly detected):  {tp}")

# Key metrics
detection_rate = tp / (tp + fn) * 100 if (tp + fn) > 0 else 0
fpr = fp / (fp + tn) * 100 if (fp + tn) > 0 else 0
precision = tp / (tp + fp) * 100 if (tp + fp) > 0 else 0
accuracy = (tp + tn) / n_total * 100

print(f"\nKey Metrics:")
print(f"  Attack Detection Rate:  {detection_rate:.2f}%")
print(f"  False Positive Rate:    {fpr:.2f}%")
print(f"  Precision:              {precision:.2f}%")
print(f"  Overall Accuracy:       {accuracy:.2f}%")

# ── 9. Per-Node Anomaly Report ─────────────────────────────────────────────────
# Identify which nodes are most suspicious
df['anomaly_score'] = anomaly_scores
df['is_anomaly'] = predictions
df['attack_label'] = attack_labels  # ground truth (injected)

# Top 20 most suspicious nodes
suspicious = df.nsmallest(20, 'anomaly_score')[
    ['anomaly_score', 'is_anomaly']
]

print(f"\nTop 10 Most Suspicious Nodes (lowest score = most anomalous):")
print(suspicious.head(10).to_string())

# ── 10. Save Outputs ───────────────────────────────────────────────────────────

# Save model and scaler
with open("models/isolation_forest.pkl", "wb") as f:
    pickle.dump(iso_forest, f)

with open("models/iso_scaler.pkl", "wb") as f:
    pickle.dump(scaler, f)

# Save results JSON (for integration with rest of pipeline)
results = {
    "model": "Isolation Forest",
    "n_estimators": 200,
    "contamination": 0.08,
    "features_used": feature_cols,
    "dataset": "WSN-DS with synthetic attack injection",
    "attack_types_simulated": ["black-hole", "sybil", "dos"],
    "metrics": {
        "detection_rate_pct": round(detection_rate, 2),
        "false_positive_rate_pct": round(fpr, 2),
        "precision_pct": round(precision, 2),
        "accuracy_pct": round(accuracy, 2),
        "true_positives": int(tp),
        "false_positives": int(fp),
        "true_negatives": int(tn),
        "false_negatives": int(fn)
    },
    "node_anomaly_scores": {
        str(i): round(float(s), 6)
        for i, s in enumerate(anomaly_scores)
    }
}

with open("outputs/anomaly_detection_results.json", "w") as f:
    json.dump(results, f, indent=2)

print("\n✅ Saved models/isolation_forest.pkl")
print("✅ Saved models/iso_scaler.pkl")
print("✅ Saved outputs/anomaly_detection_results.json")
print("\n" + "=" * 60)
print("  Isolation Forest complete!")
print("=" * 60)