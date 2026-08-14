"""
Task 6 — Feedback Loop: Digital Twin -> Model + Routing update
WSN AI Security Pipeline

Built against the REAL schemas confirmed from actual output files:

- outputs/digital_twin_results.json:
    {
      "num_rounds": 20,
      "rounds": [
        {
          "round": 0,
          "attacked_nodes": [...],            # full list, topology node IDs e.g. "114987"
          "attacked_node_types": {"114987": "blackhole", ...},
          "attacked_count": 44,
          "excluded_nodes": [...],
          "excluded_node_count": 41,
          "missed_detections": [...],         # attacked but not excluded
          "avg_trust_score": 0.7434,
          "compromised_routes_pct": 1.0,
          "compromised_routes_detail": [
             {"source": ..., "destination": ..., "path": [...],
              "attacked_intermediate_nodes": [...], "attack_types": [...]}
          ],
          "avg_hop_count": 4.25
        }, ...
      ]
    }

- outputs/routing_cost_results.json:
    {
      "routes": [...],
      "summary": {
        ...,
        "weights_used": {
          "W_DISTANCE": 1.0, "W_ENERGY": 1.0, "W_ATTACK": 2.0,
          "attack_risk_weights_by_type": {
            "Normal": 0.0, "TDMA": 0.3, "Flooding": 0.6,
            "Grayhole": 0.8, "Blackhole": 1.0
          }
        }
      }
    }

IMPORTANT: outputs/attack_classification_results.json (keyed by row_index,
values contain node_id like "node_101000") is a DIFFERENT ID space than the
Digital Twin's topology node IDs (e.g. "114987") — confirmed zero overlap,
same issue flagged in the Task 5 GNN handoff. So this feedback loop does NOT
attempt to join Twin results into the real classifier's per-node scores.
Instead:

  MODEL FEEDBACK  -> recommends a per-attack-type DETECTION_MISS_RATE
                      adjustment for digital_twin_sim.py itself (the Twin's
                      own simulated detector), based on which attack types
                      it's actually missing most in practice.

  ROUTING FEEDBACK -> recommends adjustments to attack_risk_weights_by_type
                      in routing_cost.py, based on which attack types
                      actually show up in compromised routes most often.

This script does NOT auto-edit digital_twin_sim.py or routing_cost.py —
it writes recommended new values to outputs/feedback_loop_results.json.
Applying them is a manual (reviewed) edit, consistent with how Task 2/3/4
issues were flagged-not-blindly-auto-fixed in this project so far.

Run:  python feedback_loop.py
"""

import json
import os
from collections import defaultdict

OUTPUTS_DIR = "outputs"
TWIN_PATH = os.path.join(OUTPUTS_DIR, "digital_twin_results.json")
ROUTING_PATH = os.path.join(OUTPUTS_DIR, "routing_cost_results.json")
OUT_PATH = os.path.join(OUTPUTS_DIR, "feedback_loop_results.json")

# Current baseline values (from digital_twin_sim.py / routing_cost.py) —
# used as the starting point for recommended adjustments.
CURRENT_DETECTION_MISS_RATE_BY_TYPE = {
    "Blackhole": 0.2469, "Grayhole": 0.1038, "Flooding": 0.0103, "TDMA": 0.1343
}
CURRENT_ATTACK_RISK_WEIGHTS = {
    "Normal": 0.0, "TDMA": 0.1354, "Flooding": 0.25, "Grayhole": 0.45, "Blackhole": 0.65
}
# Twin's attack_type strings are lowercase ("blackhole"), routing's are
# capitalized ("Blackhole") — normalize here so they join correctly.
TYPE_NORMALIZE = {
    "blackhole": "Blackhole", "grayhole": "Grayhole",
    "tdma": "TDMA", "flooding": "Flooding", "none": "Normal",
}

# How aggressively to move recommended values per unit of observed miss/compromise
# rate above expectation. Kept small and capped so one script run can't wildly
# swing behavior in a single pass.
MISS_RATE_LEARNING_STEP = 0.05
RISK_WEIGHT_LEARNING_STEP = 0.05
MAX_MISS_RATE = 0.5
MAX_RISK_WEIGHT = 1.0


