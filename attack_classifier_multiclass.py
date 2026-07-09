"""
attack_classifier_multiclass.py
================================
Task 2 (Person B): Multi-class attack-type classification.

Predicts one of {Normal, Blackhole, Grayhole, Flooding, TDMA} per node/timestep,
replacing the earlier binary is_attacked classifier (attack_classifier.py).

NEW in this version: a drop-ratio feature built from `Data_Sent_To_BS` in the
original WSN-DS.csv raw source (not present in processed_data.csv, not merged
before). This is real recorded data, not an invented proxy:
  - Blackhole nodes forward ~0 packets to the base station (Data_Sent_To_BS == 0
    for every Blackhole row, verified over 10,049 rows)
  - Grayhole nodes forward some packets selectively (median 1, mean ~12.3)
  - Flooding nodes forward more, but noisily (median 13, mean ~32.9)
This directly targets the Blackhole<->Grayhole confusion that was the weakest
part of the earlier version (both attacks otherwise look structurally similar
on the existing feature set).

Row alignment: WSN-DS.csv's `id` column matches processed_data.csv's `node_id`
1:1 after stripping the "node_" prefix (374,661 rows, verified index-for-index,
not just by value -- confirmed via DATA_R == packets_received on row 0 and a
full elementwise check).

Output schema (agreed with Person A / mitigation_engine.py):
    outputs/attack_classification_results.json
    { "<row_index>": {"node_id": <node_id>, "attack_type": <str>, "confidence": <float>} }

To wire into mitigation_engine.py: change its CLASSIFIER_PATH to this file's
output path. No other logic changes needed -- schema matches the stub exactly.

Usage:
    python attack_classifier_multiclass.py
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from sklearn.preprocessing import LabelEncoder
import joblib

BASE_DIR = Path(__file__).parent
PROCESSED_PATH = BASE_DIR / "data" / "processed" / "processed_data.csv"
RAW_PATH = BASE_DIR / "data" / "raw" / "WSN-DS.csv"
MODEL_OUT = BASE_DIR / "models" / "attack_classifier_multiclass.pkl"
LABEL_ENCODER_OUT = BASE_DIR / "models" / "attack_classifier_multiclass_labels.pkl"
PRED_OUT = BASE_DIR / "outputs" / "attack_classification_results.json"
EVAL_OUT = BASE_DIR / "outputs" / "attack_classifier_multiclass_evaluation.json"
TEST_IDX_OUT = BASE_DIR / "outputs" / "attack_classifier_multiclass_test_indices.json"

ATTACK_TYPES = ["Normal", "Blackhole", "Grayhole", "Flooding", "TDMA"]


def load_and_merge():
    print("Loading processed_data.csv...")
    df = pd.read_csv(PROCESSED_PATH)

    print("Loading WSN-DS.csv (raw source) for Data_Sent_To_BS...")
    raw = pd.read_csv(RAW_PATH)
    raw.columns = [c.strip() for c in raw.columns]

    assert len(raw) == len(df), (
        f"Row count mismatch: raw={len(raw)} processed={len(df)} -- "
        "alignment assumption broken, do not proceed blindly."
    )

    # Verify alignment before trusting a positional merge
    raw_ids = raw["id"].astype(str).values
    proc_ids = df["node_id"].str.replace("node_", "", regex=False).values
    mismatches = int((raw_ids != proc_ids).sum())
    assert mismatches == 0, f"{mismatches} node_id mismatches between raw and processed -- alignment broken."
    print(f"  Row alignment verified: {len(df):,} rows, 0 mismatches.")

    df["data_sent_to_bs"] = raw["Data_Sent_To_BS"].values

    # Drop ratio: fraction of received packets NOT forwarded to base station.
    # Guard divide-by-zero (nodes with 0 packets_received): treat as 0 (no
    # evidence of dropping if nothing was received in the first place).
    received = df["packets_received"].replace(0, np.nan)
    df["drop_ratio"] = 1.0 - (df["data_sent_to_bs"] / received)
    df["drop_ratio"] = df["drop_ratio"].fillna(0.0).clip(lower=0.0, upper=1.0)

    return df


def main():
    df = load_and_merge()

    FEATURES = [
        "is_cluster_head", "is_faulty", "packets_sent", "packets_received",
        "distance_to_ch", "energy_remaining", "cumulative_energy_mJ",
        "interval_energy_mJ", "power_mW", "energy_packets_sent",
        "energy_packets_received", "energy_decay_rate", "rolling_energy_avg",
        "data_sent_to_bs", "drop_ratio",
    ]

    le = LabelEncoder()
    le.fit(ATTACK_TYPES)
    y = le.transform(df["attack_type"])
    X = df[FEATURES]

    print(f"\nClass distribution:\n{df['attack_type'].value_counts()}")

    X_train, X_test, y_train, y_test, idx_train, idx_test = train_test_split(
        X, y, df.index, test_size=0.2, random_state=42, stratify=y
    )

    TEST_IDX_OUT.parent.mkdir(exist_ok=True)
    with open(TEST_IDX_OUT, "w") as f:
        json.dump(idx_test.tolist(), f)

    print("\nTraining multi-class XGBoost classifier...")
    model = XGBClassifier(
        n_estimators=300,
        max_depth=7,
        learning_rate=0.08,
        objective="multi:softprob",
        num_class=len(ATTACK_TYPES),
        eval_metric="mlogloss",
        random_state=42,
    )

    # Class-imbalance handling via sample weights (multiclass has no
    # scale_pos_weight equivalent) -- inverse frequency weighting.
    class_counts = pd.Series(y_train).value_counts()
    weight_map = {cls: len(y_train) / (len(class_counts) * cnt) for cls, cnt in class_counts.items()}
    sample_weight = pd.Series(y_train).map(weight_map).values

    model.fit(X_train, y_train, sample_weight=sample_weight)

    print("\nEvaluating...")
    y_pred = model.predict(X_test)

    report = classification_report(
        y_test, y_pred, target_names=le.classes_, output_dict=True, zero_division=0
    )
    print(classification_report(y_test, y_pred, target_names=le.classes_, zero_division=0))

    macro_f1 = f1_score(y_test, y_pred, average="macro")
    weighted_f1 = f1_score(y_test, y_pred, average="weighted")
    print(f"Macro F1: {macro_f1:.4f}  |  Weighted F1: {weighted_f1:.4f}")

    cm = confusion_matrix(y_test, y_pred)
    print("\nConfusion Matrix (rows=true, cols=pred):")
    print(le.classes_.tolist())
    print(cm)

    # Specifically surface the Blackhole/Grayhole confusion this feature targets
    bh_idx = list(le.classes_).index("Blackhole")
    gh_idx = list(le.classes_).index("Grayhole")
    print(f"\nBlackhole predicted as Grayhole: {cm[bh_idx][gh_idx]} / {cm[bh_idx].sum()}")
    print(f"Grayhole predicted as Blackhole: {cm[gh_idx][bh_idx]} / {cm[gh_idx].sum()}")

    MODEL_OUT.parent.mkdir(exist_ok=True)
    joblib.dump(model, MODEL_OUT)
    joblib.dump(le, LABEL_ENCODER_OUT)
    print(f"\nModel saved to {MODEL_OUT}")

    with open(EVAL_OUT, "w") as f:
        json.dump({
            "macro_f1": macro_f1,
            "weighted_f1": weighted_f1,
            "classification_report": report,
            "confusion_matrix": cm.tolist(),
            "labels": le.classes_.tolist(),
            "features_used": FEATURES,
            "test_set_size": len(y_test),
        }, f, indent=2)
    print(f"Evaluation saved to {EVAL_OUT}")

    # Full-dataset predictions in agreed schema
    print("\nGenerating full-dataset predictions...")
    all_probs = model.predict_proba(X)
    all_preds = all_probs.argmax(axis=1)
    all_conf = all_probs.max(axis=1)
    pred_labels = le.inverse_transform(all_preds)

    predictions = {
        str(i): {
            "node_id": df["node_id"].iloc[i],
            "attack_type": str(pred_labels[i]),
            "confidence": round(float(all_conf[i]), 4),
        }
        for i in range(len(df))
    }

    PRED_OUT.parent.mkdir(exist_ok=True)
    with open(PRED_OUT, "w") as f:
        json.dump(predictions, f)
    print(f"Predictions saved to {PRED_OUT} ({len(predictions):,} rows)")
    print("\nSchema sample:")
    print(json.dumps(predictions["0"], indent=2))


if __name__ == "__main__":
    main()
