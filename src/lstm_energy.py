import pandas as pd
import numpy as np
import json
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
from pathlib import Path

df = pd.read_csv("data/processed/processed_data.csv")

# Use energy_remaining as target
energy_series = df.groupby('node_id')['energy_remaining'].apply(list).to_dict()

# Prepare sequences
sequence_length = 10
X, y = [], []
for node_id, values in energy_series.items():
    if len(values) > sequence_length:
        for i in range(len(values) - sequence_length):
            X.append(values[i:i+sequence_length])
            y.append(values[i+sequence_length])

X = np.array(X).reshape(-1, sequence_length, 1)
y = np.array(y)

# Train/test split
split = int(0.8 * len(X))
X_train, X_test = X[:split], X[split:]
y_train, y_test = y[:split], y[split:]

print(f"Training LSTM on {len(X_train)} sequences...")
model = Sequential([
    LSTM(50, activation='relu', input_shape=(sequence_length, 1)),
    Dense(1)
])
model.compile(optimizer='adam', loss='mse')
model.fit(X_train, y_train, epochs=20, batch_size=32, verbose=1)

# Evaluate
loss = model.evaluate(X_test, y_test, verbose=0)
print(f"Test MSE: {loss:.6f}")

# Forecast next energy for each node (using last 10 timesteps)
forecasts = {}
for node_id, values in energy_series.items():
    if len(values) >= sequence_length:
        last_seq = np.array(values[-sequence_length:]).reshape(1, sequence_length, 1)
        pred = model.predict(last_seq, verbose=0)[0, 0]
        forecasts[node_id] = float(pred)
    else:
        forecasts[node_id] = float(values[-1]) if values else 0.5

energy_forecast = {
    "model": "LSTM",
    "24h_energy_forecast": forecasts,
    "test_mse": float(loss)
}

output_path = Path("outputs/energy_forecast.json")
with open(output_path, "w") as f:
    json.dump(energy_forecast, f, indent=2)
print(f"✅ Saved {output_path}")