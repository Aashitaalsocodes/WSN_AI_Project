"""
lstm_determinism_check_v2.py

Fix for lstm_determinism_check.py: TF's threading config can only be set
ONCE, before any op executes -- it can't be changed mid-process after the
context is initialized (that's what crashed Step 2 last time). So this
version can't do "standard settings" and "deterministic settings" in the
same process. Instead: run this script TWICE, using the DETERMINISTIC flag
below, and compare the two separate runs' printed results by eye.

Step 1 (previous script) already confirmed non-determinism under standard
settings (seed=2024 gave 0.000031 vs 0.000038 across two in-process runs --
smaller gap than the earlier 0.097 blowup, but still confirms the seed
alone doesn't fully control reproducibility).

This script tests whether forcing determinism fixes it. Run it TWICE as
separate `py -3.12 lstm_determinism_check_v2.py` invocations (two separate
processes) and compare the single printed test_mse between the two runs.
If they match, determinism is fixed.
"""

import os

os.environ["PYTHONHASHSEED"] = "0"
os.environ["TF_DETERMINISTIC_OPS"] = "1"
os.environ["TF_CUDNN_DETERMINISTIC"] = "1"

import numpy as np
import tensorflow as tf

# Must happen before any op runs -- set once, at the very top, before
# building/loading anything.
tf.config.threading.set_intra_op_parallelism_threads(1)
tf.config.threading.set_inter_op_parallelism_threads(1)
tf.config.experimental.enable_op_determinism()

from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping
from pathlib import Path

DATA_DIR = Path(".")
SEED = 2024
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


def main():
    (X_train, y_train), (X_val, y_val), (X_test, y_test) = load_data()

    tf.random.set_seed(SEED)
    np.random.seed(SEED)

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

    print("=" * 60)
    print(f"DETERMINISTIC RUN (seed={SEED}): test_mse={test_loss[0]:.8f}  test_mae={test_loss[1]:.8f}")
    print("=" * 60)
    print("Run this script again (fresh process) and compare the number above.")
    print("Match (to ~8 decimal places) -> determinism fixed, safe to redo seed sweeps.")
    print("Still different -> deeper nondeterminism source, needs more investigation.")


if __name__ == "__main__":
    main()