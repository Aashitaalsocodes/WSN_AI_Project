"""
run_v2_pilot_per_seed.py

Standalone companion script -- does NOT modify synthetic_trust_routing_grid_v2.py.
Imports its existing, unmodified functions and runs exactly the one config
needed to pair against the v3 bridge-node pilot:
    num_nodes=500, malicious_pct=0.25, distributions=[random, clustered],
    seeds_per_config=15, enforce_biconnected=False (i.e. "v2 standard").

Uses the IDENTICAL seed formula as both v2.run_sweep and v3.run_sweep:
    seed = 1000 * seed_offset + num_nodes + int(malicious_pct * 100)
so seed values here will match 1:1 against
outputs/synthetic_trust_routing_grid_results_v3_pilot_per_seed.csv by
seed_offset (and by seed value itself, as a redundant check).

Run from the project root:
    python run_v2_pilot_per_seed.py

Output:
    outputs/synthetic_trust_routing_grid_results_v2_pilot_per_seed.csv
"""

import csv
from pathlib import Path

from synthetic_trust_routing_grid_v2 import run_single_simulation, OUTPUTS_DIR

NUM_NODES = 500
MALICIOUS_PCT = 0.25
DISTRIBUTIONS = ["random", "clustered"]
SEEDS_PER_CONFIG = 15


def main():
    per_seed_rows = []

    for distribution in DISTRIBUTIONS:
        for seed_offset in range(SEEDS_PER_CONFIG):
            seed = 1000 * seed_offset + NUM_NODES + int(MALICIOUS_PCT * 100)
            result = run_single_simulation(
                NUM_NODES, MALICIOUS_PCT, distribution, seed,
                enforce_biconnected=False,  # "v2 standard", matches earlier console numbers
            )
            assert result is not None, (
                f"seed_offset={seed_offset} distribution={distribution} produced "
                f"no valid route pairs -- cannot log this row."
            )
            per_seed_rows.append({
                "seed_offset": seed_offset,
                "seed": seed,
                "num_nodes_base": NUM_NODES,
                "malicious_pct": MALICIOUS_PCT,
                "distribution": distribution,
                "result": result,
            })
            print(f"[v2-standard {distribution} seed_offset={seed_offset} seed={seed}] "
                  f"clustering_compromised_pct="
                  f"{result['trust_aware_clustering_compromised_pct']}")

    csv_path = OUTPUTS_DIR / "synthetic_trust_routing_grid_results_v2_pilot_per_seed.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "seed_offset", "seed", "num_nodes_base", "malicious_pct", "distribution",
            "baseline_compromised_pct", "trust_aware_compromised_pct",
            "trust_aware_clustering_compromised_pct", "soft_cost_compromised_pct",
            "valid_route_pairs",
        ])
        for row in per_seed_rows:
            r = row["result"]
            writer.writerow([
                row["seed_offset"], row["seed"], row["num_nodes_base"],
                row["malicious_pct"], row["distribution"],
                r["baseline_compromised_pct"], r["trust_aware_compromised_pct"],
                r["trust_aware_clustering_compromised_pct"], r["soft_cost_compromised_pct"],
                r["valid_route_pairs"],
            ])

    print(f"\nSaved {len(per_seed_rows)} per-seed rows to {csv_path}")


if __name__ == "__main__":
    main()