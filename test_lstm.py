import pandas as pd
print("Loading data...")
df = pd.read_csv('data/raw/energy_metrics.csv', nrows=1000)  # only first 1000 rows
print(df.shape)
print("Data loaded. Exiting.")