import pandas as pd
import numpy as np
import json
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
from pathlib import Path

df = pd.read_csv("data/processed/processed_data.csv")

features = ['energy_remaining', 'energy_decay_rate', 'rolling_energy_avg', 
            'packet_loss_ratio', 'rssi', 'energy_consumed']
for f in features:
    if f not in df.columns:
        df[f] = 0

X = df[features].fillna(0)
y = df['is_faulty'].fillna(0).astype(int)

print(f"Failure class distribution: 0={sum(y==0)}, 1={sum(y==1)}")

if sum(y==1) == 0:
    # No faulty nodes – generate synthetic failure probabilities based on low energy
    print("No faulty samples. Generating synthetic failure probabilities from energy and packet loss.")
    # Nodes with energy < 0.2 or high packet loss are risky
    risk_score = (1 - df['energy_remaining']) * 0.7 + df['packet_loss_ratio'] * 0.3
    probs = risk_score.tolist()
    latest = df.groupby('node_id').last().reset_index()
    probs_latest = risk_score.groupby(df['node_id']).last().values
    high_risk = latest.loc[probs_latest > 0.7, 'node_id'].tolist()
    
    failure_probs = {
        "model": "Random Forest (synthetic fallback)",
        "node_failure_probabilities_24h": probs_latest.tolist(),
        "high_risk_nodes": high_risk,
        "accuracy": 0.0,
        "f1_score": 0.0,
        "note": "No real fault labels; probabilities based on energy and packet loss"
    }
else:
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    model = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    if len(np.unique(y_test)) > 1:
        auc = roc_auc_score(y_test, model.predict_proba(X_test)[:,1])
    else:
        auc = 0.5
    print(f"Accuracy: {acc:.4f}, F1: {f1:.4f}, AUC: {auc:.4f}")
    
    latest = df.groupby('node_id').last().reset_index()
    X_latest = latest[features].fillna(0)
    probs = model.predict_proba(X_latest)[:, 1].tolist()
    high_risk = latest.loc[np.array(probs) > 0.7, 'node_id'].tolist()
    
    failure_probs = {
        "model": "Random Forest",
        "node_failure_probabilities_24h": probs,
        "high_risk_nodes": high_risk,
        "accuracy": float(acc),
        "f1_score": float(f1),
        "roc_auc": float(auc)
    }

output_path = Path("outputs/failure_probs.json")
with open(output_path, "w") as f:
    json.dump(failure_probs, f, indent=2)
print(f"✅ Saved {output_path}")