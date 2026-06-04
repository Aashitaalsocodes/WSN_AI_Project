import gzip
import shutil
import pandas as pd
from pathlib import Path

RAW_PATH = Path("data/raw")
GZ_FILE = RAW_PATH / "data.txt.gz"   # adjust if different

# If not found, try to find any .gz file
if not GZ_FILE.exists():
    gz_files = list(RAW_PATH.glob("*.gz"))
    if gz_files:
        GZ_FILE = gz_files[0]
        print(f"Using archive: {GZ_FILE.name}")
    else:
        raise FileNotFoundError("No .gz file found in data/raw/. Please download IBRL dataset.")

# Extract
print(f"Extracting {GZ_FILE.name} ...")
txt_path = RAW_PATH / "ibrl_data.txt"
with gzip.open(GZ_FILE, 'rb') as f_in:
    with open(txt_path, 'wb') as f_out:
        shutil.copyfileobj(f_in, f_out)
print(f"Extracted to {txt_path}")

# Load the space-separated file (no header)
# Columns: date, time, epoch, moteid, temperature, humidity, light, voltage
df = pd.read_csv(txt_path, sep=r'\s+', header=None,
                 names=['date', 'time', 'epoch', 'moteid', 'temperature', 'humidity', 'light', 'voltage'])

print(f"\nLoaded {len(df)} rows")
print("First 5 rows:")
print(df.head())

print("\nData types:")
print(df.dtypes)

# Combine date and time into a single timestamp column
df['timestamp'] = pd.to_datetime(df['date'] + ' ' + df['time'])
df.drop(columns=['date', 'time'], inplace=True)

print(f"\nNumber of readings per moteid:")
print(df['moteid'].value_counts().sort_index())

# Save a clean CSV for LSTM
csv_path = RAW_PATH / "ibrl_voltage_time_series.csv"
df.to_csv(csv_path, index=False)
print(f"\nSaved CSV version to {csv_path}")