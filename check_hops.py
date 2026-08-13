import json

d = json.load(open('outputs/synthetic_trust_routing_grid_results.json'))
results = d['results']

def avg(key, rows):
    vals = [r[key] for r in rows if r.get(key) is not None]
    return sum(vals) / len(vals) if vals else None

print("=" * 80)
print("HOP OVERHEAD BY NODE COUNT")
print("=" * 80)
for nc in sorted(set(r['num_nodes'] for r in results)):
    rows = [r for r in results if r['num_nodes'] == nc]
    b = avg('baseline_avg_hops_mean', rows)
    t = avg('trust_aware_avg_hops_mean', rows)
    print(f"nodes={nc:4d}  baseline_hops={b:.3f}  trust_aware_hops={t:.3f}  overhead={t-b:+.3f}")

print()
print("=" * 80)
print("HOP OVERHEAD BY MALICIOUS %")
print("=" * 80)
for mp in sorted(set(r['malicious_pct'] for r in results)):
    rows = [r for r in results if r['malicious_pct'] == mp]
    b = avg('baseline_avg_hops_mean', rows)
    t = avg('trust_aware_avg_hops_mean', rows)
    print(f"malicious={mp:.2f}  baseline_hops={b:.3f}  trust_aware_hops={t:.3f}  overhead={t-b:+.3f}")

print()
print("=" * 80)
print("HOP OVERHEAD BY DISTRIBUTION")
print("=" * 80)
for dist in sorted(set(r['distribution'] for r in results)):
    rows = [r for r in results if r['distribution'] == dist]
    b = avg('baseline_avg_hops_mean', rows)
    t = avg('trust_aware_avg_hops_mean', rows)
    print(f"dist={dist:10s}  baseline_hops={b:.3f}  trust_aware_hops={t:.3f}  overhead={t-b:+.3f}")

print()
print("=" * 80)
print("OVERALL AVERAGE (all 50 configs)")
print("=" * 80)
b = avg('baseline_avg_hops_mean', results)
t = avg('trust_aware_avg_hops_mean', results)
print(f"baseline_hops={b:.3f}  trust_aware_hops={t:.3f}  overhead={t-b:+.3f}")
