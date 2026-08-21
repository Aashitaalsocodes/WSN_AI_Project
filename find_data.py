import os
import inspect
from trust_engine import TrustEngine

print("=== .csv and .json files in and around this folder ===")
for root, dirs, files in os.walk('.'):
    # skip venv/node_modules/.git noise
    dirs[:] = [d for d in dirs if d not in ('.git', 'node_modules', 'venv', '__pycache__')]
    for f in files:
        if f.endswith('.csv') or f.endswith('.json'):
            print(os.path.join(root, f))

print("\n=== TrustEngine.update_trust source (to see what columns it expects) ===")
print(inspect.getsource(TrustEngine.update_trust))