import zipfile
import sys
from pathlib import Path

zip_name = sys.argv[1] if len(sys.argv) > 1 else input("Enter zip filename: ")
zip_path = Path(f"C:/Users/Aashita/Downloads/{zip_name}")
extract_to = Path("C:/Users/Aashita/Downloads/extracted")

if not zip_path.exists():
    print(f"File not found: {zip_path}")
    sys.exit(1)

extract_to.mkdir(exist_ok=True)
print(f"Extracting {zip_path.name} ...")
with zipfile.ZipFile(zip_path, 'r') as zf:
    zf.extractall(extract_to)
print("Done.")