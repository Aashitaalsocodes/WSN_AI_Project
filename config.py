# config.py
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "sample_data")
RESULTS_DIR = os.path.join(BASE_DIR, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

# Trust engine parameters
TRUST_WEIGHTS = {
    "historical_accuracy": 0.4,
    "protocol_compliance": 0.3,
    "neighbor_recommendation": 0.2,
    "anomaly_score": 0.1
}
TRUST_THRESHOLD = 0.4

# Anomaly detection
ISOLATION_FOREST_CONTAMINATION = 0.05
ISOLATION_FOREST_N_ESTIMATORS = 100

# LLM
OLLAMA_MODEL = "qwen2:1.5b"   # or "mistral:7b"
OLLAMA_API_URL = "http://localhost:11434/api/generate"

# Simulation
ROUNDS_PER_DAY = 24
FAILURE_PREDICTION_HORIZON = 24