import pandas as pd
import numpy as np
from pathlib import Path

RAW_PATH = Path("data/raw")
RAW_PATH.mkdir(parents=True, exist_ok=True)

def generate_energy_protocols():
    np.random.seed(42)
    n_nodes = 50
    n_rounds = 1000
    
    data = []
    for node_id in range(n_nodes):
        initial_energy = 1.0
        for round_num in range(n_rounds):
            energy_consumed = np.random.uniform(0.001, 0.005)
            if np.random.rand() < 0.1:
                energy_consumed *= np.random.uniform(1.5, 2.0)
            battery_after = max(0, initial_energy - energy_consumed * (round_num + 1))
            data.append([round_num, f"node_{node_id}", battery_after, energy_consumed])
    
    df = pd.DataFrame(data, columns=["round", "node_id", "battery_level_after", "energy_consumed"])
    df.to_csv(RAW_PATH / "energy_efficient_communication_protocols.csv", index=False)
    print(f"✅ Generated {len(df)} rows for energy protocols dataset")

def generate_node_status():
    np.random.seed(123)
    n_nodes = 50
    n_timesteps = 1000
    
    data = []
    for node_id in range(n_nodes):
        for t in range(n_timesteps):
            battery = max(0, 1.0 - t * 0.0005 + np.random.normal(0, 0.02))
            is_faulty = 1 if (battery < 0.1 or np.random.rand() < 0.05) else 0
            packet_loss = np.clip(np.random.uniform(0, 0.2) + (1 - battery) * 0.3, 0, 0.8)
            rssi = np.random.uniform(-90, -40) - (1 - battery) * 10
            data.append([t, f"node_{node_id}", battery, is_faulty, packet_loss, rssi])
    
    df = pd.DataFrame(data, columns=["timestamp", "node_id", "Battery", "IsFaulty", "packet_loss_ratio", "rssi"])
    df.to_csv(RAW_PATH / "node_status_in_wsn.csv", index=False)
    print(f"✅ Generated {len(df)} rows for node status dataset")

if __name__ == "__main__":
    generate_energy_protocols()
    generate_node_status()
    print("\nSynthetic data generation complete. Files saved in data/raw/")