with open('feedback_loop.py', 'r') as f:
    lines = f.readlines()

assert 'CURRENT_DETECTION_MISS_RATE_BY_TYPE = {' in lines[79], f"Line 80 mismatch: {lines[79]!r}"
assert '"Blackhole": 0.2344' in lines[80], f"Line 81 mismatch: {lines[80]!r}"
assert 'CURRENT_ATTACK_RISK_WEIGHTS = {' in lines[82], f"Line 83 mismatch: {lines[82]!r}"
assert '"Normal": 0.0, "TDMA": 0.1623' in lines[83], f"Line 84 mismatch: {lines[83]!r}"

lines[80] = '    "Blackhole": 0.2469, "Grayhole": 0.1038, "Flooding": 0.0103, "TDMA": 0.1343\n'
lines[83] = '    "Normal": 0.0, "TDMA": 0.1354, "Flooding": 0.25, "Grayhole": 0.45, "Blackhole": 0.65\n'

with open('feedback_loop.py', 'w') as f:
    f.writelines(lines)

print("Updated. New lines:")
for i in range(75, 92):
    print(f"{i+1}: {repr(lines[i])}")