import pandas as pd
import numpy as np
import json
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
import xgboost as xgb
from pathlib import Path

# Load the unified dataset (created by data_pipeline.py)
df = pd.read_csv("data/processed/processed_data.csv")

feature_cols = ['energy_remaining', 'energy_decay_rate', 'rolling_energy_avg', 
                'packet_loss_ratio', 'rssi', 'energy_consumed', 'power_mW',
                'cumulative_energy_mJ', 'interval_energy_mJ', 
                'packets_sent', 'packets_received', 'distance_to_ch',
                'ADV_S', 'ADV_R', 'JOIN_S', 'JOIN_R', 'SCH_S', 'SCH_R',
                'DATA_S', 'DATA_R', 'Data_Sent_To_BS', 'dist_CH_To_BS']
feature_cols = [c for c in feature_cols if c in df.columns]
X = df[feature_cols].fillna(0)
y = df['is_cluster_head'].fillna(0).astype(int)

print(f"Cluster head class distribution: 0={sum(y==0)}, 1={sum(y==1)}")

# Compute scale_pos_weight to handle imbalance
scale_pos_weight = sum(y==0) / sum(y==1) if sum(y==1) > 0 else 1
print(f"Using scale_pos_weight = {scale_pos_weight:.2f}")

# Split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Train with balanced weight
model = xgb.XGBClassifier(
    n_estimators=100,
    max_depth=5,
    learning_rate=0.1,
    scale_pos_weight=scale_pos_weight,
    random_state=42,
    eval_metric='logloss'
)
model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)
# Feature importance
importance = model.feature_importances_
feat_imp = sorted(zip(feature_cols, importance), key=lambda x: x[1], reverse=True)
print("\nTop 10 most important features:")
for f, imp in feat_imp[:10]:
    print(f"  {f}: {imp:.4f}")
# Evaluate
y_pred = model.predict(X_test)
acc = accuracy_score(y_test, y_pred)
f1 = f1_score(y_test, y_pred, zero_division=0)
if len(np.unique(y_test)) > 1:
    auc = roc_auc_score(y_test, model.predict_proba(X_test)[:,1])
else:
    auc = 0.5

print(f"Accuracy: {acc:.4f}, F1: {f1:.4f}, AUC: {auc:.4f}")

# Predict for all nodes (latest timestamp per node)
latest = df.groupby('node_id').last().reset_index()
X_latest = latest[feature_cols].fillna(0)
probs = model.predict_proba(X_latest)[:, 1].tolist()
top_candidates = latest.loc[np.argsort(probs)[-5:], 'node_id'].tolist()

ch_scores = {
    "model": "XGBoost with scale_pos_weight",
    "cluster_head_probabilities": probs,
    "top_candidates": top_candidates,
    "accuracy": float(acc),
    "f1_score": float(f1),
    "roc_auc": float(auc)
}

output_path = Path("outputs/ch_scores.json")
output_path.parent.mkdir(exist_ok=True)
with open(output_path, "w") as f:
    json.dump(ch_scores, f, indent=2)
print(f"✅ Saved {output_path}")