"""
xgboost_edge_prune_sweep.py

Phase 1 of Priority 7 (Lightweight AI for Edge Deployment).

REAL, MEASURED numbers only -- no simulated/fabricated results.

Built directly on top of the leakage-free CH-prediction fix:
  - Uses WSN-DS_with_faults.csv
  - Uses the SAME lagged features (prior_expended_energy, prior_energy_decay_rate,
    prior_rolling_energy_avg, prior_round_count) -- energy state as of the END of
    the PREVIOUS round, so nothing here can leak this round's CH decision.
  - Uses GroupKFold by round (Time), same as the leakage-free script, so folds
    never share a round. This is NOT a single random train/test split -- it's
    5-fold CV, so accuracy/F1/AUC are reported as mean +/- std across folds,
    matching the rigor of the rest of the project.

Adds vs. the original leakage-free script:
  - scale_pos_weight per fold (class imbalance handling), since CH rate is low
    and the original leakage-free script did not balance classes.
  - A sweep over (n_estimators, max_depth, learning_rate) configs, from the
    original 300/7 baseline down to a very light 50/3 config.
  - Real desktop-measured inference time (ms/sample) and model size (KB),
    both measured with time.time() / actual serialized model size -- not
    estimated or invented.

Output: outputs/xgboost_edge_prune_results.csv
Each row = one config, with mean+/-std across the 5 GroupKFold folds for
accuracy/F1/AUC, plus inference time and model size measured on a model
retrained on ALL usable data (for the timing/size numbers only -- CV metrics
come from the folds, not this final model).

Labeling note: all inference timing here is DESKTOP timing. It is NOT edge
hardware timing. Do not write these numbers into the paper as "edge deployment"
results -- see Phase 4 (desktop-honest interim table) for how to caption them,
and Phase 6 for real Raspberry Pi numbers once hardware arrives.
"""

import time
import json
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import GroupKFold
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score

DATA_PATH = "data/raw/WSN-DS_with_faults.csv"
OUTPUT_PATH = "outputs/xgboost_edge_prune_results.csv"

SAFE_FEATURES = [
    "prior_expended_energy",
    "prior_energy_decay_rate",
    "prior_rolling_energy_avg",
    "prior_round_count",
]

# (n_estimators, max_depth, learning_rate)
CONFIGS = [
    (300, 7, 0.08),  # original baseline (matches earlier project scale)
    (200, 7, 0.08),
    (150, 6, 0.08),
    (100, 5, 0.08),
    (80, 4, 0.08),
    (50, 3, 0.10),
]


def load_and_engineer_features():
    """Same lagged-feature construction as the leakage-free script."""
    df = pd.read_csv(DATA_PATH)
    df.columns = df.columns.str.strip()
    df = df.rename(columns={"Is_CH": "is_cluster_head"})
    df = df.sort_values(["id", "Time"]).reset_index(drop=True)

    grp = df.groupby("id")
    df["prior_expended_energy"] = grp["Expaned Energy"].shift(1)
    df["prior_energy_decay_rate"] = grp["Expaned Energy"].diff().shift(1)
    df["prior_rolling_energy_avg"] = (
        grp["Expaned Energy"].shift(1).rolling(3, min_periods=1).mean()
    )
    df["prior_round_count"] = grp.cumcount()

    clean = df.dropna(subset=SAFE_FEATURES).copy()
    return clean


def measure_inference_time_ms(model, X_sample, n_repeats=200, batch_size=1000):
    """
    Real desktop timing, per-sample. Predicting a single row is so fast that
    Python call overhead / OS scheduling jitter dominates the measurement and
    swamps the actual model compute cost. To get a real signal, we predict on
    a batch of `batch_size` rows (repeating/tiling X_sample as needed) and
    divide by batch_size to get a per-sample time. This is still desktop CPU
    timing, not edge hardware -- label accordingly wherever these numbers
    are used.
    """
    # Build a batch by tiling the sample row(s) up to batch_size.
    reps = int(np.ceil(batch_size / len(X_sample)))
    X_batch = pd.concat([X_sample] * reps, ignore_index=True).iloc[:batch_size]

    # warm-up call (avoids first-call overhead skewing the measurement)
    _ = model.predict(X_batch)

    times_per_sample = []
    for _ in range(n_repeats):
        start = time.perf_counter()
        _ = model.predict(X_batch)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        times_per_sample.append(elapsed_ms / batch_size)

    return {
        "mean_ms": float(np.mean(times_per_sample)),
        "median_ms": float(np.median(times_per_sample)),
        "std_ms": float(np.std(times_per_sample)),
        "p95_ms": float(np.percentile(times_per_sample, 95)),
    }


