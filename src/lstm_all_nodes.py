import pandas as pd
import numpy as np
import json
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
from pathlib import Path

# Load full dataset
df = pd.read_csv("data/raw/energy_metrics.csv")

# Use ALL unique nodes
nodes = df['node_id'].unique()
print(f"Training on {len(df)} rows from {len(nodes)} nodes: {list(nodes)}")

# Find the column with 'interval_energy' (case-insensitive)
energy_col = None
for col in df.columns:
    if 'interval_energy' in col.lower():
        energy_col = col
        break

if energy_col is None:
    raise KeyError(f"No 'interval_energy' column found. Available: {list(df.columns)}")

print(f"Using energy column: {energy_col}")

# Normalize the chosen energy column
scaler = MinMaxScaler()
df['energy_norm'] = scaler.fit_transform(df[[energy_col]])

sequence_length = 10
X, y = [], []

for node, group in df.groupby('node_id'):
    values = group['energy_norm'].values
    if len(values) > sequence_length:
        for i in range(len(values) - sequence_length):
            X.append(values[i:i+sequence_length])
            y.append(values[i+sequence_length])

X = np.array(X).reshape(-1, sequence_length, 1)
y = np.array(y)

print(f"Total sequences: {len(X)}")

# Train/validation split
split = int(0.8 * len(X))
X_train, X_val = X[:split], X[split:]
y_train, y_val = y[:split], y[split:]

# Build LSTM (slightly larger)
model = Sequential([
    LSTM(64, activation='relu', input_shape=(sequence_length, 1)),
    Dense(1)
])
model.compile(optimizer='adam', loss='mse')

print("Training on all nodes... (may take several minutes)")
history = model.fit(X_train, y_train, validation_data=(X_val, y_val),
                    epochs=20, batch_size=32, verbose=1)

val_loss = model.evaluate(X_val, y_val, verbose=0)
print(f"Validation MSE: {val_loss:.6f}")

# Forecast for ALL nodes
forecasts = {}
for node, group in df.groupby('node_id'):
    values = group['energy_norm'].values
    if len(values) >= sequence_length:
        last_seq = values[-sequence_length:].reshape(1, sequence_length, 1)
        pred_norm = model.predict(last_seq, verbose=0)[0, 0]
        pred_actual = scaler.inverse_transform([[pred_norm]])[0, 0]
        forecasts[node] = float(pred_actual)
    else:
        # fallback
        forecasts[node] = float(values[-1]) if len(values) > 0 else 50.0

# Save JSON
output_path = Path("outputs/energy_forecast.json")
output_path.parent.mkdir(exist_ok=True)
with open(output_path, "w") as f:
    json.dump({
        "model": "LSTM (trained on all nodes, full dataset)",
        "24h_energy_forecast_mJ": forecasts,
        "val_mse": float(val_loss)
    }, f, indent=2)

print(f"✅ Saved forecasts for {len(forecasts)} nodes to {output_path}")