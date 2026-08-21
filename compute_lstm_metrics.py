import numpy as np
from tensorflow.keras.models import load_model

model = load_model("outputs/lstm_models/lstm_dt_energy_model.h5", compile=False)

X_test = np.load("outputs/lstm_training_data/X_test.npy")
y_test = np.load("outputs/lstm_training_data/y_test.npy")
X_val = np.load("outputs/lstm_training_data/X_val.npy")
y_val = np.load("outputs/lstm_training_data/y_val.npy")

def mse(y_true, y_pred): return float(np.mean((y_true - y_pred) ** 2))
def mae(y_true, y_pred): return float(np.mean(np.abs(y_true - y_pred)))

pred_test = model.predict(X_test, verbose=0).flatten()
pred_val = model.predict(X_val, verbose=0).flatten()

y_test_flat = y_test.flatten()
y_val_flat = y_val.flatten()

print("=== LSTM Metrics ===")
print(f"Val MSE:  {mse(y_val_flat, pred_val):.6f}")
print(f"Test MSE: {mse(y_test_flat, pred_test):.6f}")
print(f"Test MAE: {mae(y_test_flat, pred_test):.6f}")

persist_pred = X_test[:, -1, 0] if X_test.ndim == 3 else X_test[:, -1]
print("\n=== Persistence Baseline ===")
print(f"Test MSE: {mse(y_test_flat, persist_pred):.6f}")
print(f"Test MAE: {mae(y_test_flat, persist_pred):.6f}")