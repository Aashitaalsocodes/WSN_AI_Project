import zipfile
import os
from pathlib import Path

downloads = Path("C:/Users/Aashita/Downloads")
extract_dir = downloads / "extracted"
extract_dir.mkdir(exist_ok=True)

zip_files = list(downloads.glob("*.zip"))
print(f"Found {len(zip_files)} zip files to extract")

for zip_path in zip_files:
    print(f"Extracting: {zip_path.name} ...")
    with zipfile.ZipFile(zip_path, 'r') as zf:
        zf.extractall(extract_dir)
    print(f"  Done.")

print(f"\nAll files extracted to: {extract_dir}")