"""
validate_risk_vs_attack.py
===========================
Cross-tabulates composite_risk_score (from preprocessed_nodes.json) against
the true attack_type labels (from processed_data.csv) to check whether high
risk scores actually correspond to real attacks, rather than just matching
in aggregate rate by coincidence.

Usage:
    python validate_risk_vs_attack.py
    python validate_risk_vs_attack.py --threshold 0.5
"""

import json
import sys
import numpy as np
import pandas as pd
from pathlib import Path

BASE_DIR     = Path(__file__).parent
DATA_PATH    = BASE_DIR / "data" / "processed" / "processed_data.csv"
NODES_PATH   = BASE_DIR / "outputs" / "preprocessed_nodes.json"


def main(threshold=0.5):
    print(f"Loading true labels from {DATA_PATH}...")
    df = pd.read_csv(DATA_PATH, usecols=["attack_type"])
    total = len(df)
    print(f"  {total:,} rows loaded")

    print(f"\nLoading preprocessed nodes from {NODES_PATH}...")
    with open(NODES_PATH) as f:
        nodes = json.load(f)
    print(f"  {len(nodes):,} nodes loaded")

    # Align risk scores to row index order
    risk_scores = np.full(total, np.nan)
    for node_key, rec in nodes.items():
        idx = int(node_key)
        if idx < total:
            risk_scores[idx] = rec["composite_risk_score"]

    df["composite_risk_score"] = risk_scores
    df["is_high_risk"] = df["composite_risk_score"] > threshold
    df["is_actual_attack"] = df["attack_type"] != "Normal"

    print("\n" + "=" * 70)
    print(f"CROSS-TAB: is_high_risk (threshold={threshold}) vs attack_type")
    print("=" * 70)
    crosstab = pd.crosstab(df["attack_type"], df["is_high_risk"], margins=True)
    print(crosstab.to_string())

    print("\n" + "=" * 70)
    print("PER-ATTACK-TYPE DETECTION RATE (recall)")
    print("=" * 70)
    for attack_type in df["attack_type"].unique():
        subset = df[df["attack_type"] == attack_type]
        n = len(subset)
        n_flagged = subset["is_high_risk"].sum()
        rate = n_flagged / n * 100 if n > 0 else 0.0
        print(f"  {attack_type:12s}: {n_flagged:6,} / {n:6,} flagged high-risk  ({rate:5.1f}%)")

    print("\n" + "=" * 70)
    print("BINARY CONFUSION MATRIX (attack vs normal, at threshold={:.2f})".format(threshold))
    print("=" * 70)
    tp = int(((df["is_high_risk"]) & (df["is_actual_attack"])).sum())
    fp = int(((df["is_high_risk"]) & (~df["is_actual_attack"])).sum())
    fn = int(((~df["is_high_risk"]) & (df["is_actual_attack"])).sum())
    tn = int(((~df["is_high_risk"]) & (~df["is_actual_attack"])).sum())

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall    = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1        = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    accuracy  = (tp + tn) / total

    print(f"  True Positives  (flagged & actually attacked):     {tp:,}")
    print(f"  False Positives (flagged & actually normal):       {fp:,}")
    print(f"  False Negatives (not flagged & actually attacked): {fn:,}")
    print(f"  True Negatives  (not flagged & actually normal):   {tn:,}")
    print(f"  Precision: {precision:.4f}")
    print(f"  Recall:    {recall:.4f}")
    print(f"  F1 score:  {f1:.4f}")
    print(f"  Accuracy:  {accuracy:.4f}")

    print("\n" + "=" * 70)
    print("RISK SCORE DISTRIBUTION BY ACTUAL LABEL")
    print("=" * 70)
    print(df.groupby("attack_type")["composite_risk_score"].describe().to_string())

    # Save results for citing in the paper
    out_path = BASE_DIR / "outputs" / "risk_validation_report.json"
    report = {
        "threshold": threshold,
        "total_nodes": total,
        "confusion_matrix": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "accuracy": round(accuracy, 4),
        "per_attack_type_detection_rate": {
            attack_type: {
                "n": int((df["attack_type"] == attack_type).sum()),
                "n_flagged": int(df[df["attack_type"] == attack_type]["is_high_risk"].sum()),
                "detection_rate_pct": round(
                    float(df[df["attack_type"] == attack_type]["is_high_risk"].mean() * 100), 2
                ),
            }
            for attack_type in df["attack_type"].unique()
        },
        "risk_score_stats_by_label": json.loads(
            df.groupby("attack_type")["composite_risk_score"].describe().to_json()
        ),
    }
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nSaved validation report to {out_path}")


if __name__ == "__main__":
    threshold = 0.5
    if "--threshold" in sys.argv:
        idx = sys.argv.index("--threshold")
        threshold = float(sys.argv[idx + 1])
    main(threshold=threshold)