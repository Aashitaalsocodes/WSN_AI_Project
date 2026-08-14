"""
aggregate_seeds.py
Load the 5 seeded digital_twin_sim_multiseed.py outputs and compute
mean+-std for FND, HND, LND, avg trust score, avg compromised-route %,
and avg hop count.
"""
import json
import statistics

SEEDS = [42, 7, 123, 2024, 99]
OUTPUTS_DIR = "outputs"

def load_seed_result(seed):
    path = f"{OUTPUTS_DIR}/digital_twin_results_seed{seed}.json"
    with open(path, "r") as f:
        return json.load(f)

def mean_std(values):
    values = [v for v in values if v is not None]
    if not values:
        return None, None
    m = statistics.mean(values)
    s = statistics.stdev(values) if len(values) > 1 else 0.0
    return round(m, 4), round(s, 4)

def main():
    fnd_vals, hnd_vals, lnd_vals = [], [], []
    trust_vals, compromised_vals, hop_vals = [], [], []

    for seed in SEEDS:
        data = load_seed_result(seed)
        rounds = data["rounds"]
        es = data["energy_summary"]

        fnd_vals.append(es["first_node_death_round"])
        hnd_vals.append(es["half_node_death_round"])
        lnd_vals.append(es["last_node_death_round"])

        trust_vals.append(statistics.mean(r["avg_trust_score"] for r in rounds))
        compromised_vals.append(statistics.mean(r["compromised_routes_pct"] for r in rounds))
        hop_vals.append(statistics.mean(r["avg_hop_count"] for r in rounds))

    def block(vals):
        m, s = mean_std(vals)
        return {"mean": m, "std": s, "raw": vals}

    summary = {
        "seeds_used": SEEDS,
        "fnd_round": block(fnd_vals),
        "hnd_round": block(hnd_vals),
        "lnd_round": block(lnd_vals),
        "avg_trust_score": block(trust_vals),
        "avg_compromised_routes_pct": block(compromised_vals),
        "avg_hop_count": block(hop_vals),
    }

    with open(f"{OUTPUTS_DIR}/multi_seed_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(json.dumps(summary, indent=2))

if __name__ == "__main__":
    main()