def model_size_kb(model):
    """Real serialized model size, not an approximation formula."""
    raw = model.get_booster().save_raw()
    return len(raw) / 1024.0


def run_sweep():
    clean = load_and_engineer_features()
    X = clean[SAFE_FEATURES]
    y = clean["is_cluster_head"].astype(int)
    groups = clean["Time"]

    print(f"Usable rows: {len(clean)}")
    print(f"CH rate: {y.mean():.4f}")
    print(f"Features: {SAFE_FEATURES}")
    print("=" * 60)

    gkf = GroupKFold(n_splits=5)
    results = []

    for n_est, depth, lr in CONFIGS:
        fold_acc, fold_f1, fold_auc = [], [], []

        for train_idx, test_idx in gkf.split(X, y, groups):
            X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
            y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

            spw = (
                (y_train == 0).sum() / (y_train == 1).sum()
                if (y_train == 1).sum() > 0
                else 1.0
            )

            fold_model = xgb.XGBClassifier(
                n_estimators=n_est,
                max_depth=depth,
                learning_rate=lr,
                scale_pos_weight=spw,
                random_state=42,
                eval_metric="logloss",
                n_jobs=1,  # single-thread, matches edge-device constraint
            )
            fold_model.fit(X_train, y_train)

            preds = fold_model.predict(X_test)
            proba = fold_model.predict_proba(X_test)[:, 1]

            fold_acc.append(accuracy_score(y_test, preds))
            fold_f1.append(f1_score(y_test, preds, zero_division=0))
            if len(np.unique(y_test)) > 1:
                fold_auc.append(roc_auc_score(y_test, proba))

        # Final model on ALL usable data, for real timing/size measurement only.
        # (CV metrics above are the actual generalization estimate -- this
        # model is NOT what the accuracy numbers refer to.)
        overall_spw = (
            (y == 0).sum() / (y == 1).sum() if (y == 1).sum() > 0 else 1.0
        )
        final_model = xgb.XGBClassifier(
            n_estimators=n_est,
            max_depth=depth,
            learning_rate=lr,
            scale_pos_weight=overall_spw,
            random_state=42,
            eval_metric="logloss",
            n_jobs=1,
        )
        final_model.fit(X, y)

        timing = measure_inference_time_ms(final_model, X.iloc[[0]])
        size_kb = model_size_kb(final_model)

        row = {
            "n_estimators": n_est,
            "max_depth": depth,
            "learning_rate": lr,
            "accuracy_mean": float(np.mean(fold_acc)),
            "accuracy_std": float(np.std(fold_acc)),
            "f1_mean": float(np.mean(fold_f1)),
            "f1_std": float(np.std(fold_f1)),
            "auc_mean": float(np.mean(fold_auc)) if fold_auc else None,
            "auc_std": float(np.std(fold_auc)) if fold_auc else None,
            "desktop_inference_ms_mean": timing["mean_ms"],
            "desktop_inference_ms_median": timing["median_ms"],
            "desktop_inference_ms_std": timing["std_ms"],
            "desktop_inference_ms_p95": timing["p95_ms"],
            "model_size_kb": size_kb,
        }
        results.append(row)

        print(
            f"n={n_est}, depth={depth}, lr={lr} | "
            f"acc={row['accuracy_mean']:.4f}+/-{row['accuracy_std']:.4f} | "
            f"f1={row['f1_mean']:.4f} | "
            f"desktop_inference_median={row['desktop_inference_ms_median']:.5f}ms/sample | "
            f"size={row['model_size_kb']:.2f}KB"
        )

    df_results = pd.DataFrame(results)
    Path("outputs").mkdir(exist_ok=True)
    df_results.to_csv(OUTPUT_PATH, index=False)
    print("=" * 60)
    print(f"Saved: {OUTPUT_PATH}")
    print()
    print("REMINDER: desktop_inference_ms_* columns are DESKTOP CPU timing.")
    print("Do not report these as edge/Raspberry Pi results in the paper.")
    return df_results


if __name__ == "__main__":
    run_sweep()