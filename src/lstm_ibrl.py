import pandas as pd
import numpy as np
import json
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
from pathlib import Path

# Load IBRL voltage time series
df = pd.read_csv("data/raw/ibrl_voltage_time_series.csv")

# Convert timestamp to datetime and sort per node
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values(['moteid', 'timestamp'])

# Use voltage as energy proxy (2.0-3.0 Volts)
target_col = 'voltage'

# Normalize voltage to [0,1] range
scaler = MinMaxScaler()
df['voltage_norm'] = scaler.fit_transform(df[[target_col]])

sequence_length = 10
X, y = [], []

for node, group in df.groupby('moteid'):
    values = group['voltage_norm'].values
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

# Build LSTM
model = Sequential([
    LSTM(64, activation='relu', input_shape=(sequence_length, 1)),
    Dense(1)
])
model.compile(optimizer='adam', loss='mse')

print("Training LSTM on real IBRL voltage data...")
history = model.fit(X_train, y_train, validation_data=(X_val, y_val),
                    epochs=20, batch_size=32, verbose=1)

val_loss = model.evaluate(X_val, y_val, verbose=0)
print(f"Validation MSE: {val_loss:.6f}")

# Forecast next voltage for each node (using last 10 readings)
forecasts = {}
for node, group in df.groupby('moteid'):
    values = group['voltage_norm'].values
    if len(values) >= sequence_length:
        last_seq = values[-sequence_length:].reshape(1, sequence_length, 1)
        pred_norm = model.predict(last_seq, verbose=0)[0, 0]
        pred_voltage = scaler.inverse_transform([[pred_norm]])[0, 0]
        forecasts[int(node)] = float(pred_voltage)
    else:
        forecasts[int(node)] = float(values[-1]) if len(values) > 0 else 2.5

energy_forecast = {
    "model": "LSTM trained on real IBRL sensor data (voltage)",
    "next_voltage_forecast_volts": forecasts,
    "val_mse": float(val_loss),
    "data_source": "Intel Berkeley Research Lab (real sensors)"
}

output_path = Path("outputs/energy_forecast_ibrl.json")
output_path.parent.mkdir(exist_ok=True)
with open(output_path, "w") as f:
    json.dump(energy_forecast, f, indent=2)
print(f"✅ Saved {output_path}")