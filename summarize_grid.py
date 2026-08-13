import json

d = json.load(open('outputs/synthetic_trust_routing_grid_results.json'))
for r in d['results']:
    if r['distribution'] == 'random' and r['malicious_pct'] == 0.10:
        avg_degree = 2 * r.get('num_edges', 0) / r['num_nodes'] if 'num_edges' in r else None
        print(f"nodes={r['num_nodes']:4d}  trust_aware={r['trust_aware_compromised_pct_mean']:6.2f}%  trust_aware_std={r['trust_aware_compromised_pct_std']}")