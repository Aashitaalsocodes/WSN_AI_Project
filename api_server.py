from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import json
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://loquacious-sorbet-f6b792.netlify.app",
        "http://localhost:5173",  # keep for local dev
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

OUTPUT_DIR = "outputs"

# Map each API route to its actual JSON file
FILE_MAP = {
    "anomaly-detection-results": "anomaly_detection_results.json",
    "attack-classifier-evaluation": "attack_classifier_evaluation_leakage_free.json",
    "attack-classifier-predictions": "attack_classifier_predictions.json",
    "attack-classifier-test-indices": "attack_classifier_test_indices.json",
    "attack-detection-evaluation": "attack_detection_evaluation.json",
    "attack-ground-truth": "attack_ground_truth.json",
    "ch-scores": "ch_scores.json",
    "ch-scores-balanced": "ch_scores_balanced.json",
    "ch-scores-nonleaky": "ch_scores_nonleaky.json",
    "dashboard-data": "dashboard_data.json",
    "energy-forecast": "energy_forecast.json",
    "energy-forecast-ibrl": "energy_forecast_ibrl.json",
    "failure-probs": "failure_probs.json",
    "final-pipeline-result": "final_pipeline_result.json",
    "routing-simulation": "routing_simulation.json",
    "trust-aware-routing-results": "trust_aware_routing_results.json",
}

@app.get("/")
def root():
    return {"status": "WSN AI backend running", "endpoints": list(FILE_MAP.keys())}

@app.get("/api/{key}")
def get_json(key: str):
    if key not in FILE_MAP:
        raise HTTPException(status_code=404, detail="Unknown endpoint")
    filepath = os.path.join(OUTPUT_DIR, FILE_MAP[key])
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail=f"{filepath} not found")
    with open(filepath, "r") as f:
        return json.load(f)