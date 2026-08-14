with open('feedback_loop.py', 'r') as f:
    lines = f.readlines()
for i in range(75, 92):
    print(f"{i+1}: {repr(lines[i])}")