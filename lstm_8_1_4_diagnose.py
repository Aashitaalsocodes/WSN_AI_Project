"""
lstm_8_1_4_diagnose.py

Follow-up to lstm_multiseed_check.py.

PURPOSE:
The 8/1/4 LSTM config (8 units, 1 layer, 4 dense) was unstable across seeds:
4/5 seeds landed at MSE ~0.03-0.04 (worse than the 64/2/16 baseline's
~0.00006), and seed=2024 diverged outright to MSE=0.097. This script digs
into WHY, rather than just reporting "it's worse" -- a tiny single-LSTM-unit
model failing to train is a common, fixable issue (vanishing/exploding
gradients, patience cutting training off before the loss actually settles,
or genuine insufficient capacity), and which of those it is changes what we
report in the paper.

REAL, MEASURED numbers only -- no simulated/fabricated results.

What this does, for the SAME 8/1/4 architecture:
  (a) Logs the full per-epoch train/val loss curve (not just the final
      number) for a few seeds, including the seed=2024 failure case, so we
      can SEE whether it diverges early, plateaus high, or trains fine and
      then EarlyStopping's restore_best_weights grabs a bad epoch.
  (b) Reruns the same seeds with a longer patience (20 instead of 8) and a
      lower learning rate (1e-3 -> 3e-4 via explicit Adam optimizer), which
      are the two most common fixes for small-RNN instability.
  (c) Reruns with gradient clipping (clipnorm=1.0) added to Adam, which
      directly targets exploding-gradient-style divergence like seed=2024.

Each variant is measured independently -- this is a diagnosis, not a
replacement sweep. Whichever fix (if any) stabilizes the model becomes the
candidate for a proper re-run of the full multi-seed comparison.

Output: outputs/lstm_8_1_4_diagnostic_results.csv (final metrics per variant/seed)
        outputs/lstm_8_1_4_loss_curves.csv (per-epoch curves for the default variant)
"""

import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping
import pandas as pd
from pathlib import Path

DATA_DIR = Path(".")
OUT_METRICS = Path("outputs/lstm_8_1_4_diagnostic_results.csv")
OUT_CURVES = Path("outputs/lstm_8_1_4_loss_curves.csv")

LSTM_UNITS, NUM_LAYERS, DENSE_UNITS = 8, 1, 4
SEEDS = [42, 1, 7, 123, 2024]  # same seeds as the multiseed check, incl. the failure case


def load_data():
    X_train_full = np.load(DATA_DIR / "X_train.npy")
    y_train_full = np.load(DATA_DIR / "y_train.npy")
    X_test = np.load(DATA_DIR / "X_test.npy")
    y_test = np.load(DATA_DIR / "y_test.npy")

    n_val = int(0.15 * len(X_train_full))
    X_train, y_train = X_train_full[:-n_val], y_train_full[:-n_val]
    X_val, y_val = X_train_full[-n_val:], y_train_full[-n_val:]

    X_train = X_train.reshape(X_train.shape[0], X_train.shape[1], 1)
    X_val = X_val.reshape(X_val.shape[0], X_val.shape[1], 1)
    X_test = X_test.reshape(X_test.shape[0], X_test.shape[1], 1)

    return (X_train, y_train), (X_val, y_val), (X_test, y_test)


def build_model(input_shape, optimizer):
    model = Sequential([
        LSTM(LSTM_UNITS, input_shape=input_shape),
        Dense(DENSE_UNITS, activation="relu"),
        Dense(1, activation="linear"),
    ])
    model.compile(optimizer=optimizer, loss="mse", metrics=["mae"])
    return model


VARIANTS = {
    # label: (optimizer_factory, patience, epochs)
    "default_adam_patience8": (lambda: Adam(), 8, 50),
    "longer_patience20": (lambda: Adam(), 20, 80),
    "lower_lr_3e4": (lambda: Adam(learning_rate=3e-4), 20, 80),
    "grad_clip_norm1": (lambda: Adam(clipnorm=1.0), 20, 80),
    "lower_lr_and_clip": (lambda: Adam(learning_rate=3e-4, clipnorm=1.0), 20, 80),
}


