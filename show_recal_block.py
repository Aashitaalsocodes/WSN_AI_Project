with open('build_recalibration_report.py', 'r') as f:
    lines = f.readlines()
for i in range(30, 52):
    print(f"{i+1}: {repr(lines[i])}")