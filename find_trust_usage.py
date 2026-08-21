import os
import re

targets = ['historical_accuracy', 'protocol_compliance', 'neighbor_recommendation',
           'update_trust', 'TrustEngine(']

print("=== Searching .py files for real TrustEngine usage / column construction ===\n")
for root, dirs, files in os.walk('.'):
    dirs[:] = [d for d in dirs if d not in ('.git', 'node_modules', 'venv', 'venv_tf', '__pycache__')]
    for f in files:
        if f.endswith('.py'):
            path = os.path.join(root, f)
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as fh:
                    content = fh.read()
            except Exception:
                continue
            hits = [t for t in targets if t in content]
            if hits:
                print(f"{path}: {hits}")