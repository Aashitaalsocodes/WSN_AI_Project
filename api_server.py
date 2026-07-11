from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import json
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://loquacious-sorbet-f6b792.netlify.app",
        "https://wsn-ai-security.netlify.app",
        "http://localhost:5173",  # keep for local dev
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

OUTPUT_DIR = "outputs"

# Map each API route to its actual JSON file
_dashboard_cache = {"data": None}

FILE_MAP = {

    "anomaly-detection-results": "anomaly_detection_results.json",
    "attack-classifier-evaluation": "attack_classifier_evaluation_leakage_free.json",
    "attack-classifier-predictions": "attack_classifier_predictions.json",
    "attack-classifier-test-indices": "attack_classifier_test_indices.json",
    "attack-classification-results": "attack_classification_results.json",
    "attack-detection-evaluation": "attack_detection_evaluation.json",
    "attack-ground-truth": "attack_ground_truth.json",
    "ch-scores": "ch_scores.json",
    "ch-scores-balanced": "ch_scores_balanced.json",
    "ch-scores-nonleaky": "ch_scores_nonleaky.json",
    "dashboard-data": "dashboard_data.json",
    "digital-twin": "digital_twin_results.json",
    "energy-forecast": "energy_forecast.json",
    "energy-forecast-ibrl": "energy_forecast_ibrl.json",
    "energy-forecast-ibrl": "energy_forecast_ibrl.json",
    "evaluation-metrics": "evaluation_metrics.json",
    "failure-probs": "failure_probs.json",
    "feedback-loop": "feedback_loop_results.json",
    "final-pipeline-result": "final_pipeline_result.json",
    "gnn-node-predictions": "gnn_node_predictions.json",
    "gnn-integration-report": "gnn_integration_report.json",
    "gnn-model-report": "gnn_model_report.json",
    "gnn-graph-data": "gnn_graph_data.json",
    "gnn-attention-weights": "gnn_attention_weights.json",
    "mitigation-summary": "mitigation_summary.json",
    "routing-simulation": "routing_simulation.json",
    "recalibration-report": "recalibration_report.json",
    "trust-aware-routing-results": "trust_aware_routing_results.json",
    }

@app.get("/")
def root():
    return {"status": "WSN AI backend running", "endpoints": list(FILE_MAP.keys()) + ["dashboard-formatted"]}


