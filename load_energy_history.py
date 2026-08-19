"""
load_energy_history.py - Extract REAL energy history from LSTM training data
"""

import json
import numpy as np
from pathlib import Path
from collections import defaultdict

OUTPUTS = Path("outputs")

def load_energy_history_from_training_data():
    """
    Extract energy history from the LSTM training data.
    The training data contains sliding windows of 3 energy values.
    We can reconstruct the original energy sequence from this.
    """
    
    # Load training data
    X_train = np.load(OUTPUTS / "lstm_training_data" / "X_train.npy")
    y_train = np.load(OUTPUTS / "lstm_training_data" / "y_train.npy")
    
    # X_train shape: (samples, 3, 1) - each sample has 3 time steps
    # y_train: (samples, 1) - the next value
    
    print(f"X_train shape: {X_train.shape}")
    print(f"y_train shape: {y_train.shape}")
    
    # Reconstruct energy sequences per node
    # Each sample: [energy_t-2, energy_t-1, energy_t] -> y = energy_t+1
    
    # We need to group by node ID (which is stored in the index)
    # Since we don't have node IDs in the numpy arrays, we need to 
    # reconstruct from the raw simulation data instead.
    
    print("\nAlternative: Using raw simulation data to build energy history...")
    
    # Use the simulation outputs directly
    from build_energy_history import build_energy_history
    energy_history = build_energy_history()
    
    return energy_history

def build_energy_history_from_simulations():
    """
    Extract energy history DIRECTLY from simulation outputs.
    This gives us per-node energy sequences over 23 rounds.
    """
    SEEDS = [42, 7, 99, 123, 2024]
    node_energy_history = defaultdict(list)
    
    for seed in SEEDS:
        json_path = OUTPUTS / f"digital_twin_results_packetmodel_seed{seed}.json"
        if not json_path.exists():
            print(f"Warning: {json_path} not found")
            continue
        
        with open(json_path) as f:
            data = json.load(f)
        
        # Get node IDs
        if 'rounds' in data and len(data['rounds']) > 0:
            # Try to get node IDs from the first round
            first_round = data['rounds'][0]
            
            # Check if we have per-node energy
            if 'node_energy_snapshot' in first_round:
                node_ids = list(first_round['node_energy_snapshot'].keys())
                print(f"Seed {seed}: Found {len(node_ids)} nodes with per-node energy")
            else:
                # Fallback: use avg_energy for all nodes
                # Generate 500 node IDs
                node_ids = [f"node_{i}" for i in range(500)]
                print(f"Seed {seed}: Using avg_energy for {len(node_ids)} nodes")
            
            # Extract energy per node
            for node_id in node_ids:
                energy_seq = []
                for round_data in data['rounds']:
                    if 'node_energy_snapshot' in round_data:
                        energy = round_data['node_energy_snapshot'].get(node_id, 0.5)
                    else:
                        energy = round_data.get('avg_energy_remaining', 0.5)
                    energy_seq.append(energy)
                node_energy_history[node_id].extend(energy_seq)
    
    # Save to file
    result = dict(node_energy_history)
    with open(OUTPUTS / "node_energy_history.json", "w") as f:
        json.dump(result, f, indent=2)
    
    print(f"\n✅ Saved energy history for {len(result)} nodes")
    if result:
        sample_node = list(result.keys())[0]
        print(f"Sample node {sample_node}: {len(result[sample_node])} energy values")
        print(f"  First 5 values: {result[sample_node][:5]}")
    
    return result

if __name__ == "__main__":
    print("=" * 60)
    print("Building Energy History from Simulations")
    print("=" * 60)
    energy_history = build_energy_history_from_simulations()