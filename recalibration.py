"""
Task 8 — Recalibration
WSN AI Security Pipeline

Step 1: Read outputs/feedback_loop_results.json (Task 6 output) and extract
the recommended DETECTION_MISS_RATE and attack_risk_weights_by_type values.

Step 2: Apply those recommended values to routing_cost.py and
digital_twin_sim.py via a controlled, matched text replacement — dry run by
default (writes to new *_recalibrated.py files), only overwrites originals
with an explicit --apply flag.
"""

import json
import os

OUTPUTS_DIR = "outputs"
FEEDBACK_LOOP_PATH = os.path.join(OUTPUTS_DIR, "feedback_loop_results.json")


def load_json(path):
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Expected input file not found: {path}\n"
            f"Make sure feedback_loop.py has been run first (Task 6 output)."
        )
    with open(path, "r") as f:
        return json.load(f)


def extract_recommendations(feedback_data):
    """
    Pulls the two recommendation blocks out of feedback_loop_results.json
    and returns them as simple {attack_type: value} dicts, stripped of the
    extra analysis fields (miss counts, shares, etc.) — just the numbers
    we'll actually apply in Step 2.
    """
    detection_recs_raw = feedback_data["model_feedback"]["recommended_detection_miss_rate_by_type"]
    risk_weight_recs_raw = feedback_data["routing_feedback"]["recommended_attack_risk_weights_by_type"]

    recommended_detection_miss_rates = {
        atype: rec["recommended_new_rate"]
        for atype, rec in detection_recs_raw.items()
    }
    recommended_risk_weights = {
        atype: rec["recommended_new_weight"]
        for atype, rec in risk_weight_recs_raw.items()
    }

    return recommended_detection_miss_rates, recommended_risk_weights


def main():
    print("Step 1: Loading feedback_loop_results.json...")
    feedback_data = load_json(FEEDBACK_LOOP_PATH)

    recommended_detection_miss_rates, recommended_risk_weights = extract_recommendations(feedback_data)

    print("\nRecommended DETECTION_MISS_RATE by attack type:")
    for atype, rate in recommended_detection_miss_rates.items():
        print(f"  {atype}: {rate}")

    print("\nRecommended attack_risk_weights_by_type:")
    for atype, weight in recommended_risk_weights.items():
        print(f"  {atype}: {weight}")

    print("\nStep 1 complete. Nothing has been modified yet — this just confirms")
    print("the recommended values are read correctly before Step 2 applies them.")

    return recommended_detection_miss_rates, recommended_risk_weights


ROUTING_COST_PATH = "routing_cost.py"
DIGITAL_TWIN_PATH = "digital_twin_sim.py"

# Exact current dict block in routing_cost.py -- matched verbatim so the
# replacement only touches this block, nothing else in the file.
CURRENT_ATTACK_RISK_WEIGHT_BLOCK = '''ATTACK_RISK_WEIGHT = {
    "Normal": 0.0,
    "TDMA": 0.3,
    "Flooding": 0.6,
    "Grayhole": 0.8,
    "Blackhole": 1.0,
}'''

# Exact current line in digital_twin_sim.py
CURRENT_DETECTION_MISS_RATE_LINE = "    DETECTION_MISS_RATE = 0.18"
CURRENT_DETECTION_USAGE_LINE = "            detected = random.random() > DETECTION_MISS_RATE"


def build_new_attack_risk_weight_block(recommended_risk_weights):
    """Builds the replacement ATTACK_RISK_WEIGHT dict text, same formatting/quote
    style as the original, Normal always pinned at 0.0 (never attacked -> no recommendation exists for it)."""
    lines = ['ATTACK_RISK_WEIGHT = {', '    "Normal": 0.0,']
    # keep original key order: TDMA, Flooding, Grayhole, Blackhole
    for atype in ["TDMA", "Flooding", "Grayhole", "Blackhole"]:
        value = recommended_risk_weights.get(atype)
        if value is None:
            raise KeyError(f"No recommended risk weight found for {atype}")
        lines.append(f'    "{atype}": {value},')
    lines.append('}')
    return "\n".join(lines)


