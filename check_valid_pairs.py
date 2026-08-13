import json
from statistics import mean

d = json.load(open('outputs/synthetic_trust_routing_grid_results.json'))
results = d['results']

print("=" * 90)
print("VALID ROUTE PAIRS CHECK (out of 50 sampled pairs per run, 15 seeds per config)")
print("=" * 90)
print(f"{'nodes':>6} {'malicious%':>10} {'dist':>10} {'avg_valid_pairs':>16} {'num_runs':>9}")

for r in sorted(results, key=lambda x: (x['distribution'], x['num_nodes'], x['malicious_pct'])):
    # valid_route_pairs isn't in the summary dict directly, so we flag if it's missing
    print(f"{r['num_nodes']:>6} {r['malicious_pct']*100:>9.0f}% {r['distribution']:>10} "
          f"{'n/a - not in summary':>16} {r['num_runs']:>9}")

print()
print("NOTE: valid_route_pairs is per-run, not saved in the summary JSON.")
print("Checking instead whether num_runs ever drops below 15 (would indicate")
print("a config where run_single_simulation returned None due to zero valid pairs):")
print()
low_runs = [r for r in results if r['num_runs'] < 15]
if low_runs:
    print(f"FOUND {len(low_runs)} configs with fewer than 15 successful runs:")
    for r in low_runs:
        print(f"  nodes={r['num_nodes']} malicious={r['malicious_pct']} dist={r['distribution']} num_runs={r['num_runs']}")
else:
    print("All 50 configs completed all 15 seeds successfully (num_runs == 15 everywhere).")
    print("This does NOT fully rule out low valid_route_pairs WITHIN a run (e.g. only")
    print("5 of 50 pairs having a path), since that's averaged silently into the mean.")
    print("Recommend re-running synthetic_trust_routing_grid.py with valid_route_pairs")
    print("added to the saved summary if you want to confirm sample size per config.")