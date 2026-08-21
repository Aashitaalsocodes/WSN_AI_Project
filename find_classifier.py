import os
for root, dirs, files in os.walk("."):
    if "node_modules" in root or ".git" in root:
        continue
    for f in files:
        if f.endswith(".py") and ("classif" in f.lower() or "anomaly" in f.lower() or "isolation" in f.lower() or "attack" in f.lower() or "explain" in f.lower()):
            print(os.path.join(root, f))
