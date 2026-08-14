with open('digital_twin_sim.py', 'r') as f:
    lines = f.readlines()

# Sanity check we're editing the right lines
assert 'DETECTION_MISS_RATE_BY_TYPE = {' in lines[124], f"Line 125 mismatch: {lines[124]!r}"
assert '"blackhole"' in lines[125], f"Line 126 mismatch: {lines[125]!r}"
assert '"grayhole"' in lines[126], f"Line 127 mismatch: {lines[126]!r}"
assert '"flooding"' in lines[127], f"Line 128 mismatch: {lines[127]!r}"
assert '"tdma"' in lines[128], f"Line 129 mismatch: {lines[128]!r}"

lines[125] = '        "blackhole": 0.2469,\n'
lines[126] = '        "grayhole": 0.1038,\n'
lines[127] = '        "flooding": 0.0103,\n'
lines[128] = '        "tdma": 0.1343,\n'

with open('digital_twin_sim.py', 'w') as f:
    f.writelines(lines)

print("Updated. New block:")
for i in range(124, 132):
    print(f"{i+1}: {repr(lines[i])}")