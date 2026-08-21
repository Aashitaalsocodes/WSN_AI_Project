"""
lstm_edge_arch_sweep.py

Phase 2 of Priority 7 (Lightweight AI for Edge Deployment).

REAL, MEASURED numbers only -- no simulated/fabricated results.

Uses the SAME 3-timestep energy-window data and Sequential(LSTM -> Dense ->
Dense(1)) architecture pattern as train_lstm_dt_energy.py, so this sweep is
an apples-to-apples comparison against the already-trained baseline model
(lstm_dt_energy_model.h5), not a different pipeline.

Data: X_train.npy (30000, 3), X_test.npy (10000, 3), y_train.npy, y_test.npy
  - No separate val split file was provided (only train/test), so a
    validation split is carved out of X_train/y_train here (last 15%,
    NOT shuffled, to mirror the time-ordered nature of energy sequences).
    This differs from the original script, which loaded a pre-made val
    split -- noted explicitly so it isn't mistaken for the same split.

Sweep: 5 configs from the 64/2/16 baseline (2-layer, 64-unit LSTM stack)
down to a very light 8/1/4 (single-layer, 8-unit LSTM) config, each
followed by a Dense(hidden) -> Dense(1, linear) head, matching the
original build_model() head shape.

For each config, real measurements:
  - test MSE / MAE (from model.evaluate, not estimated)
  - desktop inference time (ms/sample), measured with time.perf_counter()
    on a batched, warmed-up, repeated call -- same batching methodology as
    the XGBoost Phase 1 script, since single-row Keras predict() calls are
    dominated by Python/session overhead, not real compute cost
  - model size (KB), from the actual saved .h5 file size on disk -- not a
    parameter-count formula
  - parameter count (trainable params, from model.count_params())

Labeling note: all inference timing here is DESKTOP timing, not edge
hardware. Do not write these numbers into the paper as "edge deployment"
results -- see Phase 4 (desktop-honest interim table) for captioning, and
Phase 6 for real Raspberry Pi numbers once hardware arrives.

Output: outputs/lstm_edge_arch_results.csv
"""

import time
import tempfile
from pathlib import Path

import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
from tensorflow.keras.callbacks import EarlyStopping
import pandas as pd

DATA_DIR = Path(".")
OUTPUT_PATH = Path("outputs/lstm_edge_arch_results.csv")

# (lstm_units, num_lstm_layers, dense_hidden_units) -- baseline down to lightest
CONFIGS = [
    (64, 2, 16),  # baseline, mirrors the "64/2/16" described trade-off point
    (32, 2, 16),
    (32, 1, 16),
    (16, 1, 8),
    (8, 1, 4),
]

SEED = 42


def load_data():
    X_train_full = np.load(DATA_DIR / "X_train.npy")
    y_train_full = np.load(DATA_DIR / "y_train.npy")
    X_test = np.load(DATA_DIR / "X_test.npy")
    y_test = np.load(DATA_DIR / "y_test.npy")

    # Carve a validation split out of the tail of train (time-ordered, not
    # shuffled) since no separate val file was provided.
    n_val = int(0.15 * len(X_train_full))
    X_train, y_train = X_train_full[:-n_val], y_train_full[:-n_val]
    X_val, y_val = X_train_full[-n_val:], y_train_full[-n_val:]

    # reshape to (samples, timesteps, features), matching original script
    X_train = X_train.reshape(X_train.shape[0], X_train.shape[1], 1)
    X_val = X_val.reshape(X_val.shape[0], X_val.shape[1], 1)
    X_test = X_test.reshape(X_test.shape[0], X_test.shape[1], 1)

    return (X_train, y_train), (X_val, y_val), (X_test, y_test)


def build_model(input_shape, lstm_units, num_lstm_layers, dense_units):
    layers = []
    for i in range(num_lstm_layers):
        return_seq = i < num_lstm_layers - 1  # stack: all but last return sequences
        if i == 0:
            layers.append(LSTM(lstm_units, input_shape=input_shape, return_sequences=return_seq))
        else:
            layers.append(LSTM(lstm_units, return_sequences=return_seq))
    layers.append(Dense(dense_units, activation="relu"))
    layers.append(Dense(1, activation="linear"))
    model = Sequential(layers)
    model.compile(optimizer="adam", loss="mse", metrics=["mae"])
    return model


def measure_inference_time_ms(model, X_sample, n_repeats=50, batch_size=1000):
    """
    Real desktop timing, per-sample, batched (same rationale as Phase 1's
    XGBoost timing: single-row predict() calls are swamped by Python/TF
    call overhead, so we batch and divide).
    """
    reps = int(np.ceil(batch_size / len(X_sample)))
    X_batch = np.tile(X_sample, (reps, 1, 1))[:batch_size]

    # warm-up
    _ = model.predict(X_batch, verbose=0)

    times_per_sample = []
    for _ in range(n_repeats):
        start = time.perf_counter()
        _ = model.predict(X_batch, verbose=0)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        times_per_sample.append(elapsed_ms / batch_size)

    return {
        "mean_ms": float(np.mean(times_per_sample)),
        "median_ms": float(np.median(times_per_sample)),
        "std_ms": float(np.std(times_per_sample)),
        "p95_ms": float(np.percentile(times_per_sample, 95)),
    }


def model_size_kb(model):
    """Real saved-file size, not a param-count approximation."""
    with tempfile.NamedTemporaryFile(suffix=".h5", delete=False) as tmp:
        tmp_path = tmp.name
    model.save(tmp_path)
    size_kb = Path(tmp_path).stat().st_size / 1024.0
    Path(tmp_path).unlink()
    return size_kb


def run_sweep():
    tf.random.set_seed(SEED)
    np.random.seed(SEED)

    (X_train, y_train), (X_val, y_val), (X_test, y_test) = load_data()
    print(f"train: {X_train.shape}, val: {X_val.shape}, test: {X_test.shape}")
    print("=" * 60)

    results = []

    for lstm_units, num_layers, dense_units in CONFIGS:
        tf.keras.backend.clear_session()
        tf.random.set_seed(SEED)

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

        timing = measure_inference_time_ms(model, X_test[:1])
        size_kb = model_size_kb(model)
        n_params = model.count_params()

        row = {
            "lstm_units": lstm_units,
            "num_lstm_layers": num_layers,
            "dense_units": dense_units,
            "test_mse": float(test_loss[0]),
            "test_mae": float(test_loss[1]),
            "n_params": int(n_params),
            "model_size_kb": size_kb,
            "desktop_inference_ms_mean": timing["mean_ms"],
            "desktop_inference_ms_median": timing["median_ms"],
            "desktop_inference_ms_std": timing["std_ms"],
            "desktop_inference_ms_p95": timing["p95_ms"],
        }
        results.append(row)

        print(
            f"lstm_units={lstm_units}, layers={num_layers}, dense={dense_units} | "
            f"test_mse={row['test_mse']:.6f} | test_mae={row['test_mae']:.6f} | "
            f"params={n_params} | size={size_kb:.2f}KB | "
            f"desktop_inference_median={row['desktop_inference_ms_median']:.5f}ms/sample"
        )

    df_results = pd.DataFrame(results)
    OUTPUT_PATH.parent.mkdir(exist_ok=True)
    df_results.to_csv(OUTPUT_PATH, index=False)
    print("=" * 60)
    print(f"Saved: {OUTPUT_PATH}")
    print()
    print("REMINDER: desktop_inference_ms_* columns are DESKTOP CPU timing.")
    print("Do not report these as edge/Raspberry Pi results in the paper.")
    return df_results


if __name__ == "__main__":
    run_sweep()