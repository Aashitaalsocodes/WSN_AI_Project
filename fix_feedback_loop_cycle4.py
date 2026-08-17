import shutil

path = "feedback_loop.py"
backup = path + ".bak_cycle4"
shutil.copy(path, backup)

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old = """    "Normal": 0.0, "TDMA": 0.1354, "Flooding": 0.2, "Grayhole": 0.4, "Blackhole": 0.6"""
new = """    "Normal": 0.0, "TDMA": 0.1354, "Flooding": 0.15, "Grayhole": 0.35, "Blackhole": 0.5938"""

assert old in content, "Expected cycle-3 block not found - aborting, check file manually."
assert content.count(old) == 1, "Pattern found more than once - aborting to avoid ambiguous edit."

content = content.replace(old, new)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("feedback_loop.py updated to cycle-4 values. Backup saved as", backup)
