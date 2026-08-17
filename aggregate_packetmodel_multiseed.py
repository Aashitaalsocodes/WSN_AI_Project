"""
aggregate_packetmodel_multiseed.py

Same mean/std/raw pattern as aggregate_routing_multiseed.py, but pulls
the NEW packet-level metrics (packet_delivery_ratio_pct, avg_delay_ms,
throughput_kbps) from the *_packetmodel_seed{N}.json files instead of
the route-existence PDR in the original *_seed{N}.json files.

These packet-level fields only exist per-round (not in each file's
top-level "summary" block), so this script averages them directly from
the "rounds" list for every protocol, including TA-DT.

Run this AFTER all 25 files exist:
  outputs/digital_twin_results_packetmodel_seed{42,7,99,123,2024}.json
  outputs/baseline_leach_results_packetmodel_seed{...}.json
  outputs/baseline_heed_results_packetmodel_seed{...}.json
  outputs/baseline_tbr_results_packetmodel_seed{...}.json
  outputs/baseline_ai_sr_results_packetmodel_seed{...}.json

Writes outputs/packetmodel_multiseed_summary.json
"""
import json
import statistics as stats

SEEDS = [42, 7, 99, 123, 2024]

def mean_std(values):
    return {
        "mean": round(stats.mean(values), 4),
        "std": round(stats.pstdev(values), 4) if len(values) > 1 else 0.0,
        "raw": values,
    }

def per_round_means(path):
    """Average packet_delivery_ratio_pct, avg_delay_ms, throughput_kbps
    across all 23 rounds in one seed's result file."""
    d = json.load(open(path))
    rounds = d["rounds"]
    pdr = [r["packet_delivery_ratio_pct"] for r in rounds]
    delay = [r["avg_delay_ms"] for r in rounds if r.get("avg_delay_ms") is not None]
    throughput = [r["throughput_kbps"] for r in rounds]
    return {
        "pdr_pct": round(stats.mean(pdr), 4),
        "avg_delay_ms": round(stats.mean(delay), 4) if delay else None,
        "throughput_kbps": round(stats.mean(throughput), 4),
    }

results = {}

# ---------------------------------------------------------------- TA-DT
pdr, delay, throughput = [], [], []
for seed in SEEDS:
    m = per_round_means(f"outputs/digital_twin_results_packetmodel_seed{seed}.json")
    pdr.append(m["pdr_pct"])
    if m["avg_delay_ms"] is not None:
        delay.append(m["avg_delay_ms"])
    throughput.append(m["throughput_kbps"])

results["TA-DT"] = {
    "pdr_pct": mean_std(pdr),
    "avg_delay_ms": mean_std(delay),
    "throughput_kbps": mean_std(throughput),
}

# ---------------------------------------------------------------- Baselines
for proto_key, fname in [
    ("LEACH", "baseline_leach_results"),
    ("HEED", "baseline_heed_results"),
    ("TBR", "baseline_tbr_results"),
    ("AI-SR", "baseline_ai_sr_results"),
]:
    pdr, delay, throughput = [], [], []
    for seed in SEEDS:
        m = per_round_means(f"outputs/{fname}_packetmodel_seed{seed}.json")
        pdr.append(m["pdr_pct"])
        if m["avg_delay_ms"] is not None:
            delay.append(m["avg_delay_ms"])
        throughput.append(m["throughput_kbps"])

    results[proto_key] = {
        "pdr_pct": mean_std(pdr),
        "avg_delay_ms": mean_std(delay),
        "throughput_kbps": mean_std(throughput),
    }

out = {
    "seeds_used": SEEDS,
    "note": (
        "Real per-packet, per-hop PDR/delay/throughput from "
        "packet_transmission_model.py -- replaces the route-existence "
        "PDR (previously flat ~100%) reported in "
        "outputs/routing_multiseed_summary.json. See that module's "
        "docstring for drop-probability and timing calibration."
    ),
    "packet_delivery_summary": results,
}

with open("outputs/packetmodel_multiseed_summary.json", "w") as f:
    json.dump(out, f, indent=2)

print(json.dumps(out, indent=2))
print("\nWritten to outputs/packetmodel_multiseed_summary.json")