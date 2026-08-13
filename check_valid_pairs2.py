import json

d = json.load(open('outputs/synthetic_trust_routing_grid_results.json'))
results = d['results']

print("Configs where avg valid_route_pairs mean < 40 (out of 50 sampled), or min < 30:")
print("=" * 90)
flagged = 0
for r in sorted(results, key=lambda x: (x['distribution'], x['num_nodes'], x['malicious_pct'])):
    avg_valid = r.get('valid_route_pairs_mean')
    min_valid = r.get('min_valid_route_pairs')
    if (avg_valid is not None and avg_valid < 40) or (min_valid is not None and min_valid < 30):
        flagged += 1
        print(f"nodes={r['num_nodes']:4d} malicious={r['malicious_pct']:.2f} dist={r['distribution']:10s} "
              f"avg_valid={avg_valid} min_valid={min_valid}")

if flagged == 0:
    print("None flagged - sample size held up across all 50 configs.")
print(f"\nTotal flagged: {flagged} / {len(results)}")
