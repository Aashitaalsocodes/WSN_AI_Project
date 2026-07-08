"""
stub_classifier_output.py
==========================
Simulates the attack classifier's output schema: {node_id, attack_type, confidence}

This is a STUB standing in for Person B's real classifier (task 2), so that
task 3 (mitigation strategy) can be built and tested in parallel without
waiting on her model.

Uses REAL ground-truth attack_type labels from processed_data.csv as the
base signal (not random), with injected noise/confidence calibration that
roughly mirrors the real classifier's already-validated performance
(~98.7% accuracy, occasional misses concentrated on TDMA — see
outputs/risk_validation_report.json).

IMPORTANT: This is a placeholder. Once Person B's real classifier output
is available in the same schema, just point mitigation_engine.py at that
file instead of this stub's output — no logic changes needed.

Usage:
    python stub_classifier_output.py
    python stub_classifier_output.py --noise 0.05
"""

import json
import sys
import numpy as np
import pandas as pd
from pathlib import Path

BASE_DIR   = Path(__file__).parent
DATA_PATH  = BASE_DIR / "data" / "processed" / "processed_data.csv"
OUT_PATH   = BASE_DIR / "outputs" / "stub_classifier_predictions.json"

ATTACK_TYPES = ["Normal", "Blackhole", "Grayhole", "Flooding", "TDMA"]

# Per-type miss rates, loosely modeled on validated pipeline performance:
# Flooding/Grayhole/Blackhole were caught near-perfectly; TDMA had the
# weakest recall (~89.8%) in the earlier validation run.
MISS_RATE = {
    "Normal":    0.012,  # ~1.2% of Normal nodes get false-flagged (matches earlier FP rate)
    "Blackhole": 0.0,
    "Grayhole":  0.0,
    "Flooding":  0.0,
    "TDMA":      0.10,
}


def simulate_predictions(df, noise_seed=42):
    rng = np.random.default_rng(noise_seed)
    n = len(df)

    true_labels = df["attack_type"].values
    predicted_labels = true_labels.copy()
    confidences = np.zeros(n)

    for i, true_label in enumerate(true_labels):
        miss_rate = MISS_RATE.get(true_label, 0.05)
        is_miss = rng.random() < miss_rate

        if is_miss:
            # Misclassify: pick a different label (simulate confusion)
            other_labels = [t for t in ATTACK_TYPES if t != true_label]
            predicted_labels[i] = rng.choice(other_labels)
            # Misclassifications tend to have lower confidence
            confidences[i] = float(np.clip(rng.normal(0.55, 0.12), 0.30, 0.85))
        else:
            predicted_labels[i] = true_label
            # Correct predictions have higher, tighter confidence
            confidences[i] = float(np.clip(rng.normal(0.92, 0.06), 0.60, 0.999))

    return predicted_labels, confidences


def main(noise_seed=42):
    print(f"Loading ground-truth labels from {DATA_PATH}...")
    df = pd.read_csv(DATA_PATH, usecols=["attack_type"])
    total = len(df)
    print(f"  {total:,} rows loaded")
    print(f"  True distribution: {df['attack_type'].value_counts().to_dict()}")

    print(f"\nSimulating classifier predictions (seed={noise_seed})...")
    predicted_labels, confidences = simulate_predictions(df, noise_seed)

    predictions = {}
    for idx in range(total):
        predictions[str(idx)] = {
            "node_id": str(idx),
            "attack_type": str(predicted_labels[idx]),
            "confidence": round(float(confidences[idx]), 4),
        }

    OUT_PATH.parent.mkdir(exist_ok=True)
    with open(OUT_PATH, "w") as f:
        json.dump(predictions, f)

    pred_series = pd.Series(predicted_labels)
    print(f"\nPredicted distribution: {pred_series.value_counts().to_dict()}")

    accuracy = float((predicted_labels == df["attack_type"].values).mean())
    print(f"Simulated accuracy vs ground truth: {accuracy:.4f}")

    size_mb = OUT_PATH.stat().st_size / (1024 * 1024)
    print(f"\nWrote {total:,} predictions to {OUT_PATH} ({size_mb:.1f} MB)")
    print("\nSchema (per node):")
    print(json.dumps(predictions["0"], indent=2))
    print("\nNOTE: This is a STUB. Replace with Person B's real classifier output")
    print("      once available, keeping the same {node_id, attack_type, confidence} schema.")


if __name__ == "__main__":
    seed = 42
    if "--noise" in sys.argv:
        # kept for interface compatibility; seed used instead of a direct noise param
        idx = sys.argv.index("--noise")
        seed = int(float(sys.argv[idx + 1]) * 1000)
    main(noise_seed=seed)