with open('routing_cost.py', 'r') as f:
    lines = f.readlines()
for i in range(56, 66):
    print(f"{i+1}: {repr(lines[i])}")