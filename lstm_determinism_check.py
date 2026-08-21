"""
lstm_determinism_check.py

PURPOSE:
lstm_8_1_4_diagnose.py revealed that the SAME seed, SAME architecture, SAME
code path produced wildly different results across two separate script runs
(seed=2024: 0.097 in one run, 0.000041 in another). That means
tf.random.set_seed() alone is NOT making these runs reproducible -- there is
run-to-run nondeterminism happening below the seed layer, almost certainly
from multi-threaded CPU ops (oneDNN/Eigen thread-pool reductions are not
bit-deterministic by default, regardless of the seed).

This matters because every "multi-seed" comparison so far (lstm_multiseed_check.py,
lstm_8_1_4_diagnose.py) implicitly assumed that fixing the seed fixes the run.
If that's false, the reported "spread across seeds" is contaminated by this
extra, unaccounted-for noise source, and any "config A beats config B" or
"config A is unstable" conclusion drawn from those numbers isn't trustworthy
yet.

WHAT THIS SCRIPT DOES:
  1. Runs the SAME (8, 1, 4) architecture with the SAME seed (2024 -- the
     seed that showed the worst inconsistency) TWICE IN A ROW, in the same
     process, with standard (non-deterministic) TF settings, and reports
     both results. If they differ, that CONFIRMS non-determinism outside
     of what the seed controls.
  2. Sets the standard determinism flags (PYTHONHASHSEED, TF_DETERMINISTIC_OPS,
     single-threaded intra/inter-op parallelism, tf.config.experimental.enable_op_determinism)
     and repeats the same seed=2024 run TWICE IN A ROW. If these two runs now
     match exactly (or to floating-point precision), determinism is fixed and
     it's safe to redo the seed sweeps and trust the spread.

NOTE: the determinism flags must be set before TensorFlow does any GPU/CPU
op dispatch, ideally before importing tensorflow at all -- that's why the
os.environ calls are at the very top of this file, before the tensorflow
import.

Output: printed comparison only (this is a diagnostic, not a results table).
"""

import os

# These MUST be set before `import tensorflow` for full effect.
os.environ["PYTHONHASHSEED"] = "0"
os.environ["TF_DETERMINISTIC_OPS"] = "1"
os.environ["TF_CUDNN_DETERMINISTIC"] = "1"

import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping
from pathlib import Path

DATA_DIR = Path(".")
SEED = 2024  # the seed that previously gave contradictory results
LSTM_UNITS, NUM_LAYERS, DENSE_UNITS = 8, 1, 4


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


def build_model(input_shape):
    model = Sequential([
        LSTM(LSTM_UNITS, input_shape=input_shape),
        Dense(DENSE_UNITS, activation="relu"),
        Dense(1, activation="linear"),
    ])
    model.compile(optimizer=Adam(), loss="mse", metrics=["mae"])
    return model


def run_once(X_train, y_train, X_val, y_val, X_test, y_test, seed, force_single_thread=False):
    tf.keras.backend.clear_session()

    if force_single_thread:
        tf.config.threading.set_intra_op_parallelism_threads(1)
        tf.config.threading.set_inter_op_parallelism_threads(1)
        tf.config.experimental.enable_op_determinism()

    tf.random.set_seed(seed)
    np.random.seed(seed)

    model = build_model((X_train.shape[1], 1))
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
    return float(test_loss[0]), float(test_loss[1])


def main():
    (X_train, y_train), (X_val, y_val), (X_test, y_test) = load_data()

    print("=" * 70)
    print(f"STEP 1: standard (non-deterministic) settings, seed={SEED}, run TWICE")
    print("=" * 70)
    mse_a, mae_a = run_once(X_train, y_train, X_val, y_val, X_test, y_test, SEED, force_single_thread=False)
    print(f"  Run 1: test_mse={mse_a:.6f}, test_mae={mae_a:.6f}")
    mse_b, mae_b = run_once(X_train, y_train, X_val, y_val, X_test, y_test, SEED, force_single_thread=False)
    print(f"  Run 2: test_mse={mse_b:.6f}, test_mae={mae_b:.6f}")
    if abs(mse_a - mse_b) < 1e-9:
        print("  -> IDENTICAL. (Unexpected given prior evidence -- rerun a few more times to confirm.)")
    else:
        print(f"  -> DIFFERENT (delta={abs(mse_a - mse_b):.6f}). Confirms non-determinism under standard settings.")

    print()
    print("=" * 70)
    print(f"STEP 2: forced determinism settings, seed={SEED}, run TWICE")
    print("=" * 70)
    mse_c, mae_c = run_once(X_train, y_train, X_val, y_val, X_test, y_test, SEED, force_single_thread=True)
    print(f"  Run 1: test_mse={mse_c:.6f}, test_mae={mae_c:.6f}")
    mse_d, mae_d = run_once(X_train, y_train, X_val, y_val, X_test, y_test, SEED, force_single_thread=True)
    print(f"  Run 2: test_mse={mse_d:.6f}, test_mae={mae_d:.6f}")
    if abs(mse_c - mse_d) < 1e-9:
        print("  -> IDENTICAL. Determinism is fixed -- safe to redo the seed sweeps now.")
    else:
        print(f"  -> STILL DIFFERENT (delta={abs(mse_c - mse_d):.6f}). Determinism flags did not fully fix it;")
        print("     further investigation needed (e.g. GPU nondeterminism, or a source outside TF/numpy seeding).")

    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Standard settings : run1={mse_a:.6f}  run2={mse_b:.6f}  match={abs(mse_a-mse_b) < 1e-9}")
    print(f"Deterministic     : run1={mse_c:.6f}  run2={mse_d:.6f}  match={abs(mse_c-mse_d) < 1e-9}")


if __name__ == "__main__":
    main()