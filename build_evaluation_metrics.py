"""
Task 10 -- Evaluation Metrics Module
WSN AI Security Pipeline

Consumes existing pipeline outputs and produces outputs/evaluation_metrics.json
with three sections: security, energy, network_performance -- matching the
metric list from the research roadmap handoff.

Inputs (all optional except classification report + routing cost; missing
files degrade gracefully with a "not_available" note rather than crashing,
since not every metric has a source file yet):

  outputs/classification_report.json    <- Task 2 (attack classifier)
  outputs/routing_cost_results.json     <- Task 4 (cost-aware routing)
  outputs/feedback_loop_results.json    <- Task 6 (feedback loop)
  outputs/recalibration_report.json     <- Task 8 (recalibration)
  outputs/digital_twin_results.json     <- Digital Twin (round-by-round energy/attack sim)
                                            NOT YET WIRED IN -- see note below.

Run:  python build_evaluation_metrics.py
"""

import json
import os

OUTPUTS_DIR = "outputs"
CLASSIFICATION_REPORT_PATH = os.path.join(OUTPUTS_DIR, "attack_classifier_multiclass_evaluation.json")
ROUTING_COST_PATH = os.path.join(OUTPUTS_DIR, "routing_cost_results.json")
FEEDBACK_LOOP_PATH = os.path.join(OUTPUTS_DIR, "feedback_loop_results.json")
RECALIBRATION_REPORT_PATH = os.path.join(OUTPUTS_DIR, "recalibration_report.json")
DIGITAL_TWIN_PATH = os.path.join(OUTPUTS_DIR, "digital_twin_results.json")
EVAL_METRICS_PATH = os.path.join(OUTPUTS_DIR, "evaluation_metrics.json")


def load_json_optional(path):
    """Returns parsed JSON, or None (with a printed note) if the file is missing."""
    if not os.path.exists(path):
        print(f"  [skip] {path} not found -- metrics depending on it will be marked not_available")
        return None
    with open(path, "r") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# SECURITY METRICS
# ---------------------------------------------------------------------------

def compute_security_metrics(classification_report, routing_cost, recalibration_report):
    metrics = {}

    if classification_report:
        cr = classification_report["classification_report"]
        labels = classification_report["labels"]
        cm = classification_report["confusion_matrix"]

        metrics["attack_detection_accuracy"] = cr["accuracy"]
        metrics["macro_f1"] = classification_report["macro_f1"]
        metrics["weighted_f1"] = classification_report["weighted_f1"]
        metrics["precision_recall_f1_by_type"] = {
            label: {
                "precision": cr[label]["precision"],
                "recall": cr[label]["recall"],
                "f1_score": cr[label]["f1-score"],
                "support": cr[label]["support"],
            }
            for label in labels
        }

        normal_idx = labels.index("Normal")
        fpr_by_type = {}
        for i, label in enumerate(labels):
            if label == "Normal":
                continue
            col_sum = sum(cm[r][i] for r in range(len(labels)))
            true_positives = cm[i][i]
            false_positives = col_sum - true_positives
            actual_negatives = sum(sum(row) for row in cm) - sum(cm[i])
            fpr_by_type[label] = round(false_positives / actual_negatives, 4) if actual_negatives else None

        metrics["false_positive_rate_by_type"] = fpr_by_type

        missed_as_normal = sum(cm[i][normal_idx] for i in range(len(labels)) if i != normal_idx)
        total_actual_attacks = sum(sum(cm[i]) for i in range(len(labels)) if i != normal_idx)
        metrics["attack_traffic_missed_as_normal_rate"] = (
            round(missed_as_normal / total_actual_attacks, 4) if total_actual_attacks else None
        )
    else:
        metrics["note"] = "classification_report.json not found -- detection accuracy/precision/recall/F1/FPR not available"

    if routing_cost:
        summary = routing_cost["summary"]
        metrics["packet_delivery_ratio_under_attack"] = round(
            summary["routes_found"] / summary["total_routes"], 4
        )
        metrics["successful_attack_mitigation_rate"] = {
            "pct_compromised_routes_cost_aware": summary["pct_compromised_routes"],
            "pct_compromised_routes_baseline": summary["comparison_vs_baseline"]["baseline_pct_compromised"],
            "improvement_percentage_points": summary["comparison_vs_baseline"]["improvement_percentage_points"],
            "note": (
                "Mitigation rate = reduction in compromised routes achieved by cost-aware "
                "routing vs. naive baseline routing, both measured on the same 200 source/dest pairs."
            ),
        }
    else:
        metrics["packet_delivery_ratio_under_attack"] = "not_available (routing_cost_results.json missing)"
        metrics["successful_attack_mitigation_rate"] = "not_available (routing_cost_results.json missing)"

    if recalibration_report:
        metrics["recalibration_convergence"] = {
            "detection_miss_rate_converged_count": recalibration_report["detection_miss_rate"]["converged_count"],
            "detection_miss_rate_total_types": recalibration_report["detection_miss_rate"]["total_types"],
            "attack_risk_weights_converged_count": recalibration_report["attack_risk_weights"]["converged_count"],
            "attack_risk_weights_total_types": recalibration_report["attack_risk_weights"]["total_types"],
        }

    return metrics


# ---------------------------------------------------------------------------
# ENERGY METRICS
# ---------------------------------------------------------------------------

