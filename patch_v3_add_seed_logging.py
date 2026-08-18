"""
patch_v3_add_seed_logging.py

Assertion-guarded, in-place patch for synthetic_trust_routing_grid_v3.py.
Adds per-seed CSV logging to run_sweep() WITHOUT changing any existing
simulation logic, JSON output, or aggregate summary behavior. Only adds
a new CSV write alongside the existing JSON write.

Run from the project root:
    python patch_v3_add_seed_logging.py

It will refuse to touch the file (hard AssertionError) if the expected
anchor text isn't found exactly once -- meaning the source you pasted
here doesn't match what's actually in run_sweep(), and this patch
should not be applied blindly.

After running, verify with:
    findstr /n "log_per_seed_csv per_seed_rows" synthetic_trust_routing_grid_v3.py
"""

from pathlib import Path

TARGET = Path("synthetic_trust_routing_grid_v3.py")

OLD_LOOP = '''                runs = []
                for seed_offset in range(SEEDS_PER_CONFIG):
                    seed = 1000 * seed_offset + num_nodes + int(malicious_pct * 100)
                    result = run_single_simulation(
                        num_nodes, malicious_pct, distribution, seed,
                        enforce_biconnected=False,
                        add_bridge_pct=add_bridge_pct,
                    )
                    runs.append(result)

                summary = summarize_runs(runs)
                all_results.append({
                    "num_nodes_base": num_nodes,
                    "malicious_pct": malicious_pct,
                    "distribution": distribution,
                    **summary,
                })'''

NEW_LOOP = '''                runs = []
                for seed_offset in range(SEEDS_PER_CONFIG):
                    seed = 1000 * seed_offset + num_nodes + int(malicious_pct * 100)
                    result = run_single_simulation(
                        num_nodes, malicious_pct, distribution, seed,
                        enforce_biconnected=False,
                        add_bridge_pct=add_bridge_pct,
                    )
                    runs.append(result)
                    # NEW: retain per-seed rows for CSV logging (does not
                    # affect existing summary/JSON behavior below).
                    per_seed_rows.append({
                        "seed_offset": seed_offset,
                        "seed": seed,
                        "num_nodes_base": num_nodes,
                        "malicious_pct": malicious_pct,
                        "distribution": distribution,
                        "result": result,
                    })

                summary = summarize_runs(runs)
                all_results.append({
                    "num_nodes_base": num_nodes,
                    "malicious_pct": malicious_pct,
                    "distribution": distribution,
                    **summary,
                })'''

OLD_HEADER = '''    NODE_COUNTS = node_counts or [100, 250, 500, 750, 1000]
    MALICIOUS_PCTS = malicious_pcts or [0.05, 0.10, 0.15, 0.20, 0.25]
    DISTRIBUTIONS = ["random", "clustered"]
    SEEDS_PER_CONFIG = 15
    all_results = []'''

NEW_HEADER = '''    NODE_COUNTS = node_counts or [100, 250, 500, 750, 1000]
    MALICIOUS_PCTS = malicious_pcts or [0.05, 0.10, 0.15, 0.20, 0.25]
    DISTRIBUTIONS = ["random", "clustered"]
    SEEDS_PER_CONFIG = 15
    all_results = []
    per_seed_rows = []  # NEW: raw per-seed results for auditability'''

OLD_SAVE = '''    output_path = OUTPUTS_DIR / output_filename
    with open(output_path, "w") as f:
        json.dump({'''

NEW_SAVE = '''    # NEW: write per-seed CSV alongside the existing JSON summary.
    # Uses the metric that matters for the random-vs-clustered gap
    # analysis: trust_aware_clustering_compromised_pct (also includes
    # the other three compromised_pct metrics for completeness).
    csv_path = OUTPUTS_DIR / (Path(output_filename).stem + "_per_seed.csv")
    with open(csv_path, "w", newline="") as f:
        import csv as _csv
        writer = _csv.writer(f)
        writer.writerow([
            "seed_offset", "seed", "num_nodes_base", "malicious_pct", "distribution",
            "baseline_compromised_pct", "trust_aware_compromised_pct",
            "trust_aware_clustering_compromised_pct", "soft_cost_compromised_pct",
            "valid_route_pairs",
        ])
        for row in per_seed_rows:
            r = row["result"]
            assert r is not None, (
                f"seed_offset={row['seed_offset']} produced no valid route pairs "
                f"(run_single_simulation returned None) -- cannot log this row. "
                f"Investigate before trusting aggregate stats for this config."
            )
            writer.writerow([
                row["seed_offset"], row["seed"], row["num_nodes_base"],
                row["malicious_pct"], row["distribution"],
                r["baseline_compromised_pct"], r["trust_aware_compromised_pct"],
                r["trust_aware_clustering_compromised_pct"], r["soft_cost_compromised_pct"],
                r["valid_route_pairs"],
            ])
    print(f"Saved {len(per_seed_rows)} per-seed rows to {csv_path}")

    output_path = OUTPUTS_DIR / output_filename
    with open(output_path, "w") as f:
        json.dump({'''


def patch():
    text = TARGET.read_text(encoding="utf-8")

    assert text.count(OLD_HEADER) == 1, (
        "OLD_HEADER anchor not found exactly once -- file doesn't match "
        "expected source. Aborting without changes."
    )
    assert text.count(OLD_LOOP) == 1, (
        "OLD_LOOP anchor not found exactly once -- file doesn't match "
        "expected source. Aborting without changes."
    )
    assert text.count(OLD_SAVE) == 1, (
        "OLD_SAVE anchor not found exactly once -- file doesn't match "
        "expected source. Aborting without changes."
    )

    text = text.replace(OLD_HEADER, NEW_HEADER)
    text = text.replace(OLD_LOOP, NEW_LOOP)
    text = text.replace(OLD_SAVE, NEW_SAVE)

    # Ensure Path is imported (it already is, at top of file, but assert
    # rather than assume in case that changes).
    assert "from pathlib import Path" in text, (
        "Path import missing -- patch relies on it for csv_path construction."
    )

    TARGET.write_text(text, encoding="utf-8")
    print(f"Patched {TARGET} successfully.")
    print("Verify with: findstr /n \"per_seed_rows log_per_seed\" " + str(TARGET))


if __name__ == "__main__":
    patch()