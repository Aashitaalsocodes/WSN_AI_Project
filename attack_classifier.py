import pandas as pd
import json
import numpy as np
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, f1_score
import joblib
import os

# Load data
print("Loading data...")
df = pd.read_csv('data/processed/processed_data.csv')
labels = json.load(open('outputs/attack_ground_truth.json'))

# Build target column from ground truth labels
df['is_attacked'] = [labels[str(i)]['is_attacked'] for i in range(len(df))]

# Features
FEATURES = [
    'is_cluster_head', 'is_faulty', 'packets_sent', 'packets_received',
    'distance_to_ch', 'energy_remaining', 'cumulative_energy_mJ',
    'interval_energy_mJ', 'power_mW', 'energy_packets_sent',
    'energy_packets_received', 'energy_decay_rate', 'rolling_energy_avg'
]

X = df[FEATURES]
y = df['is_attacked']

print(f"Class distribution: {y.value_counts().to_dict()}")

# Train/test split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

test_indices = X_test.index.tolist()
with open('outputs/attack_classifier_test_indices.json', 'w') as f:
    json.dump(test_indices, f)
print(f"Test set indices saved: {len(test_indices)} rows")

# Train XGBoost
print("Training XGBoost classifier...")
model = XGBClassifier(
    n_estimators=100,
    max_depth=6,
    learning_rate=0.1,
    scale_pos_weight=len(y[y==0]) / len(y[y==1]),
    random_state=42,
    eval_metric='logloss'
)
model.fit(X_train, y_train)

# Evaluate
print("\nEvaluating...")
y_pred = model.predict(X_test)

print("\n=== Classification Report ===")
print(classification_report(y_test, y_pred, target_names=['Normal', 'Attacked']))

f1 = f1_score(y_test, y_pred)
print(f"F1 Score (attacked class): {f1:.4f}")

print("\n=== Confusion Matrix ===")
print(confusion_matrix(y_test, y_pred))

# Save model
os.makedirs("models", exist_ok=True)
joblib.dump(model, 'models/attack_classifier.pkl')
print("\nModel saved to models/attack_classifier.pkl")

# Save predictions (batch - fast)
print("Saving predictions...")
all_probs = model.predict_proba(X)[:, 1]
all_preds = model.predict(X)

predictions = {
    str(i): {
        "predicted_attacked": int(all_preds[i]),
        "attack_probability": float(all_probs[i])
    }
    for i in range(len(df))
}

with open('outputs/attack_classifier_predictions.json', 'w') as f:
    json.dump(predictions, f)
print("Predictions saved to outputs/attack_classifier_predictions.json")