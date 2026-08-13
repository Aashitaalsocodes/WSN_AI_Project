import json

for fname in ['baseline_leach_results.json', 'baseline_heed_results.json', 'baseline_tbr_results.json', 'baseline_ai_sr_results.json']:
    d = json.load(open('outputs/' + fname))
    print('=== ' + fname + ' ===')
    print('top-level keys:', list(d.keys()))
    if 'rounds' in d:
        print('round-0 keys:', list(d['rounds'][0].keys()))
    print()