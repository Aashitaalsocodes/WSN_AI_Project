# fix_routing_cost_cycle3.py
path = "routing_cost.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

replacements = [
    ('    "Flooding": 0.25,\n', '    "Flooding": 0.2,\n'),
    ('    "Grayhole": 0.45,\n', '    "Grayhole": 0.4,\n'),
    ('    "Blackhole": 0.65,\n', '    "Blackhole": 0.6,\n'),
]

for old, new in replacements:
    assert old in content, f"NOT FOUND: {old!r}"
    assert content.count(old) == 1, f"NOT UNIQUE ({content.count(old)}x): {old!r}"
    content = content.replace(old, new)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("routing_cost.py: ATTACK_RISK_WEIGHT updated to cycle-3 values.")