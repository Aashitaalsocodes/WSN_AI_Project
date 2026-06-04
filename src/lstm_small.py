import pandas as pd
import numpy as np
import json
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
from pathlib import Path

# Load data
df = pd.read_csv("data/raw/energy_metrics.csv")

# Take only first 5 unique nodes for small training
nodes = df['node_id'].unique()[:5]
df = df[df['node_id'].isin(nodes)]
print(f"Training on {len(df)} rows from nodes: {list(nodes)}")

# Find the column with 'interval_energy' (case-insensitive)
energy_col = None
for col in df.columns:
    if 'interval_energy' in col.lower():
        energy_col = col
        break

if energy_col is None:
    raise KeyError("No column containing 'interval_energy' found. Available columns: " + str(list(df.columns)))

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

# Build smaller LSTM model
model = Sequential([
    LSTM(32, activation='relu', input_shape=(sequence_length, 1)),
    Dense(1)
])
model.compile(optimizer='adam', loss='mse')

print("Training...")
history = model.fit(X_train, y_train, validation_data=(X_val, y_val),
                    epochs=10, batch_size=16, verbose=1)

val_loss = model.evaluate(X_val, y_val, verbose=0)
print(f"Validation MSE: {val_loss:.6f}")

# Forecast for the same nodes (using last sequence)
forecasts = {}
for node, group in df.groupby('node_id'):
    values = group['energy_norm'].values
    if len(values) >= sequence_length:
        last_seq = values[-sequence_length:].reshape(1, sequence_length, 1)
        pred_norm = model.predict(last_seq, verbose=0)[0, 0]
        pred_actual = scaler.inverse_transform([[pred_norm]])[0, 0]
        forecasts[node] = float(pred_actual)
    else:
        forecasts[node] = 0.0

# Save JSON output
output_path = Path("outputs/energy_forecast.json")
output_path.parent.mkdir(exist_ok=True)
with open(output_path, "w") as f:
    json.dump({
        "model": "LSTM (small sample, 5 nodes)",
        "24h_energy_forecast_mJ": forecasts,
        "val_mse": float(val_loss)
    }, f, indent=2)
print(f"✅ Saved {output_path}")