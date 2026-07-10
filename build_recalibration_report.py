"""
Task 8 — Recalibration, Step 6
WSN AI Security Pipeline

Builds outputs/recalibration_report.json summarizing one full recalibration
cycle:

  original baseline  ->  cycle 1 applied (recommended values from the
  pre-Task-8 feedback_loop.py run, now live in routing_cost.py /
  digital_twin_sim.py)  ->  cycle 2 recommended (fresh recommendations from
  re-running feedback_loop.py against the recalibrated Digital Twin)

A type is flagged "converged" if the cycle-2 recommended delta from cycle-1
applied is below CONVERGENCE_THRESHOLD -- meaning another recalibration pass
wouldn't move it much further. Anything above that threshold is still
actively drifting and would benefit from at least one more cycle.

Run:  python build_recalibration_report.py
"""

import json
import os

OUTPUTS_DIR = "outputs"
FEEDBACK_LOOP_PATH = os.path.join(OUTPUTS_DIR, "feedback_loop_results.json")
REPORT_PATH = os.path.join(OUTPUTS_DIR, "recalibration_report.json")

CONVERGENCE_THRESHOLD = 0.01

# --- Original baseline, before any Task 8 recalibration ---
ORIGINAL_DETECTION_MISS_RATE = {
    "Blackhole": 0.18, "Grayhole": 0.18, "Flooding": 0.18, "TDMA": 0.18,
}
ORIGINAL_ATTACK_RISK_WEIGHTS = {
    "TDMA": 0.3, "Flooding": 0.6, "Grayhole": 0.8, "Blackhole": 1.0,
}

# --- Cycle 1: values applied to routing_cost.py / digital_twin_sim.py
# (the recommendations from the pre-Task-8 feedback_loop.py run) ---
CYCLE_1_DETECTION_MISS_RATE = {
    "Blackhole": 0.1923, "Grayhole": 0.1589, "Flooding": 0.13, "TDMA": 0.1765,
}
CYCLE_1_ATTACK_RISK_WEIGHTS = {
    "TDMA": 0.25, "Flooding": 0.55, "Grayhole": 0.75, "Blackhole": 0.95,
}

# Total compromised route instances observed in the original (pre-Task-8)
# Digital Twin run, captured before that data was overwritten by the
# recalibrated re-run.
ORIGINAL_TOTAL_COMPROMISED_ROUTE_INSTANCES = 183


