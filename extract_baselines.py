import json

files = {
    "LEACH": "outputs/baseline_leach_results.json",
    "HEED": "outputs/baseline_heed_results.json",
    "TBR": "outputs/baseline_tbr_results.json",
    "AI-SR": "outputs/baseline_ai_sr_results.json",
}

results = {}

for name, path in files.items():
    with open(path) as f:
        data = json.load(f)
    rounds = data["rounds"]
    n = len(rounds)

    energies = [r["avg_energy_remaining"] for r in rounds]
    avg_energy = sum(energies) / n

    entry = {"avg_energy_remaining": avg_energy, "num_rounds": n}

    if "excluded_nodes" in rounds[0]:
        total_tp = total_fp = total_fn = total_tn = 0
        for r in rounds:
            attacked = set(r["attacked_nodes"])
            excluded = set(r["excluded_nodes"])
            tp = len(attacked & excluded)
            fn = len(attacked - excluded)
            fp = len(excluded - attacked)
            tn = 500 - tp - fn - fp
            total_tp += tp; total_fp += fp; total_fn += fn; total_tn += tn
        acc = (total_tp + total_tn) / (500 * n)
        entry["detection_accuracy"] = acc
        entry["tp"] = total_tp
        entry["fp"] = total_fp
        entry["fn"] = total_fn
        entry["tn"] = total_tn
    else:
        entry["detection_accuracy"] = None  # N/A, no detection mechanism

    results[name] = entry

for name, e in results.items():
    print(f"\n=== {name} ===")
    print(f"  avg_energy_remaining: {e['avg_energy_remaining']:.4f}")
    if e["detection_accuracy"] is not None:
        print(f"  detection_accuracy: {e['detection_accuracy']*100:.2f}%  (tp={e['tp']}, fp={e['fp']}, fn={e['fn']}, tn={e['tn']})")
    else:
        print("  detection_accuracy: N/A (no detection mechanism)")