def run_diagnosis():
    (X_train, y_train), (X_val, y_val), (X_test, y_test) = load_data()
    print(f"train: {X_train.shape}, val: {X_val.shape}, test: {X_test.shape}")
    print(f"Architecture under test: LSTM({LSTM_UNITS}) -> Dense({DENSE_UNITS}) -> Dense(1)")
    print("=" * 70)

    metric_rows = []
    curve_rows = []

    for variant_label, (opt_factory, patience, epochs) in VARIANTS.items():
        print(f"\n--- Variant: {variant_label} (patience={patience}, epochs={epochs}) ---")
        for seed in SEEDS:
            tf.keras.backend.clear_session()
            tf.random.set_seed(seed)
            np.random.seed(seed)

            model = build_model((X_train.shape[1], 1), opt_factory())
            early_stop = EarlyStopping(monitor="val_loss", patience=patience, restore_best_weights=True)

            history = model.fit(
                X_train, y_train,
                epochs=epochs,
                batch_size=128,
                validation_data=(X_val, y_val),
                callbacks=[early_stop],
                verbose=0,
            )

            test_loss = model.evaluate(X_test, y_test, verbose=0)
            stopped_epoch = early_stop.stopped_epoch if early_stop.stopped_epoch > 0 else len(history.history["loss"])
            best_val = min(history.history["val_loss"])

            row = {
                "variant": variant_label,
                "seed": seed,
                "test_mse": float(test_loss[0]),
                "test_mae": float(test_loss[1]),
                "epochs_run": len(history.history["loss"]),
                "stopped_epoch": int(stopped_epoch),
                "best_val_loss": float(best_val),
                "final_train_loss": float(history.history["loss"][-1]),
            }
            metric_rows.append(row)

            # Save full per-epoch curve only for the default variant (for plotting/inspection),
            # to keep the output file size sane -- this is the one that showed instability.
            if variant_label == "default_adam_patience8":
                for epoch_idx, (tr_loss, val_loss) in enumerate(
                    zip(history.history["loss"], history.history["val_loss"])
                ):
                    curve_rows.append({
                        "seed": seed,
                        "epoch": epoch_idx,
                        "train_loss": float(tr_loss),
                        "val_loss": float(val_loss),
                    })

            print(
                f"  seed={seed} | test_mse={row['test_mse']:.6f} | "
                f"epochs_run={row['epochs_run']} | best_val_loss={row['best_val_loss']:.6f}"
            )

    df_metrics = pd.DataFrame(metric_rows)
    df_curves = pd.DataFrame(curve_rows)

    OUT_METRICS.parent.mkdir(exist_ok=True)
    df_metrics.to_csv(OUT_METRICS, index=False)
    df_curves.to_csv(OUT_CURVES, index=False)

    print("\n" + "=" * 70)
    print("Summary (mean +/- std test_mse across seeds, per variant):")
    summary = df_metrics.groupby("variant")["test_mse"].agg(["mean", "std", "min", "max"])
    print(summary)
    print()
    print(f"Saved: {OUT_METRICS}")
    print(f"Saved per-epoch curves (default variant only): {OUT_CURVES}")
    print()
    print("READ THIS: compare 'default_adam_patience8' against the other variants.")
    print("- If longer_patience20 alone fixes it -> Phase 2/multiseed cut training short.")
    print("- If grad_clip_norm1 alone fixes it -> seed=2024-style failures were exploding gradients.")
    print("- If lower_lr fixes it -> the default LR was too aggressive for this small a model.")
    print("- If NOTHING fixes it (all variants still >> baseline's ~0.00006 MSE) -> genuine")
    print("  capacity shortfall at 8 units; report the tradeoff honestly, don't force this config.")
    return df_metrics, df_curves


if __name__ == "__main__":
    run_diagnosis()