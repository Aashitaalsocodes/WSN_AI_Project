import pandas as pd
import numpy as np
import json
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
import xgboost as xgb
from pathlib import Path

# Load the unified dataset
df = pd.read_csv("data/processed/processed_data.csv")

# Determine the correct distance-to-base-station column
dist_col = None
for col in df.columns:
    col_lower = col.lower()
    if ('dist' in col_lower and ('bs' in col_lower or 'base' in col_lower)):
        dist_col = col
        break
if dist_col is None:
    # Fallback: if no exact match, try any column with 'dist' (excluding distance_to_ch)
    candidates = [c for c in df.columns if 'dist' in c.lower() and 'ch' not in c.lower()]
    dist_col = candidates[0] if candidates else None
if dist_col is None:
    print("Warning: No distance-to-base-station column found. Using zeros.")
    df['distance_to_bs'] = 0
    dist_col = 'distance_to_bs'

# Pre-election features only
feature_cols = ['energy_remaining', 'energy_decay_rate', 'rolling_energy_avg', dist_col]
# Ensure all exist; fill missing with 0
for col in feature_cols:
    if col not in df.columns:
        df[col] = 0

X = df[feature_cols].fillna(0)
y = df['is_cluster_head'].fillna(0).astype(int)

print(f"Cluster head class distribution: 0={sum(y==0)}, 1={sum(y==1)}")
print(f"Using features: {feature_cols}")

# Split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Train without scale_pos_weight (to see baseline) – you can add it if needed
model = xgb.XGBClassifier(
    n_estimators=100,
    max_depth=5,
    learning_rate=0.1,
    random_state=42,
    eval_metric='logloss'
)
model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)

# Evaluate
y_pred = model.predict(X_test)
acc = accuracy_score(y_test, y_pred)
f1 = f1_score(y_test, y_pred, zero_division=0)
if len(np.unique(y_test)) > 1:
    auc = roc_auc_score(y_test, model.predict_proba(X_test)[:, 1])
else:
    auc = 0.5

print(f"Accuracy: {acc:.4f}, F1: {f1:.4f}, AUC: {auc:.4f}")

# Feature importance
importance = model.feature_importances_
feat_imp = sorted(zip(feature_cols, importance), key=lambda x: x[1], reverse=True)
print("\nFeature importances:")
for f, imp in feat_imp:
    print(f"  {f}: {imp:.4f}")

# Predict for all nodes (latest timestamp per node)
latest = df.groupby('node_id').last().reset_index()
X_latest = latest[feature_cols].fillna(0)
probs = model.predict_proba(X_latest)[:, 1].tolist()
top_candidates = latest.loc[np.argsort(probs)[-5:], 'node_id'].tolist()

ch_scores = {
    "model": "XGBoost (non‑leaky, pre‑election features only)",
    "cluster_head_probabilities": probs,
    "top_candidates": top_candidates,
    "accuracy": float(acc),
    "f1_score": float(f1),
    "roc_auc": float(auc),
    "features_used": feature_cols
}

output_path = Path("outputs/ch_scores_nonleaky.json")
output_path.parent.mkdir(exist_ok=True)
with open(output_path, "w") as f:
    json.dump(ch_scores, f, indent=2)
print(f"✅ Saved {output_path}")