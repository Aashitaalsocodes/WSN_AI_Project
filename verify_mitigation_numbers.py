import json
from statistics import mean

std = json.load(open('outputs/synthetic_trust_routing_grid_results.json'))['results']
bic = json.load(open('outputs/synthetic_trust_routing_grid_results_biconnected.json'))['results']

def agg(results, dist, key):
    vals = [r[key] for r in results if r['distribution'] == dist]
    return round(mean(vals), 2), len(vals)

for dist in ['random', 'clustered']:
    ta_std, n1 = agg(std, dist, 'trust_aware_compromised_pct_mean')
    sc_std, n2 = agg(std, dist, 'soft_cost_compromised_pct_mean')
    ta_bic, n3 = agg(bic, dist, 'trust_aware_compromised_pct_mean')
    sc_bic, n4 = agg(bic, dist, 'soft_cost_compromised_pct_mean')
    print(f'{dist}: trust_aware std={ta_std}% (n={n1}) -> bic={ta_bic}% (n={n3})')
    print(f'{dist}: soft_cost  std={sc_std}% (n={n2}) -> bic={sc_bic}% (n={n4})')