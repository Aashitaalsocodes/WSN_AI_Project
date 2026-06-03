import pandas as pd
import numpy as np
from pathlib import Path

RAW_PATH = Path("data/raw")
PROCESSED_PATH = Path("data/processed")
PROCESSED_PATH.mkdir(parents=True, exist_ok=True)

def load_wsn_ds():
    df = pd.read_csv(RAW_PATH / "WSN-DS.csv")
    # Strip spaces from column names
    df.columns = df.columns.str.strip()
    print("WSN-DS columns:", list(df.columns))
    
    # Rename the actual columns in your file
    rename_dict = {}
    for col in df.columns:
        if col == 'Expanded Energy':
            rename_dict[col] = 'energy_remaining'
        elif col == 'Is_CH':
            rename_dict[col] = 'is_cluster_head'
        elif 'Dist' in col:
            rename_dict[col] = 'distance_to_bs'
    if rename_dict:
        df = df.rename(columns=rename_dict)
    
    # If energy column still missing, create synthetic (should not happen)
    if 'energy_remaining' not in df.columns:
        print("Warning: creating synthetic energy column")
        df['energy_remaining'] = np.random.uniform(0.1, 1.0, len(df))
    
    if 'is_cluster_head' not in df.columns:
        print("Warning: creating synthetic cluster head column")
        df['is_cluster_head'] = np.random.randint(0, 2, len(df))
    else:
        df['is_cluster_head'] = df['is_cluster_head'].astype(int)
    
    df['timestamp'] = df.index
    df['node_id'] = 'node_' + (df.index % 50).astype(str)
    return df[['timestamp', 'node_id', 'energy_remaining', 'is_cluster_head']]

def load_energy_protocols():
    df = pd.read_csv(RAW_PATH / "energy_efficient_communication_protocols.csv")
    df = df.rename(columns={'round': 'timestamp', 'battery_level_after': 'energy_remaining'})
    return df[['timestamp', 'node_id', 'energy_remaining', 'energy_consumed']]

def load_node_status():
    df = pd.read_csv(RAW_PATH / "node_status_in_wsn.csv")
    df = df.rename(columns={'Battery': 'energy_remaining', 'IsFaulty': 'is_faulty'})
    return df[['timestamp', 'node_id', 'energy_remaining', 'is_faulty', 'packet_loss_ratio', 'rssi']]

def create_unified_dataset():
    print("Loading datasets...")
    df1 = load_wsn_ds()
    df2 = load_energy_protocols()
    df3 = load_node_status()
    
    unified = df1.copy()
    unified['energy_consumed'] = np.nan
    unified['is_faulty'] = 0
    unified['packet_loss_ratio'] = np.nan
    unified['rssi'] = np.nan
    
    if len(df2) > 0:
        node_consumption = df2.groupby('node_id')['energy_consumed'].mean().to_dict()
        unified['energy_consumed'] = unified['node_id'].map(node_consumption).fillna(0.003)
    
    if len(df3) > 0:
        node_fault = df3.groupby('node_id')['is_faulty'].mean().round().to_dict()
        unified['is_faulty'] = unified['node_id'].map(node_fault).fillna(0).astype(int)
        node_packet = df3.groupby('node_id')['packet_loss_ratio'].mean().to_dict()
        unified['packet_loss_ratio'] = unified['node_id'].map(node_packet).fillna(0.05)
        node_rssi = df3.groupby('node_id')['rssi'].mean().to_dict()
        unified['rssi'] = unified['node_id'].map(node_rssi).fillna(-65)
    
    # Feature engineering
    unified['energy_decay_rate'] = unified.groupby('node_id')['energy_remaining'].diff()
    unified['rolling_energy_avg'] = unified.groupby('node_id')['energy_remaining'].transform(
        lambda x: x.rolling(5, min_periods=1).mean()
    )
    
    # Fill NaN values (use bfill() instead of method='bfill')
    unified = unified.bfill().fillna(0)
    
    # Save to CSV only (avoids pyarrow issue)
    unified.to_csv(PROCESSED_PATH / "processed_data.csv", index=False)
    # Optionally save parquet if pyarrow is installed
    try:
        unified.to_parquet(PROCESSED_PATH / "features.parquet", index=False)
        print("Parquet file saved.")
    except:
        print("Parquet skipped (pyarrow not installed). CSV file saved.")
    
    print(f"\n✅ Unified dataset saved: {len(unified)} rows, {len(unified.columns)} columns")
    print(f"Columns: {list(unified.columns)}")
    return unified

if __name__ == "__main__":
    create_unified_dataset()