def compute_energy_metrics(digital_twin_results):
    unavailable_core = {
        "average_residual_energy": "not_available",
        "energy_consumption_per_packet": "not_available",
        "network_lifetime": "not_available",
        "first_node_death_round": "not_available",
        "half_node_death_round": "not_available",
        "last_node_death_round": "not_available",
    }

    if not digital_twin_results:
        return {**unavailable_core, "note": "digital_twin_results.json not found."}

    rounds = digital_twin_results.get("rounds", [])
    if not rounds:
        return {**unavailable_core, "note": "digital_twin_results.json has no 'rounds' data."}

    # Real schema check: digital_twin_results.json's rounds contain
    # attacked_nodes, avg_trust_score, compromised_routes_pct, avg_hop_count --
    # there is NO per-node energy_remaining / residual-battery field. FND/HND/LND
    # and per-packet energy consumption are genuinely not computable from this
    # file as it stands; the Digital Twin only tracks trust + compromise per round.
    trust_by_round = [r["avg_trust_score"] for r in rounds if "avg_trust_score" in r]
    compromised_pct_by_round = [r["compromised_routes_pct"] for r in rounds if "compromised_routes_pct" in r]

    proxies = {
        "avg_trust_score_first_round": trust_by_round[0] if trust_by_round else None,
        "avg_trust_score_last_round": trust_by_round[-1] if trust_by_round else None,
        "avg_trust_score_decline": (
            round(trust_by_round[0] - trust_by_round[-1], 4) if len(trust_by_round) >= 2 else None
        ),
        "compromised_routes_pct_first_round": compromised_pct_by_round[0] if compromised_pct_by_round else None,
        "compromised_routes_pct_last_round": compromised_pct_by_round[-1] if compromised_pct_by_round else None,
        "compromised_routes_pct_trend": compromised_pct_by_round,
        "note_on_proxies": (
            "Network-health proxies over the 20 simulation rounds, not true energy metrics -- "
            "trust decline / compromise rate over time stands in for network degradation in the "
            "absence of energy data."
        ),
    }

    return {
        **unavailable_core,
        "network_health_proxies": proxies,
        "note": (
            "digital_twin_results.json has round-by-round attack/trust/routing data but does NOT "
            "include per-node energy_remaining or residual battery values. FND/HND/LND, average "
            "residual energy, and energy-per-packet genuinely cannot be computed from this file. "
            "digital_twin_sim.py needs to additionally export per-node energy_remaining at each "
            "round to make these computable -- this is a gap in the simulation's output, worth "
            "flagging before the paper's energy section is written."
        ),
    }


# ---------------------------------------------------------------------------
# NETWORK PERFORMANCE METRICS
# ---------------------------------------------------------------------------

def compute_network_performance_metrics(routing_cost):
    if not routing_cost:
        return {
            "throughput": "not_available",
            "end_to_end_delay_proxy_avg_hops": "not_available",
            "routing_overhead": "not_available",
            "note": "routing_cost_results.json not found",
        }

    summary = routing_cost["summary"]
    baseline = summary["comparison_vs_baseline"]

    return {
        "end_to_end_delay_proxy_avg_hops": {
            "cost_aware_avg_hops": summary["avg_hop_count"],
            "baseline_avg_hops": baseline["baseline_avg_hops"],
            "hop_count_tradeoff": baseline["hop_count_tradeoff"],
            "note": (
                "True end-to-end delay needs per-hop latency data, which the routing sim "
                "doesn't currently model. Avg hop count is used as a proxy -- more hops "
                "generally means more delay, all else equal."
            ),
        },
        "routing_overhead": {
            "avg_total_cost": summary["avg_total_cost"],
            "note": (
                "'total_cost' here is the routing-cost-formula value (distance + energy + "
                "attack risk / trust), not control-packet overhead in the classic WSN sense. "
                "True routing overhead (e.g. route-discovery control packets per data packet) "
                "isn't currently instrumented in the routing sim."
            ),
        },
        "throughput": "not_available -- routing sim doesn't currently model packet-level throughput over time",
        "avg_trust_on_path": summary["avg_trust_on_path"],
    }


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    print("Loading pipeline outputs...")
    classification_report = load_json_optional(CLASSIFICATION_REPORT_PATH)
    routing_cost = load_json_optional(ROUTING_COST_PATH)
    feedback_loop = load_json_optional(FEEDBACK_LOOP_PATH)
    recalibration_report = load_json_optional(RECALIBRATION_REPORT_PATH)
    digital_twin_results = load_json_optional(DIGITAL_TWIN_PATH)

    report = {
        "security": compute_security_metrics(classification_report, routing_cost, recalibration_report),
        "energy": compute_energy_metrics(digital_twin_results),
        "network_performance": compute_network_performance_metrics(routing_cost),
    }

    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    with open(EVAL_METRICS_PATH, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nWrote {EVAL_METRICS_PATH}")

    print("\n--- Security ---")
    if "attack_detection_accuracy" in report["security"]:
        print(f"Accuracy: {report['security']['attack_detection_accuracy']:.4f}")
        print(f"Macro F1: {report['security']['macro_f1']:.4f}")
        print(f"Weighted F1: {report['security']['weighted_f1']:.4f}")
    if isinstance(report["security"].get("successful_attack_mitigation_rate"), dict):
        m = report["security"]["successful_attack_mitigation_rate"]
        print(f"Mitigation improvement: {m['improvement_percentage_points']} pts "
              f"({m['pct_compromised_routes_baseline']}% -> {m['pct_compromised_routes_cost_aware']}%)")

    print("\n--- Energy ---")
    print(report["energy"].get("note", "computed"))

    print("\n--- Network Performance ---")
    if isinstance(report["network_performance"].get("end_to_end_delay_proxy_avg_hops"), dict):
        h = report["network_performance"]["end_to_end_delay_proxy_avg_hops"]
        print(f"Avg hops (cost-aware vs baseline): {h['cost_aware_avg_hops']} vs {h['baseline_avg_hops']} "
              f"(tradeoff: +{h['hop_count_tradeoff']})")


if __name__ == "__main__":
    main()