import pandas as pd
import numpy as np
from pathlib import Path

RAW_PATH = Path("data/raw")
PROCESSED_PATH = Path("data/processed")
PROCESSED_PATH.mkdir(parents=True, exist_ok=True)

def load_wsn_ds():
    """Load WSN-DS dataset WITH newly created fault labels."""
    df = pd.read_csv(RAW_PATH / "WSN-DS_with_faults.csv")  # Use the new file
    # ... (rest of your renaming logic to make sure column names match)
    # Example: If your file has an 'Energy' column, map it to 'energy_remaining'
    df = df.rename(columns={'Energy': 'energy_remaining'})
    return df

def load_energy_metrics():
    """Load REAL energy data from WSN-MERLIN for LSTM."""
    # Update the path to your actual energy_metrics.csv file
    energy_path = RAW_PATH / "energy_metrics.csv"
    if not energy_path.exists():
        raise FileNotFoundError(f"Energy metrics not found at {energy_path}. Please check the file path.")
    df = pd.read_csv(energy_path)
    # Rename columns to match what your pipeline expects
    # (e.g., 'timestamp', 'node_id', 'energy_remaining')
    return df

def create_unified_dataset():
    # Load the datasets
    wsn_df = load_wsn_ds()
    energy_df = load_energy_metrics()

    # Merge them on common columns like 'node_id' and 'timestamp'
    # This is just an example; you'll need to check the actual column names
    # For example: unified = pd.merge(wsn_df, energy_df, on=['node_id', 'timestamp'], how='inner')
    
    # Feature engineering (same as before)
    # ... (your code to add 'energy_decay_rate', 'rolling_energy_avg')
    
    # Save the unified dataset
    unified.to_csv(PROCESSED_PATH / "processed_data.csv", index=False)
    print(f"Unified dataset saved with {len(unified)} rows.")

if __name__ == "__main__":
    create_unified_dataset()