import gzip
import shutil
import pandas as pd
from pathlib import Path

RAW_PATH = Path("data/raw")
GZ_FILE = RAW_PATH / "data.txt.gz"

if not GZ_FILE.exists():
    gz_files = list(RAW_PATH.glob("*.gz"))
    if gz_files:
        GZ_FILE = gz_files[0]
        print(f"Using archive: {GZ_FILE.name}")
    else:
        raise FileNotFoundError("No .gz file found in data/raw/")

print(f"Extracting {GZ_FILE.name} ...")
txt_path = RAW_PATH / "ibrl_data.txt"
with gzip.open(GZ_FILE, 'rb') as f_in:
    with open(txt_path, 'wb') as f_out:
        shutil.copyfileobj(f_in, f_out)
print(f"Extracted to {txt_path}")

# Parse lines manually
data_rows = []
with open(txt_path, 'r') as f:
    for line in f:
        parts = line.strip().split()
        if len(parts) >= 8:
            date = parts[0]
            time = parts[1]
            epoch = int(parts[2])
            moteid = int(parts[3])
            temperature = float(parts[4])
            humidity = float(parts[5])
            light = float(parts[6])
            voltage = float(parts[7])
            data_rows.append([date, time, epoch, moteid, temperature, humidity, light, voltage])

df = pd.DataFrame(data_rows, columns=['date', 'time', 'epoch', 'moteid', 'temperature', 'humidity', 'light', 'voltage'])
print(f"\nLoaded {len(df)} rows")

# Combine date and time, then convert to datetime with mixed format (handles both with and without microseconds)
df['datetime_str'] = df['date'] + ' ' + df['time']
df['timestamp'] = pd.to_datetime(df['datetime_str'], format='mixed', errors='coerce')
df.drop(columns=['date', 'time', 'datetime_str'], inplace=True)

if df['timestamp'].isna().any():
    print(f"Warning: {df['timestamp'].isna().sum()} rows could not be parsed (will be dropped)")
    df = df.dropna(subset=['timestamp'])

print("\nFirst 5 rows:")
print(df.head())

print("\nNumber of readings per moteid:")
print(df['moteid'].value_counts().sort_index())

# Save clean CSV
csv_path = RAW_PATH / "ibrl_voltage_time_series.csv"
df.to_csv(csv_path, index=False)
print(f"\nSaved CSV version to {csv_path}")