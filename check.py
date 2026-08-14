import json
d = json.load(open('outputs/digital_twin_results.json'))
r0 = d['rounds'][0]
print('round 0 keys:', list(r0.keys()))
print('compromised_routes_pct:', r0.get('compromised_routes_pct'))