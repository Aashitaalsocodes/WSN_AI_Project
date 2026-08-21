with open('trust_aware_routing.py', 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

lines = content.splitlines()
# Print lines 100 onward, up to ~200, to find where trust_scores is constructed
print("\n".join(lines[100:220]))