def build_dashboard_payload():
    with open(os.path.join(OUTPUT_DIR, "dashboard_data.json")) as f:
        raw = json.load(f)
    with open(os.path.join(OUTPUT_DIR, "routing_simulation.json")) as f:
        routing_raw = json.load(f)
    with open(os.path.join(OUTPUT_DIR, "digital_twin_results.json")) as f:
        digital_twin_raw = json.load(f)
    with open(os.path.join(OUTPUT_DIR, "feedback_loop_results.json")) as f:
        feedback_loop_raw = json.load(f)
    with open(os.path.join(OUTPUT_DIR, "attack_classification_results.json")) as f:
        multiclass_raw = json.load(f)
    with open(os.path.join(OUTPUT_DIR, "gnn_model_report.json")) as f:
        gnn_model_report_raw = json.load(f)
    with open(os.path.join(OUTPUT_DIR, "mitigation_summary.json")) as f:
        mitigation_summary_raw = json.load(f)
    with open(os.path.join(OUTPUT_DIR, "evaluation_metrics.json")) as f:
        evaluation_metrics_raw = json.load(f)
    

    no = raw["network_overview"]
    ad = raw["attack_detection"]
    rt = raw["routing"]
    en = raw["energy"]
    ch = raw["cluster_heads"]
    pr = raw["pipeline_report"]

    # --- Network Overview ---
    dist = no["attack_distribution"]
    color_map = {"Normal": "#a78bfa", "Grayhole": "#ffb020", "Blackhole": "#ff3860", "TDMA": "#ff3860", "Flooding": "#ff3860"}
    node_distribution = [{"name": k, "value": v, "color": color_map.get(k, "#a78bfa")} for k, v in dist.items()]
    trust_thresholds = [
        {"flagged": int(no["total_attacked"] * 1.4), "percent": round(no["pct_attacked"] * 1.4, 2)},
        {"flagged": int(no["total_attacked"] * 1.1), "percent": round(no["pct_attacked"] * 1.1, 2)},
        {"flagged": no["total_attacked"], "percent": no["pct_attacked"]},
        {"flagged": int(no["total_attacked"] * 0.6), "percent": round(no["pct_attacked"] * 0.6, 2)},
    ]
    network_overview = {
        "totalNodes": no["total_nodes"],
        "attackedNodes": no["total_attacked"],
        "percentAttacked": no["pct_attacked"],
        "classifierF1": ad["xgboost_supervised"]["f1_score"],
        "nodeDistribution": node_distribution,
        "trustThresholds": trust_thresholds,
    }

    # --- Attack Detection ---
    if_rates = ad["isolation_forest"]["detection_rate_by_attack_type"]
    xg_rates = ad["xgboost_supervised"]["detection_rate_by_attack_type"]
    detection_rates = []
    for t in ["blackhole", "flooding", "grayhole", "tdma"]:
        i = if_rates.get(t, {"detected": 0, "total": 1})
        x = xg_rates.get(t, {"detected": 0, "total": 1})
        detection_rates.append({
            "attack": t.capitalize(),
            "isolationForest": round(100 * i["detected"] / max(i["total"], 1), 1),
            "xgboost": round(100 * x["detected"] / max(x["total"], 1), 1),
        })
    cm = ad["xgboost_supervised"]["confusion_matrix"]
    attack_detection = {
        "models": ["Isolation Forest", "XGBoost"],
        "detectionRates": detection_rates,
        "confusionMatrix": {"tp": cm["true_positives"], "fp": cm["false_positives"], "fn": cm["false_negatives"], "tn": cm["true_negatives"]},
    }

    # --- Routing Simulation ---
    baseline = {
        "compromisedPercent": rt["baseline_summary"]["pct_compromised_routes"],
        "routesAffected": rt["baseline_summary"]["routes_through_attacked_node"],
        "totalRoutes": rt["baseline_summary"]["total_routes"],
        "avgHops": rt["baseline_summary"]["avg_hop_count"],
    }
    trust_aware = {
        "compromisedPercent": rt["trust_aware_summary"]["pct_compromised_routes"],
        "routesAffected": rt["trust_aware_summary"]["routes_through_attacked_node"],
        "totalRoutes": rt["trust_aware_summary"]["total_routes"],
        "avgHops": rt["trust_aware_summary"]["avg_hop_count"],
    }
    metrics = {
        "excludedNodes": rt["comparison_vs_baseline"]["excluded_nodes"],
        "hopOverhead": rt["comparison_vs_baseline"]["hop_count_tradeoff"],
        "routesFound": rt["trust_aware_summary"]["routes_found"],
        "trustThreshold": 0.4,
        "networkNodes": rt["num_nodes"],
        "networkEdges": rt["num_edges"],
    }
    sample_routes = []
    for r in routing_raw.get("baseline_routes", [])[:8]:
        sample_routes.append({
            "id": r["route_id"],
            "label": f"Route {r['route_id']}",
            "hops": r["hop_count"],
            "path": r["path"],
            "status": "Compromised" if r["passes_through_attacked_node"] else "Secure",
        })
    routing_simulation = {"baseline": baseline, "trustAware": trust_aware, "metrics": metrics, "sampleRoutes": sample_routes}

    # --- Energy Forecast ---
    voltage_forecast = en["next_voltage_forecast_volts"]
    voltage_data = [{"node": int(k), "voltage": round(v, 3)} for k, v in voltage_forecast.items()]
    voltages = [v["voltage"] for v in voltage_data]
    avg_forecast = sum(voltages) / len(voltages) if voltages else 0
    outlier_nodes = [v["node"] for v in voltage_data if v["voltage"] < 2.0 or v["voltage"] > 2.5]
    cluster_heads_list = [{"id": cid, "rank": i + 1, "selected": i == 0} for i, cid in enumerate(ch["top_candidates"])]
    energy_forecast = {
        "model": en["model"],
        "valMSE": en["val_mse"],
        "avgForecast": avg_forecast,
        "dataSource": en["data_source"],
        "sensorNodes": len(voltage_data),
        "minVoltage": round(min(voltages), 3) if voltages else 0,
        "maxVoltage": round(max(voltages), 3) if voltages else 0,
        "voltageData": voltage_data,
        "outlierNodes": outlier_nodes,
        "clusterHeads": cluster_heads_list,
        "defaultThreshold": 2.0,
    }

    # --- Pipeline Report ---
    action_lines = [l.replace("Immediate Action 1:", "").replace("Immediate Action 2:", "").strip() for l in pr["attack_alert"].split("\n") if "Action" in l]
    pipeline_report = {
        "flaggedNodes": no["total_attacked"],
        "avgTrustScore": 0.7484,
        "trustThreshold": 0.4,
        "llmModel": "Ollama LLM",
        "healthReport": pr["health_report"],
        "attackAlert": {"title": pr["attack_alert"].split("\n")[0], "actions": action_lines},
        "adaptivePolicies": [
            {"icon": "route", "title": "Adaptive Routing", "description": "Reroute traffic away from low-trust nodes."},
            {"icon": "sliders", "title": "Dynamic Thresholds", "description": "Adjust trust threshold based on network conditions."},
            {"icon": "battery", "title": "Duty Cycling", "description": "Rotate high-energy nodes to conserve power."},
            {"icon": "scan", "title": "Anomaly Scanning", "description": "Continuously scan for anomalous behavior patterns."},
        ],
        "simulationSteps": [
            "Collecting node telemetry...",
            "Running anomaly detection...",
            "Scoring trust values...",
            "Updating routing policies...",
            "Pipeline complete.",
        ],
    }

 # --- Digital Twin ---
    digital_twin = {"rounds": digital_twin_raw["rounds"]}
 # --- Feedback Loop ---
    feedback_loop = {
        "detectionRateRecommendations": feedback_loop_raw["model_feedback"]["recommended_detection_miss_rate_by_type"],
        "riskWeightRecommendations": feedback_loop_raw["routing_feedback"]["recommended_attack_risk_weights_by_type"],
        "totalCompromisedRouteInstances": feedback_loop_raw["routing_feedback"]["total_compromised_route_instances"],
        "note": feedback_loop_raw["note"],
    }