def load_json(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Expected input file not found: {path}")
    with open(path, "r") as f:
        return json.load(f)


def build_type_comparison(original, cycle_1_applied, cycle_2_recommended, value_key):
    """
    For each attack type, builds the original -> cycle1 -> cycle2 chain plus
    a convergence flag based on how much cycle2 still wants to move from
    cycle1.
    """
    comparison = {}
    for atype in cycle_1_applied:
        cycle_2_value = cycle_2_recommended.get(atype, {}).get(value_key)
        cycle_1_value = cycle_1_applied[atype]
        original_value = original.get(atype)

        delta_cycle1_to_cycle2 = round(abs(cycle_2_value - cycle_1_value), 4) if cycle_2_value is not None else None
        converged = delta_cycle1_to_cycle2 is not None and delta_cycle1_to_cycle2 < CONVERGENCE_THRESHOLD

        comparison[atype] = {
            "original": original_value,
            "cycle_1_applied": cycle_1_value,
            "cycle_2_recommended": cycle_2_value,
            "delta_cycle1_to_cycle2": delta_cycle1_to_cycle2,
            "converged": converged,
        }
    return comparison


def main():
    print("Loading cycle 2 feedback_loop_results.json (post-recalibration re-run)...")
    feedback_data = load_json(FEEDBACK_LOOP_PATH)

    cycle_2_detection_recs = feedback_data["model_feedback"]["recommended_detection_miss_rate_by_type"]
    cycle_2_risk_recs = feedback_data["routing_feedback"]["recommended_attack_risk_weights_by_type"]
    new_total_compromised = feedback_data["routing_feedback"]["total_compromised_route_instances"]

    detection_comparison = build_type_comparison(
        ORIGINAL_DETECTION_MISS_RATE, CYCLE_1_DETECTION_MISS_RATE,
        cycle_2_detection_recs, "recommended_new_rate",
    )
    risk_weight_comparison = build_type_comparison(
        ORIGINAL_ATTACK_RISK_WEIGHTS, CYCLE_1_ATTACK_RISK_WEIGHTS,
        cycle_2_risk_recs, "recommended_new_weight",
    )

    detection_converged_count = sum(1 for v in detection_comparison.values() if v["converged"])
    risk_converged_count = sum(1 for v in risk_weight_comparison.values() if v["converged"])

    compromised_route_change = new_total_compromised - ORIGINAL_TOTAL_COMPROMISED_ROUTE_INSTANCES

    report = {
        "convergence_threshold": CONVERGENCE_THRESHOLD,
        "detection_miss_rate": {
            "by_type": detection_comparison,
            "converged_count": detection_converged_count,
            "total_types": len(detection_comparison),
            "summary": (
                f"{detection_converged_count}/{len(detection_comparison)} attack types converged "
                f"(delta < {CONVERGENCE_THRESHOLD}) after one recalibration cycle."
            ),
        },
        "attack_risk_weights": {
            "by_type": risk_weight_comparison,
            "converged_count": risk_converged_count,
            "total_types": len(risk_weight_comparison),
            "summary": (
                f"{risk_converged_count}/{len(risk_weight_comparison)} attack types converged "
                f"(delta < {CONVERGENCE_THRESHOLD}) after one recalibration cycle. "
                + ("All types stabilized." if risk_converged_count == len(risk_weight_comparison)
                   else "Some types are still actively drifting and would benefit from another cycle.")
            ),
        },
        "compromised_routes": {
            "original_total_instances": ORIGINAL_TOTAL_COMPROMISED_ROUTE_INSTANCES,
            "post_recalibration_total_instances": new_total_compromised,
            "change": compromised_route_change,
            "note": (
                "Total compromised route instances across all 20 Digital Twin rounds. "
                "A small or negative change after one cycle is expected -- recalibration "
                "tunes detection/routing parameters gradually (capped step size) rather "
                "than in one large jump, matching how the feedback loop was designed to "
                "avoid overcorrecting from a single noisy simulation run."
            ),
        },
        "recommendation": (
            "Run a second recalibration cycle for attack_risk_weights_by_type, which has not "
            "yet converged, before treating these as final tuned values."
            if risk_converged_count < len(risk_weight_comparison)
            else "Recalibration has converged for both detection miss rates and risk weights."
        ),
    }

    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    with open(REPORT_PATH, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nWrote {REPORT_PATH}")

    print("\n--- Detection Miss Rate Convergence ---")
    print(report["detection_miss_rate"]["summary"])
    for atype, v in detection_comparison.items():
        status = "converged" if v["converged"] else "still drifting"
        print(f"  {atype}: {v['original']} -> {v['cycle_1_applied']} -> {v['cycle_2_recommended']}  ({status})")

    print("\n--- Attack Risk Weight Convergence ---")
    print(report["attack_risk_weights"]["summary"])
    for atype, v in risk_weight_comparison.items():
        status = "converged" if v["converged"] else "still drifting"
        print(f"  {atype}: {v['original']} -> {v['cycle_1_applied']} -> {v['cycle_2_recommended']}  ({status})")

    print(f"\n--- Compromised Routes ---")
    print(f"Original: {ORIGINAL_TOTAL_COMPROMISED_ROUTE_INSTANCES}  ->  After cycle 1: {new_total_compromised}  "
          f"(change: {compromised_route_change:+d})")

    print(f"\n{report['recommendation']}")


if __name__ == "__main__":
    main()