def load_json(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Expected input file not found: {path}")
    with open(path, "r") as f:
        return json.load(f)


def analyze_miss_rates_by_type(twin_data):
    """
    For each attack type, compute: of all times a node of that type was
    attacked, what fraction ended up in missed_detections?
    """
    attacked_by_type = defaultdict(int)
    missed_by_type = defaultdict(int)

    for rnd in twin_data.get("rounds", []):
        attacked_types = rnd.get("attacked_node_types", {})
        missed_set = set(rnd.get("missed_detections", []))
        for node_id, atype in attacked_types.items():
            norm_type = TYPE_NORMALIZE.get(atype.lower(), atype)
            attacked_by_type[norm_type] += 1
            if node_id in missed_set:
                missed_by_type[norm_type] += 1

    miss_rate_by_type = {}
    for atype, total in attacked_by_type.items():
        missed = missed_by_type.get(atype, 0)
        miss_rate_by_type[atype] = {
            "times_attacked": total,
            "times_missed": missed,
            "observed_miss_rate": round(missed / total, 4) if total else 0.0,
        }
    return miss_rate_by_type


def analyze_compromise_rates_by_type(twin_data):
    """
    For each attack type, count how often it showed up as the cause of a
    compromised route (i.e. an attacked intermediate node on a chosen path).
    """
    compromise_count_by_type = defaultdict(int)
    total_compromised_routes = 0

    for rnd in twin_data.get("rounds", []):
        for route in rnd.get("compromised_routes_detail", []):
            total_compromised_routes += 1
            for atype in route.get("attack_types", []):
                norm_type = TYPE_NORMALIZE.get(atype.lower(), atype)
                compromise_count_by_type[norm_type] += 1

    return dict(compromise_count_by_type), total_compromised_routes


def recommend_detection_miss_rates(miss_rate_by_type):
    """
    If a type's observed miss rate is above the current flat 0.18 baseline,
    that means the Twin's simple detector is under-modeling how hard that
    attack type is to catch (or vice versa if below). Nudge a per-type
    recommended DETECTION_MISS_RATE toward the observed rate, capped.
    """
    recommendations = {}
    for atype, stats in miss_rate_by_type.items():
        if atype == "Normal":
            continue  # Normal nodes are never "missed" in a meaningful sense
        observed = stats["observed_miss_rate"]
        current = CURRENT_DETECTION_MISS_RATE_BY_TYPE.get(atype, 0.18)
        direction = 1 if observed > current else -1
        step = min(abs(observed - current), MISS_RATE_LEARNING_STEP) * direction
        new_rate = max(0.0, min(MAX_MISS_RATE, round(current + step, 4)))
        recommendations[atype] = {
            "current_flat_rate": current,
            "observed_miss_rate": observed,
            "recommended_new_rate": new_rate,
        }
    return recommendations


def recommend_risk_weights(compromise_count_by_type, total_compromised_routes):
    """
    If a type accounts for a disproportionate share of compromised routes
    relative to its current attack_risk_weight, nudge that weight up
    (routing should penalize it harder), capped at MAX_RISK_WEIGHT.
    """
    recommendations = {}
    if total_compromised_routes == 0:
        return recommendations

    for atype, current_weight in CURRENT_ATTACK_RISK_WEIGHTS.items():
        if atype == "Normal":
            continue
        count = compromise_count_by_type.get(atype, 0)
        share = round(count / total_compromised_routes, 4) if total_compromised_routes else 0.0
        # if this type's share of compromises exceeds its current weight
        # (normalized against the max weight of 1.0), nudge upward
        direction = 1 if share > current_weight else -1
        step = min(abs(share - current_weight), RISK_WEIGHT_LEARNING_STEP) * direction
        new_weight = max(0.0, min(MAX_RISK_WEIGHT, round(current_weight + step, 4)))
        recommendations[atype] = {
            "current_weight": current_weight,
            "share_of_compromised_routes": share,
            "compromise_count": count,
            "recommended_new_weight": new_weight,
        }
    return recommendations


def main():
    print("Loading Digital Twin and routing cost outputs...")
    twin_data = load_json(TWIN_PATH)
    routing_data = load_json(ROUTING_PATH)

    miss_rate_by_type = analyze_miss_rates_by_type(twin_data)
    compromise_count_by_type, total_compromised_routes = analyze_compromise_rates_by_type(twin_data)

    print(f"Attack types observed: {list(miss_rate_by_type.keys())}")
    print(f"Total compromised route instances across all rounds: {total_compromised_routes}")

    detection_rate_recs = recommend_detection_miss_rates(miss_rate_by_type)
    risk_weight_recs = recommend_risk_weights(compromise_count_by_type, total_compromised_routes)

    result = {
        "note": (
            "Model feedback tunes the Digital Twin's OWN simulated detector "
            "(DETECTION_MISS_RATE in digital_twin_sim.py), not the real "
            "attack_classifier_multiclass.py output — those use a different, "
            "non-overlapping node ID space (topology IDs vs WSN-DS node_ids)."
        ),
        "model_feedback": {
            "miss_rate_analysis_by_type": miss_rate_by_type,
            "recommended_detection_miss_rate_by_type": detection_rate_recs,
        },
        "routing_feedback": {
            "compromise_count_by_type": compromise_count_by_type,
            "total_compromised_route_instances": total_compromised_routes,
            "recommended_attack_risk_weights_by_type": risk_weight_recs,
        },
    }

    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    with open(OUT_PATH, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\nWrote {OUT_PATH}")

    print("\n--- Recommended DETECTION_MISS_RATE changes (digital_twin_sim.py) ---")
    for atype, rec in detection_rate_recs.items():
        print(f"  {atype}: {rec['current_flat_rate']} -> {rec['recommended_new_rate']} "
              f"(observed miss rate: {rec['observed_miss_rate']})")

    print("\n--- Recommended attack_risk_weights_by_type changes (routing_cost.py) ---")
    for atype, rec in risk_weight_recs.items():
        print(f"  {atype}: {rec['current_weight']} -> {rec['recommended_new_weight']} "
              f"(share of compromised routes: {rec['share_of_compromised_routes']})")

    print("\nThese are recommendations only — review before manually updating")
    print("DETECTION_MISS_RATE / attack_risk_weights_by_type in the source scripts.")
    print("Next: wire outputs/feedback_loop_results.json into api_server.py's FILE_MAP.")


if __name__ == "__main__":
    main()
