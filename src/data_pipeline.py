import pandas as pd
import numpy as np
from pathlib import Path

RAW_PATH = Path("data/raw")
PROCESSED_PATH = Path("data/processed")
PROCESSED_PATH.mkdir(parents=True, exist_ok=True)

def load_wsn_fault():
    df = pd.read_csv(RAW_PATH / "WSN-DS_with_faults.csv")
    df.columns = df.columns.str.strip()
    
    rename_map = {
        'Is_CH': 'is_cluster_head',
        'Dist_To_CH': 'distance_to_ch',
        'DATA_S': 'packets_sent',
        'DATA_R': 'packets_received',
        'Attack type': 'attack_type',
        'Expanded Energy': 'energy_remaining_wsn'
    }
    df = df.rename(columns=rename_map)
    df['is_faulty'] = df['is_faulty'].astype(int)
    
    if 'id' in df.columns:
        df['node_id'] = 'node_' + df['id'].astype(str)
    else:
        df['node_id'] = 'node_' + (df.index % 50).astype(str)
    
    df['timestamp'] = df.index
    return df

def load_energy_metrics():
    df = pd.read_csv(RAW_PATH / "energy_metrics.csv")
    df = df.rename(columns={
        'battery_percent': 'energy_remaining',
        'timestamp': 'energy_timestamp',
        'cumulative_energy': 'cumulative_energy_mJ',
        'interval_energy': 'interval_energy_mJ',
        'power_consumption': 'power_mW',
        'packets_sent': 'energy_packets_sent',
        'packets_received': 'energy_packets_received'
    })
    keep = ['energy_timestamp', 'node_id', 'energy_remaining', 'cumulative_energy_mJ', 
            'interval_energy_mJ', 'power_mW', 'energy_packets_sent', 'energy_packets_received']
    return df[keep]

def create_unified_dataset():
    print("Loading datasets...")
    wsn_df = load_wsn_fault()
    print(f"WSN-DS with faults: {len(wsn_df)} rows")
    
    energy_df = load_energy_metrics()
    print(f"Energy metrics: {len(energy_df)} rows")
    
    energy_agg = energy_df.groupby('node_id').agg({
        'energy_remaining': 'mean',
        'cumulative_energy_mJ': 'max',
        'interval_energy_mJ': 'mean',
        'power_mW': 'mean',
        'energy_packets_sent': 'sum',
        'energy_packets_received': 'sum'
    }).reset_index()
    
    wsn_cols = ['node_id', 'timestamp', 'is_cluster_head', 'is_faulty', 'attack_type',
                'packets_sent', 'packets_received', 'distance_to_ch']
    if 'energy_remaining_wsn' in wsn_df.columns:
        wsn_cols.append('energy_remaining_wsn')
    wsn_subset = wsn_df[wsn_cols]
    
    unified = pd.merge(wsn_subset, energy_agg, on='node_id', how='left')
    
    if 'energy_remaining_wsn' in unified.columns:
        unified['energy_remaining'] = unified['energy_remaining'].fillna(unified['energy_remaining_wsn'])
    else:
        unified['energy_remaining'] = unified['energy_remaining'].fillna(50.0)
    
    unified.drop(columns=['energy_remaining_wsn'], errors='ignore', inplace=True)
    
    unified['energy_decay_rate'] = unified.groupby('node_id')['energy_remaining'].diff()
    unified['rolling_energy_avg'] = unified.groupby('node_id')['energy_remaining'].transform(
        lambda x: x.rolling(5, min_periods=1).mean()
    )
    
    unified = unified.bfill().fillna(0)
    
    unified.to_csv(PROCESSED_PATH / "processed_data.csv", index=False)
    print(f"\n✅ Unified dataset saved: {len(unified)} rows, {len(unified.columns)} columns")
    print(f"Columns: {list(unified.columns)}")
    return unified

if __name__ == "__main__":
    create_unified_dataset()