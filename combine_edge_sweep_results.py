"""
combine_edge_sweep_results.py

Phase 3 of Priority 7 (Lightweight AI for Edge Deployment).

REAL, MEASURED numbers only -- no simulated/fabricated results.

Purpose: take the two sweep outputs already produced by
  - xgboost_edge_prune_sweep.py   -> outputs/xgboost_edge_prune_results.csv
  - lstm_edge_arch_sweep.py       -> outputs/lstm_edge_arch_results.csv
and combine them into ONE comparison table + a short plain-text summary,
so Section VIII / the new lightweight-AI subsection can cite a single
table instead of two separately-shaped CSVs.

This script does NOT re-run any training and does NOT invent numbers.
It only reads the two CSVs that must already exist on disk, reshapes them
into a common schema, and writes:

  outputs/edge_sweep_combined.csv   -- one row per config, both families
  outputs/edge_sweep_summary.txt    -- plain-text "smallest / most accurate /
                                        best size-accuracy tradeoff" summary,
                                        computed directly from the CSV rows

Labeling note (same as Phase 1 / Phase 2): every timing number in the
combined table is DESKTOP CPU timing carried over unchanged from the two
input CSVs. This script does not measure anything itself, so it cannot
fix or launder that label -- it just repeats it loudly in the header,
the column name, and the summary text, so nobody downstream mistakes it
for Raspberry Pi / edge-hardware timing before Phase 6 exists.

Usage:
    python combine_edge_sweep_results.py
"""

from pathlib import Path

import pandas as pd

XGB_PATH = Path("outputs/xgboost_edge_prune_results.csv")
LSTM_PATH = Path("outputs/lstm_edge_arch_results.csv")

OUT_CSV = Path("outputs/edge_sweep_combined.csv")
OUT_SUMMARY = Path("outputs/edge_sweep_summary.txt")


def require_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(
            f"Expected sweep output not found: {path}\n"
            f"Run the corresponding Phase 1/2 sweep script first -- "
            f"this script does not generate results, only combines them."
        )


def load_xgboost(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["model_family"] = "XGBoost"
    df["config_label"] = df.apply(
        lambda r: f"n={int(r['n_estimators'])},depth={int(r['max_depth'])},lr={r['learning_rate']}",
        axis=1,
    )
    # Common schema: accuracy-style metric for ranking = f1_mean (imbalanced task)
    df["primary_metric_name"] = "f1_mean"
    df["primary_metric_value"] = df["f1_mean"]
    df["desktop_inference_ms_median"] = df["desktop_inference_ms_median"]
    df["model_size_kb"] = df["model_size_kb"]
    return df[[
        "model_family", "config_label",
        "primary_metric_name", "primary_metric_value",
        "accuracy_mean", "accuracy_std", "f1_mean", "f1_std",
        "auc_mean", "auc_std",
        "desktop_inference_ms_median", "desktop_inference_ms_p95",
        "model_size_kb",
    ]]


def load_lstm(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["model_family"] = "LSTM"
    df["config_label"] = df.apply(
        lambda r: f"units={int(r['lstm_units'])},layers={int(r['num_lstm_layers'])},dense={int(r['dense_units'])}",
        axis=1,
    )
    # Common schema: for LSTM the task is regression, so lower MSE is better.
    # We still expose it under primary_metric_value but flag the direction
    # explicitly in primary_metric_name so nobody averages F1 and MSE together.
    df["primary_metric_name"] = "test_mse (lower=better)"
    df["primary_metric_value"] = df["test_mse"]
    # Fill classification-only columns with None so the combined CSV has one
    # consistent header -- NOT fabricated zeros, explicit missing values.
    for col in ["accuracy_mean", "accuracy_std", "f1_mean", "f1_std", "auc_mean", "auc_std"]:
        df[col] = None
    return df[[
        "model_family", "config_label",
        "primary_metric_name", "primary_metric_value",
        "accuracy_mean", "accuracy_std", "f1_mean", "f1_std",
        "auc_mean", "auc_std",
        "desktop_inference_ms_median", "desktop_inference_ms_p95",
        "model_size_kb",
    ]]


def build_summary(combined: pd.DataFrame) -> str:
    lines = []
    lines.append("EDGE SWEEP SUMMARY -- DESKTOP CPU TIMING ONLY, NOT EDGE HARDWARE")
    lines.append("(inference numbers below are from a desktop CPU, single-thread; do not")
    lines.append(" caption these as Raspberry Pi / edge-deployment results -- see Phase 6)")
    lines.append("=" * 70)

    for family in combined["model_family"].unique():
        sub = combined[combined["model_family"] == family].copy()
        lines.append(f"\n[{family}]")

        smallest = sub.loc[sub["model_size_kb"].idxmin()]
        lines.append(
            f"  Smallest model:  {smallest['config_label']} "
            f"({smallest['model_size_kb']:.2f} KB, "
            f"{smallest['primary_metric_name']}={smallest['primary_metric_value']:.6f})"
        )

        if family == "XGBoost":
            best = sub.loc[sub["primary_metric_value"].idxmax()]
        else:  # LSTM: lower MSE is better
            best = sub.loc[sub["primary_metric_value"].idxmin()]
        lines.append(
            f"  Best metric:     {best['config_label']} "
            f"({best['primary_metric_name']}={best['primary_metric_value']:.6f}, "
            f"{best['model_size_kb']:.2f} KB)"
        )

        fastest = sub.loc[sub["desktop_inference_ms_median"].idxmin()]
        lines.append(
            f"  Fastest desktop inference: {fastest['config_label']} "
            f"({fastest['desktop_inference_ms_median']:.5f} ms/sample median)"
        )

        if smallest["config_label"] == best["config_label"]:
            lines.append(
                "  NOTE: the smallest config is ALSO the best-metric config for this "
                "family -- real result, worth double-checking with a repeat/multi-seed "
                "run before stating it in the paper as a finding, since each config here "
                "was only trained once (no variance estimate for this family)."
                if family == "LSTM" else
                "  NOTE: the smallest config is ALSO the best-metric config for this "
                "family -- consistent with the 5-fold GroupKFold CV already run for this family."
            )

    lines.append("\n" + "=" * 70)
    lines.append(
        "Caption reminder for the paper: label every number above as measured on a "
        "desktop CPU (single-thread where applicable), NOT the target edge hardware. "
        "Replace with Raspberry Pi numbers once Phase 6 hardware measurements exist."
    )
    return "\n".join(lines)


def run():
    require_file(XGB_PATH)
    require_file(LSTM_PATH)

    xgb_df = load_xgboost(XGB_PATH)
    lstm_df = load_lstm(LSTM_PATH)

    combined = pd.concat([xgb_df, lstm_df], ignore_index=True)

    OUT_CSV.parent.mkdir(exist_ok=True)
    combined.to_csv(OUT_CSV, index=False)

    summary_text = build_summary(combined)
    OUT_SUMMARY.write_text(summary_text)

    print(combined.to_string(index=False))
    print()
    print(summary_text)
    print()
    print(f"Saved: {OUT_CSV}")
    print(f"Saved: {OUT_SUMMARY}")


if __name__ == "__main__":
    run()