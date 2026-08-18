"""
summarize_clustering_fix.py

Reads outputs/synthetic_trust_routing_grid_results.json and prints a
side-by-side comparison of trust_aware vs trust_aware_clustering compromised
route %, isolated to distribution == "clustered" (the scenario the paper's
Figure 8 / 21.42% limitation is about), plus the overall average improvement.

Usage:
    python summarize_clustering_fix.py
"""

import json
from pathlib import Path
from statistics import mean

RESULTS_PATH = Path("outputs") / "synthetic_trust_routing_grid_results.json"


def main():
    with open(RESULTS_PATH) as f:
        data = json.load(f)

    results = data["results"]
    clustered = [r for r in results if r["distribution"] == "clustered"]
    random_dist = [r for r in results if r["distribution"] == "random"]

    assert clustered, "No clustered-distribution results found -- did the sweep run correctly?"

    print("=" * 100)
    print(f"{'nodes':>6} {'mal%':>6} | {'baseline':>9} {'trust_aware':>12} {'trust_aware_clust':>18} | {'clust_vs_TA':>12}")
    print("=" * 100)

    improvements = []
    for r in sorted(clustered, key=lambda x: (x["num_nodes"], x["malicious_pct"])):
        baseline = r["baseline_compromised_pct_mean"]
        trust_aware = r["trust_aware_compromised_pct_mean"]
        clustering = r["trust_aware_clustering_compromised_pct_mean"]
        delta = round(trust_aware - clustering, 2)  # positive = clustering-aware is better (lower compromised %)
        improvements.append(delta)
        print(f"{r['num_nodes']:>6} {r['malicious_pct']*100:>5.0f}% | "
              f"{baseline:>9.2f} {trust_aware:>12.2f} {clustering:>18.2f} | {delta:>+12.2f}")

    print("=" * 100)
    print(f"\nAverage improvement (trust_aware - trust_aware_clustering) across clustered configs: "
          f"{round(mean(improvements), 2)} percentage points")
    print(f"Configs where clustering-aware was BETTER (positive delta): "
          f"{sum(1 for d in improvements if d > 0)}/{len(improvements)}")
    print(f"Configs where clustering-aware was WORSE (negative delta): "
          f"{sum(1 for d in improvements if d < 0)}/{len(improvements)}")

    hop_deltas = []
    for r in clustered:
        ta_hops = r["trust_aware_avg_hops_mean"]
        tac_hops = r["trust_aware_clustering_avg_hops_mean"]
        hop_deltas.append(tac_hops - ta_hops)
    print(f"\nAverage extra hop count (clustering-aware vs trust-aware): "
          f"{round(mean(hop_deltas), 3)} hops")

    print("\n--- For reference, random-distribution trust_aware_clustering (should NOT be much worse than trust_aware) ---")
    for r in sorted(random_dist, key=lambda x: (x["num_nodes"], x["malicious_pct"]))[:5]:
        print(f"nodes={r['num_nodes']} mal%={r['malicious_pct']*100:.0f}% "
              f"trust_aware={r['trust_aware_compromised_pct_mean']:.2f} "
              f"trust_aware_clustering={r['trust_aware_clustering_compromised_pct_mean']:.2f}")


if __name__ == "__main__":
    main()