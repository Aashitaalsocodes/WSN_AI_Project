# fix_recal_baseline_cycle3.py
path = "build_recalibration_report.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old = 'CURRENTLY_APPLIED_ATTACK_RISK_WEIGHTS = {\n    "TDMA": 0.1354, "Flooding": 0.25, "Grayhole": 0.45, "Blackhole": 0.65,\n}'
new = 'CURRENTLY_APPLIED_ATTACK_RISK_WEIGHTS = {\n    "TDMA": 0.1354, "Flooding": 0.2, "Grayhole": 0.4, "Blackhole": 0.6,\n}'

assert old in content, "NOT FOUND: CURRENTLY_APPLIED_ATTACK_RISK_WEIGHTS block"
assert content.count(old) == 1, f"NOT UNIQUE ({content.count(old)}x)"
content = content.replace(old, new)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("build_recalibration_report.py: CURRENTLY_APPLIED_ATTACK_RISK_WEIGHTS updated to cycle-3 values.")