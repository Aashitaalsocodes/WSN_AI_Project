import json

d = json.load(open('outputs/synthetic_trust_routing_grid_results.json'))
results = d['results']

def fmt(pct):
    return f"{pct:6.2f}%" if pct is not None else "   n/a"

print("=" * 70)
print("BREAKDOWN BY NODE COUNT (averaged across all malicious_pct + distribution)")
print("=" * 70)
node_counts = sorted(set(r['num_nodes'] for r in results))
for nc in node_counts:
    rows = [r for r in results if r['num_nodes'] == nc]
    ta_vals = [r['trust_aware_compromised_pct_mean'] for r in rows]
    base_vals = [r.get('baseline_compromised_pct_mean') for r in rows if r.get('baseline_compromised_pct_mean') is not None]
    avg_ta = sum(ta_vals) / len(ta_vals)
    avg_base = sum(base_vals) / len(base_vals) if base_vals else None
    print(f"nodes={nc:4d}  n_configs={len(rows):3d}  trust_aware={fmt(avg_ta)}  baseline={fmt(avg_base)}")

print()
print("=" * 70)
print("BREAKDOWN BY MALICIOUS % (averaged across all node counts + distribution)")
print("=" * 70)
mal_pcts = sorted(set(r['malicious_pct'] for r in results))
for mp in mal_pcts:
    rows = [r for r in results if r['malicious_pct'] == mp]
    ta_vals = [r['trust_aware_compromised_pct_mean'] for r in rows]
    base_vals = [r.get('baseline_compromised_pct_mean') for r in rows if r.get('baseline_compromised_pct_mean') is not None]
    avg_ta = sum(ta_vals) / len(ta_vals)
    avg_base = sum(base_vals) / len(base_vals) if base_vals else None
    print(f"malicious_pct={mp:.2f}  n_configs={len(rows):3d}  trust_aware={fmt(avg_ta)}  baseline={fmt(avg_base)}")

print()
print("=" * 70)
print("BREAKDOWN BY DISTRIBUTION (averaged across all node counts + malicious_pct)")
print("=" * 70)
dists = sorted(set(r['distribution'] for r in results))
for dist in dists:
    rows = [r for r in results if r['distribution'] == dist]
    ta_vals = [r['trust_aware_compromised_pct_mean'] for r in rows]
    base_vals = [r.get('baseline_compromised_pct_mean') for r in rows if r.get('baseline_compromised_pct_mean') is not None]
    avg_ta = sum(ta_vals) / len(ta_vals)
    avg_base = sum(base_vals) / len(base_vals) if base_vals else None
    print(f"distribution={dist:10s}  n_configs={len(rows):3d}  trust_aware={fmt(avg_ta)}  baseline={fmt(avg_base)}")

print()
print("=" * 70)
print(f"TOTAL RESULT ROWS: {len(results)} (expect 5 node_counts x 5 malicious_pcts x 2 distributions = 50 configs, x 15 seeds = 750 sims aggregated into 50 rows)")
print("=" * 70)