def build_new_detection_miss_rate_block(recommended_detection_miss_rates):
    """
    Converts the flat DETECTION_MISS_RATE into a per-type dict. Attack type
    strings in digital_twin_sim.py are lowercase ("blackhole"), so keys are
    lowercased here to match simulate_round()'s usage.
    """
    lines = ["    DETECTION_MISS_RATE_BY_TYPE = {"]
    for atype in ["blackhole", "grayhole", "flooding", "tdma"]:
        # recommended dict keys are capitalized (Blackhole, Grayhole, ...)
        cap_key = atype.capitalize() if atype != "tdma" else "TDMA"
        value = recommended_detection_miss_rates.get(cap_key)
        if value is None:
            raise KeyError(f"No recommended detection miss rate found for {cap_key}")
        lines.append(f'        "{atype}": {value},')
    lines.append("    }")
    return "\n".join(lines)


def apply_recalibration(recommended_detection_miss_rates, recommended_risk_weights, apply=False):
    """
    Reads routing_cost.py and digital_twin_sim.py, builds updated versions
    with the recommended values applied, and writes them either to new
    "_recalibrated.py" files (dry run, default) or overwrites the originals
    (apply=True). Never silently overwrites without the explicit flag.
    """
    # --- routing_cost.py ---
    with open(ROUTING_COST_PATH, "r") as f:
        routing_src = f.read()

    if CURRENT_ATTACK_RISK_WEIGHT_BLOCK not in routing_src:
        raise ValueError(
            "Could not find the expected ATTACK_RISK_WEIGHT block in routing_cost.py -- "
            "the file may have changed since this script was written. Paste the current "
            "block back to Claude to update the matcher before retrying."
        )
    new_block = build_new_attack_risk_weight_block(recommended_risk_weights)
    new_routing_src = routing_src.replace(CURRENT_ATTACK_RISK_WEIGHT_BLOCK, new_block)

    # --- digital_twin_sim.py ---
    with open(DIGITAL_TWIN_PATH, "r") as f:
        twin_src = f.read()

    if CURRENT_DETECTION_MISS_RATE_LINE not in twin_src:
        raise ValueError(
            "Could not find the expected DETECTION_MISS_RATE line in digital_twin_sim.py -- "
            "the file may have changed since this script was written. Paste the current "
            "line back to Claude to update the matcher before retrying."
        )
    if CURRENT_DETECTION_USAGE_LINE not in twin_src:
        raise ValueError(
            "Could not find the expected DETECTION_MISS_RATE usage line in digital_twin_sim.py."
        )

    new_detection_block = build_new_detection_miss_rate_block(recommended_detection_miss_rates)
    new_usage_line = (
        "            detected = random.random() > DETECTION_MISS_RATE_BY_TYPE[attack_type]"
    )
    new_twin_src = twin_src.replace(CURRENT_DETECTION_MISS_RATE_LINE, new_detection_block)
    new_twin_src = new_twin_src.replace(CURRENT_DETECTION_USAGE_LINE, new_usage_line)

    if apply:
        routing_out_path = ROUTING_COST_PATH
        twin_out_path = DIGITAL_TWIN_PATH
        print("\napply=True -- OVERWRITING original source files.")
    else:
        routing_out_path = "routing_cost_recalibrated.py"
        twin_out_path = "digital_twin_sim_recalibrated.py"
        print(f"\nDry run (apply=False) -- writing to {routing_out_path} and {twin_out_path}")
        print("Review these against the originals, then re-run with apply=True to make it real.")

    with open(routing_out_path, "w") as f:
        f.write(new_routing_src)
    with open(twin_out_path, "w") as f:
        f.write(new_twin_src)

    print(f"Wrote {routing_out_path}")
    print(f"Wrote {twin_out_path}")


if __name__ == "__main__":
    import sys
    detection_rates, risk_weights = main()

    apply_flag = "--apply" in sys.argv
    print("\n" + "=" * 60)
    print("Step 2: Applying recalibration" + (" (LIVE)" if apply_flag else " (DRY RUN)"))
    print("=" * 60)
    apply_recalibration(detection_rates, risk_weights, apply=apply_flag)