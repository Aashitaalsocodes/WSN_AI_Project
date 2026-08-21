import re

with open('trust_aware_routing.py', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

print("=== Lines mentioning 'trust_scores' (assignment or construction) ===\n")
for i, line in enumerate(lines):
    if 'trust_scores' in line or 'trust_score' in line:
        print(f"{i+1}: {line.rstrip()}")