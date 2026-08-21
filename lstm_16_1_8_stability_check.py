"""
lstm_16_1_8_stability_check.py

PURPOSE:
The 8/1/4 LSTM config was found to be genuinely unstable (bimodal: converges
well ~0.00004 MSE or gets stuck ~0.097 MSE, confirmed even under forced TF
determinism -- see lstm_determinism_check_v2.py). 16/1/8 is the next
candidate up in size from the original Phase 2 sweep (1,297 params vs 361
for 8/1/4, 48.30 KB vs 38.30 KB) and was stable in that single Phase 2 run.
This checks whether it's ACTUALLY stable across multiple seeds, using the
same forced-determinism setup and the same seed set as the 8/1/4 checks,
so results are directly comparable.

REAL, MEASURED numbers only -- no simulated/fabricated results.

Also reruns the 64/2/16 baseline under the SAME forced-determinism settings
(previous baseline numbers were measured WITHOUT determinism forced, so
they aren't a fully apples-to-apples comparison point until redone here).

Determinism flags are set at the top, before any TF op runs (lesson from
the crash in lstm_determinism_check.py v1) -- this means threading config
can't be changed later in the same process, so this script forces
determinism for its entire run, for both configs.

SEEDS: same 5 as used throughout (42, 1, 7, 123, 2024) for direct
comparability with the earlier 8/1/4 numbers.

Output: outputs/lstm_16_1_8_stability_results.csv
"""

import os

os.environ["PYTHONHASHSEED"] = "0"
os.environ["TF_DETERMINISTIC_OPS"] = "1"
os.environ["TF_CUDNN_DETERMINISTIC"] = "1"

import numpy as np
import tensorflow as tf

tf.config.threading.set_intra_op_parallelism_threads(1)
tf.config.threading.set_inter_op_parallelism_threads(1)
tf.config.experimental.enable_op_determinism()

from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping
import pandas as pd
from pathlib import Path

DATA_DIR = Path(".")
OUTPUT_PATH = Path("outputs/lstm_16_1_8_stability_results.csv")

# (lstm_units, num_lstm_layers, dense_units, label)
CONFIGS = [
    (64, 2, 16, "baseline_64_2_16"),
    (16, 1, 8, "candidate_16_1_8"),
]

SEEDS = [42, 1, 7, 123, 2024]


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
    model.compile(optimizer=Adam(), loss="mse", metrics=["mae"])
    return model


def run_check():
    (X_train, y_train), (X_val, y_val), (X_test, y_test) = load_data()
    print(f"train: {X_train.shape}, val: {X_val.shape}, test: {X_test.shape}")
    print("Forced determinism: single-threaded ops, enable_op_determinism() ON")
    print("=" * 70)

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
            test_loss = model.evaluate(X_test, y_test, verbose=0)

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

    print("=" * 70)
    print("Summary (mean +/- std, min, max across seeds):")
    summary = df_results.groupby("config_label")["test_mse"].agg(["mean", "std", "min", "max"])
    print(summary)
    print()
    print(f"Saved: {OUTPUT_PATH}")
    print()
    print("READ THIS: look at 'max' for candidate_16_1_8. If max stays in the same")
    print("ballpark as baseline (no seed blowing up to ~0.01-0.1 like 8/1/4 did),")
    print("16/1/8 is a stable, defensible 'lightweight' recommendation. If any seed")
    print("blows up, this config isn't safe to recommend either and 32/1/16 (the")
    print("next size up from Phase 2) should be checked instead.")
    return df_results


if __name__ == "__main__":
    run_check()