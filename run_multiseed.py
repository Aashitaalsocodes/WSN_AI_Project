"""
run_multiseed.py

Runs hybrid_xgb_lstm_detector.py multiple times across configs (time_frac x
seq_len) and torch seeds, in-process (no subprocess spawning, no shell loop
syntax to worry about on Windows), and aggregates mean +/- std for each
metric -- including per-class recall, so you can specifically check whether
the LSTM's Blackhole gain (0.41 baseline) is real or noise.

USAGE (same directory, same venv):
    python run_multiseed.py --csv data\\raw\\WSN-DS.csv

Defaults to the two configs discussed:
    (time_frac=0.7, seq_len=10)   -- your original run
    (time_frac=0.5, seq_len=5)    -- brings Flooding into the test set
each run 3 times with torch_seed in {42, 43, 44}.

Takes a while: 2 configs x 3 seeds x ~15 epochs each on CPU. Reduce
--seeds-per-config or --epochs if you want a faster first pass.
"""

import argparse
import json
import os
import statistics as stats

import hybrid_xgb_lstm_detector as hx


DEFAULT_CONFIGS = [
    {"time_frac": 0.7, "seq_len": 10},
    {"time_frac": 0.5, "seq_len": 5},
]


def make_args(csv_path, time_frac, seq_len, torch_seed, epochs, xgb_model_path, results_path, ensemble_mode="stacking"):
    # Namespace matching hybrid_xgb_lstm_detector's expected args directly --
    # equivalent to what argparse would produce from the CLI flags.
    return argparse.Namespace(
        csv=csv_path,
        node_col=None,
        time_col=None,
        seq_len=seq_len,
        xgb_weight=hx.XGB_WEIGHT,
        lstm_weight=hx.LSTM_WEIGHT,
        epochs=epochs,
        xgb_model_path=xgb_model_path,
        split_mode="time",
        time_frac=time_frac,
        node_frac=0.8,
        val_frac=0.15,
        torch_seed=torch_seed,
        results_path=results_path,
        ensemble_mode="stacking",
    )


def summarize(values):
    if len(values) == 1:
        return {"mean": values[0], "std": 0.0, "n": 1}
    return {"mean": stats.mean(values), "std": stats.stdev(values), "n": len(values)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--seeds-per-config", type=int, default=3)
    ap.add_argument("--epochs", type=int, default=15)
    ap.add_argument("--out-dir", default="hybrid_xgb_lstm_outputs/multiseed")
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    seeds = [42 + i for i in range(args.seeds_per_config)]

    all_runs = []  # list of (config, seed, results_dict)

    for cfg in DEFAULT_CONFIGS:
        # XGBoost only depends on the time split, not the torch seed, so cache
        # per-config (not per-seed) to avoid retraining it 3x for nothing.
        xgb_model_path = os.path.join(
            args.out_dir, f"xgb_tf{cfg['time_frac']}_sl{cfg['seq_len']}.pkl"
        )
        for seed in seeds:
            print(f"\n{'#'*70}\n# CONFIG time_frac={cfg['time_frac']} seq_len={cfg['seq_len']} "
                  f"torch_seed={seed}\n{'#'*70}")
            results_path = os.path.join(
                args.out_dir, f"results_tf{cfg['time_frac']}_sl{cfg['seq_len']}_seed{seed}.json"
            )
            run_args = make_args(
                args.csv, cfg["time_frac"], cfg["seq_len"], seed, args.epochs,
                xgb_model_path, results_path,
            )
            results = hx.run_once(run_args)
            all_runs.append((cfg, seed, results))

    # --- Aggregate per config ---
    print("\n\n" + "=" * 78)
    print("MULTI-SEED SUMMARY")
    print("=" * 78)

    summary_out = {}
    for cfg in DEFAULT_CONFIGS:
        key = f"time_frac={cfg['time_frac']}_seq_len={cfg['seq_len']}"
        runs_for_cfg = [r for c, s, r in all_runs if c == cfg]
        if not runs_for_cfg:
            continue

        print(f"\n--- {key} ({len(runs_for_cfg)} seeds) ---")
        cfg_summary = {}
        for model_name in ["xgb_only", "lstm_only", "hybrid"]:
            recall_macro_vals = [r[model_name]["recall_macro"] for r in runs_for_cfg]
            per_round_vals = [r[model_name]["per_round_pooled_recall"] for r in runs_for_cfg]
            blackhole_vals = [
                r[model_name]["recall_per_class"].get("Blackhole", float("nan")) for r in runs_for_cfg
            ]
            cfg_summary[model_name] = {
                "recall_macro": summarize(recall_macro_vals),
                "per_round_pooled_recall": summarize(per_round_vals),
                "blackhole_recall": summarize(blackhole_vals),
            }
            rm = cfg_summary[model_name]["recall_macro"]
            pr = cfg_summary[model_name]["per_round_pooled_recall"]
            bh = cfg_summary[model_name]["blackhole_recall"]
            print(f"  {model_name:10s}  recall_macro={rm['mean']:.4f}+/-{rm['std']:.4f}   "
                  f"per_round={pr['mean']:.4f}+/-{pr['std']:.4f}   "
                  f"blackhole={bh['mean']:.4f}+/-{bh['std']:.4f}")

        # Delta hybrid - xgb, computed per-seed then averaged, not mean-of-means -
        # this matches the pairing (same split, same seed) so it isolates the
        # ensemble's effect rather than mixing in split variance.
        deltas_macro = [r["hybrid"]["recall_macro"] - r["xgb_only"]["recall_macro"] for r in runs_for_cfg]
        deltas_blackhole = [
            r["hybrid"]["recall_per_class"].get("Blackhole", float("nan"))
            - r["xgb_only"]["recall_per_class"].get("Blackhole", float("nan"))
            for r in runs_for_cfg
        ]
        cfg_summary["delta_hybrid_minus_xgb"] = {
            "recall_macro": summarize(deltas_macro),
            "blackhole_recall": summarize(deltas_blackhole),
        }
        dm = cfg_summary["delta_hybrid_minus_xgb"]["recall_macro"]
        db = cfg_summary["delta_hybrid_minus_xgb"]["blackhole_recall"]
        print(f"  DELTA (hybrid - xgb)  recall_macro={dm['mean']:+.4f}+/-{dm['std']:.4f}   "
              f"blackhole={db['mean']:+.4f}+/-{db['std']:.4f}")
        if dm["std"] > 0 and abs(dm["mean"]) < dm["std"]:
            print("  -> macro-recall delta is smaller than its own std dev across seeds: "
                  "treat as noise, not a real effect, at this seed count.")
        if db["std"] > 0 and abs(db["mean"]) < db["std"]:
            print("  -> blackhole delta is smaller than its own std dev across seeds: "
                  "treat as noise, not a real effect, at this seed count.")

        summary_out[key] = cfg_summary

    summary_path = os.path.join(args.out_dir, "multiseed_summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary_out, f, indent=2)
    print(f"\n[done] full summary written to {summary_path}")
    print("\nReminder: 3 seeds gives you a rough signal, not a confidence interval you'd "
          "want to defend in a review. If a delta looks promising here, rerun with "
          "--seeds-per-config 5 before it goes in the paper.")


if __name__ == "__main__":
    main()