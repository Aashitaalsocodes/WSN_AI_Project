import json

d = json.load(open('outputs/digital_twin_results.json'))
rounds = d['rounds']

total_tp, total_fp, total_tn = 0, 0, 0
energy_vals = []

for r in rounds:
    attacked = len(r['attacked_nodes'])
    excluded = len(r['excluded_nodes'])
    missed = len(r['missed_detections'])
    tp = attacked - missed
    fp = excluded - tp
    tn = 500 - attacked - fp
    total_tp += tp
    total_fp += fp
    total_tn += tn
    energy_vals.append(r['avg_energy_remaining'])

n = len(rounds)
acc = (total_tp + total_tn) / (500 * n)
print('detection_accuracy:', round(acc * 100, 2))
print('avg_energy_remaining_across_rounds:', round(sum(energy_vals) / n, 4))
print('num_rounds:', n)
print('total_tp:', total_tp, 'total_fp:', total_fp, 'total_tn:', total_tn)