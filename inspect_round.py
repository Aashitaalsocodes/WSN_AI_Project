import json

d = json.load(open('outputs/digital_twin_results.json'))
r = d['rounds'][16]  # a round after FND, should have real activity
for k, v in r.items():
    if isinstance(v, list):
        print(k, '(list, len', len(v), '):', v[:5])
    else:
        print(k, ':', v)