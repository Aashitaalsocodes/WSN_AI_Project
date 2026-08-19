"""
train_lstm_dt_energy.py
Train a small LSTM to predict next-round energy from a 3-round window.
Sized for ~30k samples of scalar sequences — no need for a big stack.
"""
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
from tensorflow.keras.callbacks import EarlyStopping
from pathlib import Path

DATA_DIR = Path("outputs/lstm_training_data")
MODEL_DIR = Path("outputs/lstm_models")

def load_split(name):
    X = np.load(DATA_DIR / f"X_{name}.npy")
    y = np.load(DATA_DIR / f"y_{name}.npy")
    X = X.reshape(X.shape[0], X.shape[1], 1)  # (samples, timesteps, features)
    return X, y

def build_model(input_shape):
    model = Sequential([
        LSTM(16, input_shape=input_shape),
        Dense(8, activation='relu'),
        Dense(1, activation='linear')
    ])
    model.compile(optimizer='adam', loss='mse', metrics=['mae'])
    return model

def main():
    X_train, y_train = load_split("train")
    X_val, y_val = load_split("val")
    X_test, y_test = load_split("test")

    print(f"train: {X_train.shape}, val: {X_val.shape}, test: {X_test.shape}")

    model = build_model((X_train.shape[1], 1))
    model.summary()

    early_stop = EarlyStopping(monitor='val_loss', patience=8, restore_best_weights=True)

    history = model.fit(
        X_train, y_train,
        epochs=50,
        batch_size=128,
        validation_data=(X_val, y_val),
        callbacks=[early_stop],
        verbose=1
    )

    train_loss = model.evaluate(X_train, y_train, verbose=0)
    val_loss = model.evaluate(X_val, y_val, verbose=0)
    test_loss = model.evaluate(X_test, y_test, verbose=0)

    print(f"\nTrain  -> MSE: {train_loss[0]:.6f}, MAE: {train_loss[1]:.6f}")
    print(f"Val    -> MSE: {val_loss[0]:.6f}, MAE: {val_loss[1]:.6f}")
    print(f"Test   -> MSE: {test_loss[0]:.6f}, MAE: {test_loss[1]:.6f}")

    # Compare against a trivial baseline: predict last value = no change
    baseline_pred = X_test[:, -1, 0]
    baseline_mse = np.mean((baseline_pred - y_test) ** 2)
    baseline_mae = np.mean(np.abs(baseline_pred - y_test))
    print(f"\nBaseline (persistence) -> MSE: {baseline_mse:.6f}, MAE: {baseline_mae:.6f}")
    print("(LSTM should beat this baseline meaningfully, or it's not adding value)")

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    model.save(MODEL_DIR / "lstm_dt_energy_model.h5")
    print(f"\nSaved model to {MODEL_DIR / 'lstm_dt_energy_model.h5'}")

if __name__ == "__main__":
    main()