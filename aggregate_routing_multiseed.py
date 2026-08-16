"""
aggregate_routing_multiseed.py

Builds mean +/- std across the 5 seeds (42, 7, 123, 2024, 99) for:
  - Section VI: routing_cost_results_seed{N}.json (200-route test)
  - Section VIII: TA-DT row from digital_twin_results_seed{N}.json,
    using the exact tp/fp/tn formula from analyze.py, plus the 4
    baseline rows from baseline_*_results_seed{N}.json

Writes outputs/routing_multiseed_summary.json in the same mean/std/raw
shape as the existing outputs/multi_seed_summary.json, so it's easy to
cross-check and to paraphrase into the paper's Section VI/VIII tables.
"""
import json
import statistics as stats

SEEDS = [42, 7, 123, 2024, 99]

def mean_std(values):
    return {
        "mean": round(stats.mean(values), 4),
        "std": round(stats.pstdev(values), 4) if len(values) > 1 else 0.0,
        "raw": values,
    }

def detection_accuracy_and_recall(dt_path):
    d = json.load(open(dt_path))
    rounds = d["rounds"]
    total_tp = total_fp = total_tn = total_attacked = 0
    energy_vals = []
    for r in rounds:
        attacked = len(r["attacked_nodes"])
        excluded = len(r["excluded_nodes"])
        missed = len(r["missed_detections"])
        tp = attacked - missed
        fp = excluded - tp
        tn = 500 - attacked - fp
        total_tp += tp
        total_fp += fp
        total_tn += tn
        total_attacked += attacked
        energy_vals.append(r["avg_energy_remaining"])
    n = len(rounds)
    acc = (total_tp + total_tn) / (500 * n) * 100
    recall = (total_tp / total_attacked * 100) if total_attacked else None
    avg_energy = sum(energy_vals) / n
    return acc, recall, avg_energy

# ---------------------------------------------------------------- Section VI
routing_cost_hop = []
routing_cost_compromised = []
for seed in SEEDS:
    d = json.load(open(f"outputs/routing_cost_results_seed{seed}.json"))
    s = d["summary"]
    routing_cost_hop.append(s["avg_hop_count"])
    routing_cost_compromised.append(s["pct_compromised_routes"])

section_vi = {
    "avg_hop_count": mean_std(routing_cost_hop),
    "pct_compromised_routes": mean_std(routing_cost_compromised),
}

# ---------------------------------------------------------------- Section VIII: TA-DT
ta_dt_acc, ta_dt_recall, ta_dt_energy = [], [], []
for seed in SEEDS:
    acc, recall, energy = detection_accuracy_and_recall(f"outputs/digital_twin_results_seed{seed}.json")
    ta_dt_acc.append(round(acc, 4))
    ta_dt_recall.append(round(recall, 4))
    ta_dt_energy.append(round(energy, 4))

# reuse existing multi_seed_summary.json for TA-DT's FND/HND/LND/hop/compromised
existing = json.load(open("outputs/multi_seed_summary.json"))

section_viii = {
    "TA-DT": {
        "detection_accuracy_pct": mean_std(ta_dt_acc),
        "detection_recall_pct": mean_std(ta_dt_recall),
        "avg_energy_remaining": mean_std(ta_dt_energy),
        "fnd_hnd_lnd": {
            "fnd": existing["fnd_round"],
            "hnd": existing["hnd_round"],
            "lnd": existing["lnd_round"],
        },
        "avg_hop_count": existing["avg_hop_count"],
        "avg_compromised_routes_pct": existing["avg_compromised_routes_pct"],
        "pdr_pct": "100.0 (flat by simulation design, see Limitations)",
    }
}

# ---------------------------------------------------------------- Section VIII: baselines
for proto_key, fname in [
    ("LEACH", "baseline_leach_results"),
    ("HEED", "baseline_heed_results"),
    ("TBR", "baseline_tbr_results"),
    ("AI-SR", "baseline_ai_sr_results"),
]:
    pdr, compromised, hop, energy, fnd, hnd, lnd, det_acc = [], [], [], [], [], [], [], []
    for seed in SEEDS:
        d = json.load(open(f"outputs/{fname}_seed{seed}.json"))
        s = d["summary"]
        e = d["energy_summary"]
        pdr.append(s["avg_packet_delivery_ratio_pct"])
        compromised.append(s["avg_compromised_routes_pct"])
        hop.append(s["avg_hop_count"])
        rounds = d["rounds"]
        energy.append(round(sum(r["avg_energy_remaining"] for r in rounds) / len(rounds), 4))
        fnd.append(e["first_node_death_round"])
        hnd.append(e["half_node_death_round"])
        lnd.append(e["last_node_death_round"])
        if s["detection_accuracy_pct"] is not None:
            det_acc.append(s["detection_accuracy_pct"])

    section_viii[proto_key] = {
        "pdr_pct": mean_std(pdr),
        "avg_compromised_routes_pct": mean_std(compromised),
        "avg_hop_count": mean_std(hop),
        "avg_energy_remaining": mean_std(energy),
        "fnd_hnd_lnd": {
            "fnd": mean_std(fnd),
            "hnd": mean_std(hnd),
            "lnd": mean_std(lnd),
        },
        "detection_accuracy_pct": mean_std(det_acc) if det_acc else "N/A (no trust/attack classifier)",
    }

out = {"seeds_used": SEEDS, "section_vi_200_route_test": section_vi, "section_viii_protocol_comparison": section_viii}
with open("outputs/routing_multiseed_summary.json", "w") as f:
    json.dump(out, f, indent=2)

print(json.dumps(out, indent=2))
print("\nWritten to outputs/routing_multiseed_summary.json")