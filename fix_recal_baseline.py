with open('build_recalibration_report.py', 'r') as f:
    lines = f.readlines()

assert 'CURRENTLY_APPLIED_DETECTION_MISS_RATE = {' in lines[45], f"Line 46 mismatch: {lines[45]!r}"
assert '"Blackhole": 0.2344' in lines[46], f"Line 47 mismatch: {lines[46]!r}"
assert 'CURRENTLY_APPLIED_ATTACK_RISK_WEIGHTS = {' in lines[48], f"Line 49 mismatch: {lines[48]!r}"
assert '"TDMA": 0.1623' in lines[49], f"Line 50 mismatch: {lines[49]!r}"

lines[46] = '    "Blackhole": 0.2469, "Grayhole": 0.1038, "Flooding": 0.0103, "TDMA": 0.1343,\n'
lines[49] = '    "TDMA": 0.1354, "Flooding": 0.25, "Grayhole": 0.45, "Blackhole": 0.65,\n'

with open('build_recalibration_report.py', 'w') as f:
    f.writelines(lines)

print("Updated. New lines:")
for i in range(30, 52):
    print(f"{i+1}: {repr(lines[i])}")