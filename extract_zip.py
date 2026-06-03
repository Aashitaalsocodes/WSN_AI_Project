import zipfile
import os
from pathlib import Path

downloads = Path("C:/Users/Aashita/Downloads")
extract_to = downloads / "extracted"
extract_to.mkdir(exist_ok=True)

zip_files = list(downloads.glob("*.zip"))
print(f"Found {len(zip_files)} zip files")

for zip_path in zip_files:
    print(f"Extracting: {zip_path.name} ...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    print(f"  Done.")

print(f"\nAll files extracted to: {extract_to}")