import pandas as pd
import numpy as np
import json
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
import xgboost as xgb
from pathlib import Path

# ------------------------------------------------------------
# 1. Load raw WSN-DS dataset
# ------------------------------------------------------------
df = pd.read_csv("data/raw/WSN-DS.csv")
df.columns = df.columns.str.strip()

# ------------------------------------------------------------
# 2. Identify columns
# ------------------------------------------------------------
energy_col = None
dist_bs_col = None
node_id_col = None
round_col = None
target_col = None

for col in df.columns:
    col_lower = col.lower()
    if 'energy' in col_lower and 'expanded' not in col_lower:
        energy_col = col
    if 'dist' in col_lower and 'bs' in col_lower:
        dist_bs_col = col
    if col_lower == 'id':
        node_id_col = col
    if 'round' in col_lower or 'time' in col_lower:
        round_col = col
    if col_lower in ['is_ch', 'isch', 'cluster_head', 'is_cluster_head']:
        target_col = col

if energy_col is None:
    raise KeyError("No energy column found")
if dist_bs_col is None:
    raise KeyError("No distance-to-BS column found")
if target_col is None:
    raise KeyError("No cluster head label column found")

# ------------------------------------------------------------
# 3. Build feature matrix (pre‑election only)
# ------------------------------------------------------------
X = pd.DataFrame()
X['energy_remaining'] = df[energy_col]
X['distance_to_bs'] = df[dist_bs_col]

# Add node_id as categorical (if useful) – convert to integer codes
if node_id_col is not None:
    X['node_id_code'] = df[node_id_col].astype('category').cat.codes

# Add round number if available (helps with temporal patterns)
if round_col is not None:
    X['round'] = df[round_col]

# Simple engineered feature: energy * distance (interaction)
X['energy_dist_interaction'] = X['energy_remaining'] * X['distance_to_bs']

# Fill missing values
X = X.fillna(0)

y = df[target_col].astype(int)

print(f"Class distribution: 0={sum(y==0)}, 1={sum(y==1)}")
print(f"Features: {list(X.columns)}")

# ------------------------------------------------------------
# 4. Train / test split
# ------------------------------------------------------------
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# ------------------------------------------------------------
# 5. Compute scale_pos_weight
# ------------------------------------------------------------
scale_pos_weight = (sum(y_train==0) / sum(y_train==1)) if sum(y_train==1) > 0 else 1
print(f"Using scale_pos_weight = {scale_pos_weight:.2f}")

# ------------------------------------------------------------
# 6. Train XGBoost with balancing
# ------------------------------------------------------------
model = xgb.XGBClassifier(
    n_estimators=200,
    max_depth=4,
    learning_rate=0.05,
    scale_pos_weight=scale_pos_weight,
    random_state=42,
    eval_metric='logloss'
)
model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)

# ------------------------------------------------------------
# 7. Evaluate
# ------------------------------------------------------------
y_pred = model.predict(X_test)
acc = accuracy_score(y_test, y_pred)
f1 = f1_score(y_test, y_pred, zero_division=0)
if len(np.unique(y_test)) > 1:
    auc = roc_auc_score(y_test, model.predict_proba(X_test)[:,1])
else:
    auc = 0.5

print(f"Accuracy: {acc:.4f}, F1: {f1:.4f}, AUC: {auc:.4f}")

# ------------------------------------------------------------
# 8. Feature importance
# ------------------------------------------------------------
importance = model.feature_importances_
feat_imp = sorted(zip(X.columns, importance), key=lambda x: x[1], reverse=True)
print("\nFeature importances:")
for f, imp in feat_imp:
    print(f"  {f}: {imp:.4f}")

# ------------------------------------------------------------
# 9. Predict for each unique node (using latest round if available)
# ------------------------------------------------------------
if round_col is not None:
    # Take the last round per node
    latest_idx = df.groupby(node_id_col)[round_col].idxmax() if node_id_col else df.index
    X_latest = X.loc[latest_idx]
else:
    # Otherwise, take mean per node
    if node_id_col is not None:
        node_means = X.groupby(df[node_id_col]).mean()
        X_latest = node_means
    else:
        X_latest = X

probs = model.predict_proba(X_latest)[:, 1].tolist()
if node_id_col is not None:
    nodes = X_latest.index.tolist() if hasattr(X_latest, 'index') else df[node_id_col].unique().tolist()
else:
    nodes = [f"node_{i}" for i in range(len(probs))]

ch_scores = {
    "model": "XGBoost with class balancing and non‑leaky features",
    "cluster_head_probabilities": dict(zip(nodes, probs)),
    "accuracy": float(acc),
    "f1_score": float(f1),
    "roc_auc": float(auc),
    "features_used": list(X.columns),
    "scale_pos_weight": float(scale_pos_weight)
}

output_path = Path("outputs/ch_scores_balanced.json")
output_path.parent.mkdir(exist_ok=True)
with open(output_path, "w") as f:
    json.dump(ch_scores, f, indent=2)
print(f"✅ Saved {output_path}")