import json
from scipy import stats

std = json.load(open('outputs/synthetic_trust_routing_grid_results.json'))['results']
bic = json.load(open('outputs/synthetic_trust_routing_grid_results_biconnected.json'))['results']

def config_key(r):
    return (r['num_nodes'], r['malicious_pct'])

def paired_values(std_results, bic_results, dist, key):
    std_f = {config_key(r): r[key] for r in std_results if r['distribution'] == dist}
    bic_f = {config_key(r): r[key] for r in bic_results if r['distribution'] == dist}
    common = sorted(set(std_f.keys()) & set(bic_f.keys()))
    a = [std_f[k] for k in common]
    b = [bic_f[k] for k in common]
    return a, b, common

for mode_key, label in [('trust_aware_compromised_pct_mean', 'trust-aware'),
                          ('soft_cost_compromised_pct_mean', 'soft-cost')]:
    a, b, common = paired_values(std, bic, 'clustered', mode_key)
    t_stat, p_val = stats.ttest_rel(a, b)
    print(f'{label}: n_configs={len(common)}, df={len(common)-1}, t={t_stat:.2f}, p={p_val:.4f}')