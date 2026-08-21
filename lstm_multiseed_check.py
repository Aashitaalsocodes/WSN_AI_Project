"""
lstm_multiseed_check.py

Follow-up to Phase 2 (lstm_edge_arch_sweep.py).

PURPOSE:
Phase 2 ran each of the 5 LSTM configs ONCE (single seed), and the smallest
config (8 units, 1 layer, 4 dense) came out with the BEST test MSE/MAE of
the whole sweep -- better than the 64/2/16 baseline. That's the kind of
surprising, single-run result that could easily just be a lucky
EarlyStopping draw rather than a real effect.

This script reruns ONLY the two configs that matter for that claim --
the baseline (64, 2, 16) and the smallest (8, 1, 4) -- across multiple
seeds, and reports mean +/- std for each, so we can see whether the gap
holds up or falls inside noise.

REAL, MEASURED numbers only -- no simulated/fabricated results.

Data and model-building logic are identical to lstm_edge_arch_sweep.py
(same val split carve-out, same build_model() shape). Only difference:
loop over N_SEEDS per config instead of one run per config, and we only
run the two configs in question (not all 5) to keep runtime down.

Output: outputs/lstm_multiseed_results.csv
  One row per (config, seed) -- raw runs, not pre-averaged -- so you can
  compute mean/std/whatever you need afterward, and so a reviewer (or you,
  six months from now) can see the actual spread, not just a summary stat.
"""

import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
from tensorflow.keras.callbacks import EarlyStopping
import pandas as pd
from pathlib import Path

DATA_DIR = Path(".")
OUTPUT_PATH = Path("outputs/lstm_multiseed_results.csv")

# Only the two configs in question for the "smallest wins" claim.
CONFIGS = [
    (64, 2, 16, "baseline"),
    (8, 1, 4, "smallest"),
]

SEEDS = [42, 1, 7, 123, 2024]  # 5 seeds per config


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


def build_model(input_shape, lstm_units, num_lstm_layers, dense_units):
    layers = []
    for i in range(num_lstm_layers):
        return_seq = i < num_lstm_layers - 1
        if i == 0:
            layers.append(LSTM(lstm_units, input_shape=input_shape, return_sequences=return_seq))
        else:
            layers.append(LSTM(lstm_units, return_sequences=return_seq))
    layers.append(Dense(dense_units, activation="relu"))
    layers.append(Dense(1, activation="linear"))
    model = Sequential(layers)
    model.compile(optimizer="adam", loss="mse", metrics=["mae"])
    return model


def run_multiseed():
    (X_train, y_train), (X_val, y_val), (X_test, y_test) = load_data()
    print(f"train: {X_train.shape}, val: {X_val.shape}, test: {X_test.shape}")
    print("=" * 60)

    results = []

    for lstm_units, num_layers, dense_units, label in CONFIGS:
        for seed in SEEDS:
            tf.keras.backend.clear_session()
            tf.random.set_seed(seed)
            np.random.seed(seed)

            model = build_model((X_train.shape[1], 1), lstm_units, num_layers, dense_units)

            early_stop = EarlyStopping(monitor="val_loss", patience=8, restore_best_weights=True)
            model.fit(
                X_train, y_train,
                epochs=50,
                batch_size=128,
                validation_data=(X_val, y_val),
                callbacks=[early_stop],
                verbose=0,
            )

            test_loss = model.evaluate(X_test, y_test, verbose=0)  # [mse, mae]

            row = {
                "config_label": label,
                "lstm_units": lstm_units,
                "num_lstm_layers": num_layers,
                "dense_units": dense_units,
                "seed": seed,
                "test_mse": float(test_loss[0]),
                "test_mae": float(test_loss[1]),
            }
            results.append(row)

            print(f"[{label}] seed={seed} | test_mse={row['test_mse']:.6f} | test_mae={row['test_mae']:.6f}")

    df_results = pd.DataFrame(results)
    OUTPUT_PATH.parent.mkdir(exist_ok=True)
    df_results.to_csv(OUTPUT_PATH, index=False)

    print("=" * 60)
    print("Summary (mean +/- std across seeds):")
    summary = df_results.groupby("config_label")[["test_mse", "test_mae"]].agg(["mean", "std"])
    print(summary)
    print()
    print(f"Saved raw per-seed results: {OUTPUT_PATH}")
    print()
    print("INTERPRETATION NOTE: if the baseline and smallest config's MSE")
    print("distributions overlap (mean difference is within ~1 std of either),")
    print("do NOT claim 'smallest model wins' in the paper -- report instead")
    print("that MSE was comparable across the size range, which is still a")
    print("legitimate and useful finding for the edge-deployment argument.")
    return df_results


if __name__ == "__main__":
    run_multiseed()