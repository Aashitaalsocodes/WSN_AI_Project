"""
explain_anomalies_shap.py — Option B: real SHAP values
pip install shap --break-system-packages
"""
import pandas as pd
import numpy as np
import pickle
import json
import shap

FEATURE_COLS = ['ADV_S', 'ADV_R', 'JOIN_S', 'JOIN_R',
                'SCH_S', 'SCH_R', 'DATA_S', 'DATA_R',
                'Data_Sent_To_BS', 'Expaned Energy']

def main(top_n_features=3, max_flagged=200):
    df = pd.read_csv("data/raw/WSN-DS.csv")
    df.columns = df.columns.str.strip()
    feature_cols = [c for c in FEATURE_COLS if c in df.columns]
    X = df[feature_cols].fillna(df[feature_cols].median())

    with open("models/isolation_forest.pkl", "rb") as f:
        model = pickle.load(f)
    with open("models/iso_scaler.pkl", "rb") as f:
        scaler = pickle.load(f)

    X_scaled = pd.DataFrame(scaler.transform(X), columns=feature_cols)

    raw_preds = model.predict(X_scaled)
    flagged_idx = np.where(raw_preds == -1)[0][:max_flagged]  # cap for speed

    # TreeExplainer has native IsolationForest support
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_scaled.iloc[flagged_idx])

    explanations = []
    for pos, i in enumerate(flagged_idx):
        contribs = pd.Series(shap_values[pos], index=feature_cols)
        top = contribs.abs().sort_values(ascending=False).head(top_n_features)
        reasons = [
            f"{feat} contributed {contribs[feat]:+.3f} to anomaly score"
            for feat in top.index
        ]
        explanations.append({
            "row_index": int(i),
            "attack_type_ground_truth": df.iloc[i].get("Attack type", "unknown").strip(),
            "shap_values": {f: round(float(contribs[f]), 4) for f in feature_cols},
            "top_contributing_features": list(top.index),
            "explanation": "Flagged because: " + "; ".join(reasons)
        })

    with open("outputs/anomaly_explanations_shap.json", "w") as f:
        json.dump({"method": "shap-tree-explainer", "explanations": explanations}, f, indent=2)
    print(f"Wrote {len(explanations)} SHAP explanations")

if __name__ == "__main__":
    main()