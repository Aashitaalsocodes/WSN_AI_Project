import pandas as pd

df = pd.read_csv('data/processed/processed_data.csv', 
                 usecols=['node_id', 'distance_to_ch', 'is_cluster_head', 'packets_sent', 'packets_received'])

print('Total rows:', len(df))
print('Unique nodes:', df['node_id'].nunique())
print('Sample node_ids:', df['node_id'].unique()[:5].tolist())
print('distance_to_ch range:', df['distance_to_ch'].min(), '-', df['distance_to_ch'].max())
print('Rows per node (mean):', round(len(df) / df['node_id'].nunique(), 1))
print('Rows per node (sample):')
print(df['node_id'].value_counts().head(5))