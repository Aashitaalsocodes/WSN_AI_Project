import json
from collections import Counter

nodes = json.load(open('outputs/mitigation_actions.json'))
ch_nodes = [n for n in nodes.values() if n.get('is_cluster_head') == 1]

pred_dist = Counter(n['attack_type'] for n in ch_nodes)
print("Predicted attack_type among CHs:", pred_dist)
print("Total predicted Blackhole (CH + non-CH):", sum(1 for n in nodes.values() if n['attack_type']=='Blackhole'))
print("Should be close to true Blackhole count: 10,049")