import json
import os

def load(path):
    with open(path) as f:
        return json.load(f)

print("Loading output files...")

final = load('outputs/final_pipeline_result.json')
attack_eval = load('outputs/attack_detection_evaluation.json')
attack_eval_clean = load('outputs/attack_classifier_evaluation_leakage_free.json')
energy = load('outputs/energy_forecast_ibrl.json')
ch_scores = load('outputs/ch_scores_nonleaky.json')
routing = load('outputs/routing_simulation.json')
trust_aware = load('outputs/trust_aware_routing_results.json')

print("Building dashboard_data.json...")

dashboard = {
    "project": "WSN AI Security Pipeline",
    "network_overview": {
        "total_nodes": 374661,
        "attack_distribution": {
            "Normal": 340066,
            "Grayhole": 14596,
            "Blackhole": 10049,
            "TDMA": 6638,
            "Flooding": 3312
        },
        "total_attacked": 34595,
        "pct_attacked": round(34595 / 374661 * 100, 2)
    },
    "attack_detection": {
        "isolation_forest": attack_eval,
        "xgboost_supervised": attack_eval_clean
    },
    "routing": {
        "baseline_summary": routing["baseline_summary"],
        "trust_aware_summary": trust_aware["trust_aware_summary"],
        "comparison_vs_baseline": trust_aware["comparison_vs_baseline"],
        "num_nodes": routing["num_nodes"],
        "num_edges": routing["num_edges"]
    },
    "energy": energy,
    "cluster_heads": {
        "top_candidates": ch_scores.get("top_candidates", []),
        "model_metrics": ch_scores.get("model_metrics", {})
    },
    "pipeline_report": {
        "health_report": final.get("health_report", ""),
        "attack_alert": final.get("attack_alert", ""),
        "recommendations": final.get("recommendations", "")
    }
}

os.makedirs("outputs", exist_ok=True)
with open("outputs/dashboard_data.json", "w") as f:
    json.dump(dashboard, f, indent=2)

print("Done — outputs/dashboard_data.json created")
print(f"File size: {os.path.getsize('outputs/dashboard_data.json')} bytes")