# --- Multiclass Classification (Task 2) ---
    attack_type_counts = {}
    confidence_sums = {}
    for record in multiclass_raw.values():
        atype = record["attack_type"]
        attack_type_counts[atype] = attack_type_counts.get(atype, 0) + 1
        confidence_sums.setdefault(atype, []).append(record["confidence"])

    avg_confidence_by_type = {
        atype: round(sum(vals) / len(vals), 4)
        for atype, vals in confidence_sums.items()
    }

    multiclass_classification = {
        "attackTypeCounts": attack_type_counts,
        "avgConfidenceByType": avg_confidence_by_type,
        "macroF1": 0.840,
        "totalRecords": len(multiclass_raw),
    }
   
    # --- GNN Model Report (Task 7) ---
    gnn_model_report = gnn_model_report_raw

    # --- Mitigation Summary (Task 3) ---
    mitigation_summary = mitigation_summary_raw
    # --- Evaluation Metrics (Task 10) ---
    evaluation_metrics = evaluation_metrics_raw
    return {
        "networkOverview": network_overview,
        "attackDetection": attack_detection,
        "routingSimulation": routing_simulation,
        "energyForecast": energy_forecast,
        "pipelineReport": pipeline_report,
        "digitalTwin": digital_twin,
        "feedbackLoop": feedback_loop,
        "multiclassClassification": multiclass_classification,
        "gnnModelReport": gnn_model_report,
        "mitigationSummary": mitigation_summary,
        "gnnGraph": {
            "numNodes": 11120,
            "numEdges": 55585,
            "pctAttacked": 10.09,
            "featureNames": ["attack_probability_mean", "attack_probability_max", "composite_risk_score_mean", "packet_delivery_ratio_mean", "distance_to_ch_norm", "is_cluster_head"],
        },
       "evaluationMetrics": evaluation_metrics,
        "ticker": f"{no['total_nodes']:,} nodes monitored — {no['total_attacked']:,} attacks detected — F1 {ad['xgboost_supervised']['f1_score']:.2f}",
    }
@app.get("/api/dashboard-formatted")
def get_dashboard_formatted():
    try:
        if _dashboard_cache["data"] is None:
            _dashboard_cache["data"] = build_dashboard_payload()
        return _dashboard_cache["data"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/{key}")
def get_json(key: str):
    if key not in FILE_MAP:
        raise HTTPException(status_code=404, detail="Unknown endpoint")
    filepath = os.path.join(OUTPUT_DIR, FILE_MAP[key])
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail=f"{filepath} not found")
    with open(filepath, "r") as f:
        return json.load(f)