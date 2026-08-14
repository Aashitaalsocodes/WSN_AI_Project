with open('digital_twin_sim.py', 'r') as f:
    lines = f.readlines()
for i in range(124, 132):
    print(f"{i+1}: {repr(lines[i])}")