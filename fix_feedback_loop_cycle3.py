# fix_feedback_loop_cycle3.py
path = "feedback_loop.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old = 'CURRENT_ATTACK_RISK_WEIGHTS = {\n    "Normal": 0.0, "TDMA": 0.1354, "Flooding": 0.25, "Grayhole": 0.45, "Blackhole": 0.65\n}'
new = 'CURRENT_ATTACK_RISK_WEIGHTS = {\n    "Normal": 0.0, "TDMA": 0.1354, "Flooding": 0.2, "Grayhole": 0.4, "Blackhole": 0.6\n}'

assert old in content, "NOT FOUND: CURRENT_ATTACK_RISK_WEIGHTS block — check exact formatting"
assert content.count(old) == 1, f"NOT UNIQUE ({content.count(old)}x)"
content = content.replace(old, new)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("feedback_loop.py: CURRENT_ATTACK_RISK_WEIGHTS updated to cycle-3 values.")