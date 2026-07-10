"""
explain_anomalies_shap.py — Option B: real SHAP values
pip install shap --break-system-packages
"""
import os
import pandas as pd
import numpy as np
import pickle
import json
import shap

FEATURE_COLS = ['ADV_S', 'ADV_R', 'JOIN_S', 'JOIN_R',
                'SCH_S', 'SCH_R', 'DATA_S', 'DATA_R',
                'Data_Sent_To_BS', 'Expaned Energy']


def main(top_n_features=3, per_type_quota=30):
    df = pd.read_csv("data/raw/WSN-DS.csv")
    df.columns = df.columns.str.strip()

    # Sanity check: confirm expected columns exist before doing any real work
    feature_cols = [c for c in FEATURE_COLS if c in df.columns]
    missing = [c for c in FEATURE_COLS if c not in df.columns]
    if missing:
        print(f"WARNING: missing expected feature columns: {missing}")
    if "Attack type" not in df.columns:
        print(f"WARNING: 'Attack type' column not found. Available columns: {df.columns.tolist()}")

    X = df[feature_cols].fillna(df[feature_cols].median())

    with open("models/isolation_forest.pkl", "rb") as f:
        model = pickle.load(f)
    with open("models/iso_scaler.pkl", "rb") as f:
        scaler = pickle.load(f)

    X_scaled = pd.DataFrame(scaler.transform(X), columns=feature_cols)

    raw_preds = model.predict(X_scaled)
    all_flagged_idx = np.where(raw_preds == -1)[0]

    # IMPORTANT: WSN-DS.csv is laid out in contiguous blocks (a run of Normal
    # rows, then a block per attack type), not shuffled. Taking the first
    # N flagged rows in row order (the original "[:max_flagged]" approach)
    # silently biases the whole explanation set toward whichever traffic
    # type happens to appear first in the file -- in practice this produced
    # 200/200 "Normal" explanations and zero attack examples. A first fix
    # (pure random sampling across all flagged rows) solved that but still
    # left minority classes like Grayhole underrepresented, since Normal
    # is the majority class overall.
    #
    # This version instead takes an EQUAL quota per attack type (capped to
    # however many flagged rows actually exist for that type, for rare
    # classes). This gives a balanced, defensible sample for the paper's
    # interpretability section -- every attack type gets fair coverage,
    # including Grayhole, which matters given the known Grayhole/Blackhole
    # confusion elsewhere in the pipeline. Seed 42 matches the convention
    # already used in digital_twin_sim.py for reproducibility.
    rng = np.random.default_rng(42)

    if "Attack type" in df.columns:
        flagged_labels = df["Attack type"].iloc[all_flagged_idx].astype(str).str.strip()
        flagged_idx_list = []
        for label, group in pd.Series(all_flagged_idx, index=flagged_labels.values).groupby(level=0):
            group_vals = group.values
            n = min(per_type_quota, len(group_vals))
            chosen = rng.choice(group_vals, size=n, replace=False)
            flagged_idx_list.append(chosen)
        flagged_idx = np.concatenate(flagged_idx_list)
        flagged_idx.sort()
    else:
        # Fallback if the label column is missing: random sample, no stratification possible
        sample_size = min(per_type_quota * 5, len(all_flagged_idx))
        flagged_idx = rng.choice(all_flagged_idx, size=sample_size, replace=False)
        flagged_idx.sort()

    # TreeExplainer has native IsolationForest support.
    # IMPORTANT sign convention: TreeExplainer explains contributions to
    # model.score_samples(), where sklearn's IsolationForest convention is
    # LOWER (more negative) score = MORE anomalous. That means a positive
    # raw SHAP value pushes the score UP, i.e. LESS anomalous — the opposite
    # of what you'd intuitively expect when reading "contributed to anomaly".
    # We flip the sign here so that in our output, positive always means
    # "pushed toward anomalous" and negative means "pushed toward normal".
    # This matches the same sign-convention bug class already caught once
    # in the Isolation Forest -> TrustEngine scoring path — flipping here
    # keeps the two consistent.
    explainer = shap.TreeExplainer(model)
    raw_shap_values = explainer.shap_values(X_scaled.iloc[flagged_idx])
    shap_values = -1 * np.array(raw_shap_values)

    os.makedirs("outputs", exist_ok=True)

    explanations = []
    for pos, i in enumerate(flagged_idx):
        contribs = pd.Series(shap_values[pos], index=feature_cols)
        top = contribs.abs().sort_values(ascending=False).head(top_n_features)

        reasons = []
        for feat in top.index:
            direction = "toward anomalous" if contribs[feat] > 0 else "toward normal"
            reasons.append(f"{feat} ({contribs[feat]:+.3f}, pushed {direction})")

        raw_label = df.iloc[i].get("Attack type", "unknown")
        attack_type = str(raw_label).strip() if pd.notna(raw_label) else "unknown"

        explanations.append({
            "row_index": int(i),
            "attack_type_ground_truth": attack_type,
            "shap_values": {f: round(float(contribs[f]), 4) for f in feature_cols},
            "top_contributing_features": list(top.index),
            "explanation": "Flagged because: " + "; ".join(reasons)
        })

    output = {
        "method": "shap-tree-explainer",
        "sign_convention": "positive = pushed toward anomalous, negative = pushed toward normal",
        "explanations": explanations
    }

    with open("outputs/anomaly_explanations_shap.json", "w") as f:
        json.dump(output, f, indent=2)

    print(f"Wrote {len(explanations)} SHAP explanations")

    # Quick sanity check: distribution of ground-truth attack types in the
    # sample. If this comes back 100% one type, something's off upstream
    # (e.g. the isolation forest itself, not this script) -- flag it rather
    # than assume the sampling fix alone guarantees a good spread.
    dist = pd.Series([e["attack_type_ground_truth"] for e in explanations]).value_counts()
    print("Attack type distribution in sample:")
    print(dist.to_string())


if __name__ == "__main__":
    main()