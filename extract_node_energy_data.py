"""
extract_node_energy_data.py
Extract real per-node energy timeseries from all 5 seed JSONs
and build sliding-window (X, y) samples for LSTM training.
"""
import json
import numpy as np
from pathlib import Path
from collections import defaultdict

OUTPUT_DIR = Path("outputs")
SEEDS = [42, 7, 99, 123, 2024]
WINDOW = 3

TRAIN_SEEDS = [42, 7, 123]
VAL_SEEDS = [99]
TEST_SEEDS = [2024]

def load_node_energy(seed):
    path = OUTPUT_DIR / f"digital_twin_results_packetmodel_seed{seed}.json"
    with open(path, 'r') as f:
        data = json.load(f)

    node_energy = defaultdict(list)
    for round_data in data['rounds']:
        snapshot = round_data['node_energy_snapshot']
        for node_id, energy in snapshot.items():
            node_energy[node_id].append(energy)
    return dict(node_energy)

def build_windows(node_energy_dict):
    X, y = [], []
    for node_id, seq in node_energy_dict.items():
        if len(seq) <= WINDOW:
            continue
        for i in range(WINDOW, len(seq)):
            X.append(seq[i - WINDOW:i])
            y.append(seq[i])
    return X, y

def main():
    splits = {"train": [], "val": [], "test": []}
    splits_y = {"train": [], "val": [], "test": []}

    for seed in SEEDS:
        node_energy = load_node_energy(seed)
        n_nodes = len(node_energy)
        n_rounds = len(next(iter(node_energy.values())))
        print(f"seed {seed}: {n_nodes} nodes, {n_rounds} rounds")

        X, y = build_windows(node_energy)

        if seed in TRAIN_SEEDS:
            key = "train"
        elif seed in VAL_SEEDS:
            key = "val"
        else:
            key = "test"

        splits[key].extend(X)
        splits_y[key].extend(y)

    out_dir = Path("outputs/lstm_training_data")
    out_dir.mkdir(parents=True, exist_ok=True)

    for key in ["train", "val", "test"]:
        X_arr = np.array(splits[key], dtype=np.float32)
        y_arr = np.array(splits_y[key], dtype=np.float32)
        np.save(out_dir / f"X_{key}.npy", X_arr)
        np.save(out_dir / f"y_{key}.npy", y_arr)
        print(f"{key}: {X_arr.shape[0]} samples")

    print(f"\nSaved to {out_dir}/")

if __name__ == "__main__":
    main()