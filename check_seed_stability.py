"""
check_seed_stability.py

Purpose: verify whether the "clustered - random" gap widens from v2 -> v3
(bridge-node deployment) in more than 12 of 15 seeds.

USAGE (run from your project directory, e.g. C:\\Users\\Admin\\WSN_AI_Project):
    python scripts\\check_seed_stability.py --v2 <path_to_v2_per_seed_file> --v3 <path_to_v3_per_seed_file>

Expected input format: CSV with at minimum these columns (header row required):
    seed, random_pct, clustered_pct

If your actual output files use different column names, adjust COL_SEED /
COL_RANDOM / COL_CLUSTERED below rather than renaming your data files.

The script is assertion-guarded: it will hard-fail (not silently coerce)
if seeds don't line up 1:1 between v2 and v3, or if there aren't exactly
15 seeds in each file. That's intentional -- a mismatch here would
invalidate the stability claim, so we want a loud error, not a quiet
partial comparison.
"""

import argparse
import csv
import sys

COL_SEED = "seed"
COL_RANDOM = "random_pct"
COL_CLUSTERED = "clustered_pct"

EXPECTED_SEED_COUNT = 15
STABILITY_THRESHOLD = 12  # >12 of 15 seeds must show widening


def load_per_seed(path):
    rows = {}
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames is not None, f"{path}: no header row found"
        for col in (COL_SEED, COL_RANDOM, COL_CLUSTERED):
            assert col in reader.fieldnames, (
                f"{path}: expected column '{col}' not found. "
                f"Found columns: {reader.fieldnames}. "
                f"Edit COL_SEED/COL_RANDOM/COL_CLUSTERED at top of script if names differ."
            )
        for r in reader:
            seed = r[COL_SEED].strip()
            assert seed not in rows, f"{path}: duplicate seed {seed}"
            rows[seed] = {
                "random": float(r[COL_RANDOM]),
                "clustered": float(r[COL_CLUSTERED]),
            }
    assert len(rows) == EXPECTED_SEED_COUNT, (
        f"{path}: expected exactly {EXPECTED_SEED_COUNT} seeds, found {len(rows)}. "
        f"Seeds present: {sorted(rows.keys())}"
    )
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--v2", required=True, help="path to v2 (standard) per-seed CSV")
    ap.add_argument("--v3", required=True, help="path to v3 (+10% bridges) per-seed CSV")
    args = ap.parse_args()

    v2 = load_per_seed(args.v2)
    v3 = load_per_seed(args.v3)

    assert set(v2.keys()) == set(v3.keys()), (
        "Seed sets differ between v2 and v3 files -- cannot pair seeds 1:1.\n"
        f"v2 only: {sorted(set(v2) - set(v3))}\n"
        f"v3 only: {sorted(set(v3) - set(v2))}"
    )

    widened = 0
    narrowed = 0
    unchanged = 0
    details = []

    for seed in sorted(v2.keys(), key=lambda s: int(s) if s.isdigit() else s):
        gap_v2 = v2[seed]["clustered"] - v2[seed]["random"]
        gap_v3 = v3[seed]["clustered"] - v3[seed]["random"]
        delta = gap_v3 - gap_v2

        if delta > 1e-9:
            widened += 1
            verdict = "WIDENED"
        elif delta < -1e-9:
            narrowed += 1
            verdict = "narrowed"
        else:
            unchanged += 1
            verdict = "unchanged"

        details.append(
            f"  seed {seed:>3}: v2 gap={gap_v2:6.2f}pts  v3 gap={gap_v3:6.2f}pts  "
            f"delta={delta:+6.2f}pts  [{verdict}]"
        )

    print(f"Per-seed gap comparison (v2 standard vs v3 +10% bridges):\n")
    print("\n".join(details))
    print()
    print(f"Widened:   {widened} / {EXPECTED_SEED_COUNT}")
    print(f"Narrowed:  {narrowed} / {EXPECTED_SEED_COUNT}")
    print(f"Unchanged: {unchanged} / {EXPECTED_SEED_COUNT}")
    print()

    is_stable = widened > STABILITY_THRESHOLD
    print(
        f"Stability criterion (widened in >{STABILITY_THRESHOLD} of {EXPECTED_SEED_COUNT} seeds): "
        f"{'PASS - result is stable' if is_stable else 'FAIL - result is NOT stable, likely seed noise'}"
    )

    sys.exit(0 if is_stable else 1)


if __name__ == "__main__":
    main()