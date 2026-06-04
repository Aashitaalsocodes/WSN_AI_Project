import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, confusion_matrix
import json
import pickle
import os

os.makedirs("outputs", exist_ok=True)
os.makedirs("models", exist_ok=True)

print("=" * 60)
print("  Isolation Forest v2 — Using Real WSN-DS Attack Labels")
print("=" * 60)

# ── 1. Load Data ───────────────────────────────────────────────
df = pd.read_csv("data/raw/WSN-DS.csv")

# Strip whitespace from column names
df.columns = df.columns.str.strip()
print(f"\nDataset: {df.shape[0]} rows, {df.shape[1]} columns")

# ── 2. Check Attack type column ────────────────────────────────
print(f"\nAttack type distribution:")
print(df['Attack type'].value_counts())

# Create binary label: 0 = Normal, 1 = Attack
df['is_attack'] = (df['Attack type'].str.strip() != 'Normal').astype(int)
print(f"\nBinary labels:")
print(f"  Normal: {(df['is_attack']==0).sum()}")
print(f"  Attack: {(df['is_attack']==1).sum()}")

# ── 3. Feature Selection ───────────────────────────────────────
# Behavioral features only — no leaky columns
feature_cols = ['ADV_S', 'ADV_R', 'JOIN_S', 'JOIN_R',
                'SCH_S', 'SCH_R', 'DATA_S', 'DATA_R',
                'Data_Sent_To_BS', 'Expaned Energy']

# Keep only columns that exist
feature_cols = [c for c in feature_cols if c in df.columns]
print(f"\nFeatures ({len(feature_cols)}): {feature_cols}")

X = df[feature_cols].copy()
y = df['is_attack'].values

# Handle missing/infinite values
X = X.fillna(X.median())
X = X.replace([np.inf, -np.inf], np.nan).fillna(X.median())

# ── 4. Scale ───────────────────────────────────────────────────
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# ── 5. Train Isolation Forest ──────────────────────────────────
# Set contamination to actual attack proportion
attack_rate = y.mean()
print(f"\nActual attack rate in dataset: {attack_rate:.4f} ({attack_rate*100:.2f}%)")

print("\nTraining Isolation Forest...")
iso_forest = IsolationForest(
    n_estimators=300,
    contamination=float(attack_rate),
    max_samples=min(10000, len(X)),
    random_state=42,
    n_jobs=-1
)

iso_forest.fit(X_scaled)
print("Training complete.")

# ── 6. Predict ─────────────────────────────────────────────────
raw_preds = iso_forest.predict(X_scaled)
anomaly_scores = iso_forest.decision_function(X_scaled)

# -1 = anomaly → 1 (attack), 1 = normal → 0
predictions = np.where(raw_preds == -1, 1, 0)

# ── 7. Evaluate ────────────────────────────────────────────────
print("\n" + "=" * 60)
print("  EVALUATION RESULTS")
print("=" * 60)

print("\nClassification Report:")
print(classification_report(y, predictions,
      target_names=['Normal', 'Attack'], digits=4))

cm = confusion_matrix(y, predictions)
tn, fp, fn, tp = cm.ravel()

detection_rate = tp / (tp + fn) * 100 if (tp + fn) > 0 else 0
fpr           = fp / (fp + tn) * 100 if (fp + tn) > 0 else 0
precision     = tp / (tp + fp) * 100 if (tp + fp) > 0 else 0
accuracy      = (tp + tn) / len(y) * 100

print("Confusion Matrix:")
print(f"  True Negatives  (normal correctly identified): {tn}")
print(f"  False Positives (normal flagged as attack):    {fp}")
print(f"  False Negatives (attacks missed):              {fn}")
print(f"  True Positives  (attacks detected):            {tp}")

print(f"\nKey Metrics:")
print(f"  Attack Detection Rate : {detection_rate:.2f}%")
print(f"  False Positive Rate   : {fpr:.2f}%")
print(f"  Precision             : {precision:.2f}%")
print(f"  Overall Accuracy      : {accuracy:.2f}%")

# ── 8. Per Attack Type Breakdown ───────────────────────────────
print("\nDetection breakdown by attack type:")
df['predicted_attack'] = predictions
for attack in df['Attack type'].str.strip().unique():
    mask = df['Attack type'].str.strip() == attack
    subset = df[mask]
    if len(subset) == 0:
        continue
    detected = subset['predicted_attack'].sum()
    total = len(subset)
    pct = detected / total * 100
    print(f"  {attack:20s}: {detected:6d}/{total:6d} detected ({pct:.1f}%)")

# ── 9. Top suspicious nodes ────────────────────────────────────
df['anomaly_score'] = anomaly_scores
top_suspicious = df.nsmallest(10, 'anomaly_score')[
    ['Attack type', 'anomaly_score', 'predicted_attack']
]
print(f"\nTop 10 Most Suspicious Rows:")
print(top_suspicious.to_string())

# ── 10. Save ───────────────────────────────────────────────────
with open("models/isolation_forest.pkl", "wb") as f:
    pickle.dump(iso_forest, f)

with open("models/iso_scaler.pkl", "wb") as f:
    pickle.dump(scaler, f)

results = {
    "model": "Isolation Forest v2",
    "n_estimators": 300,
    "contamination": round(float(attack_rate), 4),
    "features_used": feature_cols,
    "dataset": "WSN-DS with REAL attack labels",
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
print("  Done!")
print("=" * 60)