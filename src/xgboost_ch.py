import pandas as pd
import numpy as np
import json
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
import xgboost as xgb
from pathlib import Path

df = pd.read_csv("data/processed/processed_data.csv")

features = ['energy_remaining', 'energy_decay_rate', 'rolling_energy_avg', 
            'packet_loss_ratio', 'rssi', 'energy_consumed']
for f in features:
    if f not in df.columns:
        df[f] = 0

X = df[features].fillna(0)
y = df['is_cluster_head'].fillna(0).astype(int)

# Check class distribution
print(f"Class distribution: 0={sum(y==0)}, 1={sum(y==1)}")

if sum(y==1) == 0:
    # No positive examples – generate synthetic probabilities based on energy
    print("No cluster head samples found. Generating synthetic CH probabilities from energy levels.")
    probs = (df['energy_remaining'] / df['energy_remaining'].max()).tolist()
    ch_scores = {
        "model": "XGBoost (synthetic fallback)",
        "cluster_head_probabilities": probs,
        "top_candidates": df.groupby('node_id')['energy_remaining'].mean().nlargest(5).index.tolist(),
        "accuracy": 0.0,
        "f1_score": 0.0,
        "note": "No real cluster head labels; probabilities based on energy"
    }
else:
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    model = xgb.XGBClassifier(n_estimators=100, max_depth=5, learning_rate=0.1, random_state=42)
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    auc = roc_auc_score(y_test, model.predict_proba(X_test)[:,1]) if len(np.unique(y_test))>1 else 0.5
    
    # Predict for all nodes (latest timestamp)
    latest = df.groupby('node_id').last().reset_index()
    X_latest = latest[features].fillna(0)
    probs = model.predict_proba(X_latest)[:, 1].tolist()
    
    ch_scores = {
        "model": "XGBoost",
        "cluster_head_probabilities": probs,
        "top_candidates": latest.loc[np.argsort(probs)[-5:], 'node_id'].tolist(),
        "accuracy": float(acc),
        "f1_score": float(f1),
        "roc_auc": float(auc)
    }
    print(f"Accuracy: {acc:.4f}, F1: {f1:.4f}, AUC: {auc:.4f}")

output_path = Path("outputs/ch_scores.json")
with open(output_path, "w") as f:
    json.dump(ch_scores, f, indent=2)
print(f"✅ Saved {output_path}")