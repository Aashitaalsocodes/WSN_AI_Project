import shutil

path = "build_recalibration_report.py"
backup = path + ".bak_cycle6"
shutil.copy(path, backup)

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old = """    "TDMA": 0.1354, "Flooding": 0.1, "Grayhole": 0.3, "Blackhole": 0.5938,"""
new = """    "TDMA": 0.1354, "Flooding": 0.05, "Grayhole": 0.2969, "Blackhole": 0.5938,"""

assert old in content, "Expected cycle-5 block not found - aborting."
assert content.count(old) == 1, "Pattern found more than once - aborting."
content = content.replace(old, new)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("build_recalibration_report.py updated to cycle-6 values. Backup saved as", backup)
