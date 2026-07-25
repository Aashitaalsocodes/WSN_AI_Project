# WSN AI Security Dashboard

An AI-powered dashboard for monitoring and securing Wireless Sensor Networks (WSNs) — combining attack detection, routing simulation, energy forecasting, and a graph-based digital twin in one interactive interface.

🔗 **Live dashboard (frontend):** [wsn-dashboard.vercel.app](https://wsn-dashboard.vercel.app/)
🔗 **API (backend):** [wsn-ai-project.onrender.com](https://wsn-ai-project.onrender.com)

---

## 📖 Overview

Wireless Sensor Networks face two intertwined challenges: vulnerability to attacks (sinkhole, blackhole, DoS, etc.) and tight per-node energy constraints. This project builds an end-to-end AI pipeline plus a dashboard to visualize it:

- **Attack Detection & Classification** — Isolation Forest for anomaly detection, plus a supervised multiclass attack classifier.
- **Graph Neural Network (GNN) Analysis** — GraphSAGE/GAT models predict per-node malicious/benign trust scores over the network topology graph.
- **Routing Simulation** — Trust-aware routing simulation and cost analysis across the sensor network.
- **Energy Forecasting** — LSTM-based forecasting of node energy consumption/depletion.
- **Digital Twin** — A simulated network state used to validate detection and mitigation logic.
- **LLM-Generated Insights** — A local Ollama LLM (Qwen2/Mistral) turns ML outputs into plain-English network insights.
- **Explainability** — SHAP explanations for anomaly predictions.
- **Feedback Loop & Mitigation Engine** — Closes the loop between detection, trust scoring, and mitigation actions.

## 🛠️ Tech Stack

**Frontend** (`frontend/dashboard/`) — deployed on **Vercel**
- React 19 + Vite 8
- Tailwind CSS v4
- D3 / d3-force (network graph visualizations)
- Recharts (charts), Framer Motion (animations), React Router, React CountUp

**Backend** (`api_server.py`) — deployed on **Render**
- FastAPI + Uvicorn
- Serves precomputed JSON results from `outputs/` over REST, CORS-scoped to the Vercel frontend

**ML / Data Pipeline** (offline scripts, run locally, write JSON to `outputs/`)
- PyTorch + PyTorch Geometric (GraphSAGE, GAT — GNN node classification)
- scikit-learn (Isolation Forest, Random Forest, XGBoost)
- pandas / numpy
- SHAP (explainability)
- Ollama (local LLM for plain-English insights)

## 📂 Project Structure

```
WSN_AI_Project/
├── api_server.py                  # FastAPI backend — exposes outputs/ as REST endpoints
├── config.py                      # Shared config (thresholds, Ollama URL/model, etc.)
├── run_full_pipeline.py           # Orchestrates TrustEngine + LLMInterface → final_pipeline_result.json
│
├── gnn_model.py                   # GNN (GraphSAGE/GAT) training — node malicious/benign prediction
├── gnn_graph_builder.py           # Builds the network graph for the GNN
├── integrate_gnn_pipeline.py
│
├── isolation_forest.py            # Unsupervised anomaly detection
├── isolation_forest_v2.py
├── attack_classifier.py           # Supervised attack classifier
├── attack_classifier_multiclass.py
├── attack_label_generator.py
│
├── trust_engine.py                # Computes per-node trust scores
├── trust_aware_routing.py         # Trust-aware routing logic
├── routing_cost.py / wsn_routing_sim.py
│
├── digital_twin_sim.py            # Digital twin simulation
├── feedback_loop.py               # Feedback loop between detection & mitigation
├── mitigation_engine.py
├── recalibration.py
├── ollama_llm.py                  # Local LLM interface (Ollama) for plain-English insights
│
├── explain_anomalies.py           # Explainability (base)
├── explain_anomalies_shap.py      # SHAP-based explainability
├── peek_shap_samples.py
│
├── preprocess_pipeline.py         # Data preprocessing
├── evaluate_attack_detection.py
├── evaluate_attack_classifier_leakage_free.py
├── build_evaluation_metrics.py
│
├── src/                           # Additional model scripts
│   ├── lstm_energy.py / lstm_ibrl.py / lstm_all_nodes.py / lstm_small.py
│   ├── random_forest_failure.py
│   ├── xgboost_ch.py / xgboost_nonleaky.py
│   ├── data_pipeline.py
│   └── generate_synthetic_data.py
│
├── models/                        # Saved trained models (.pkl)
│   ├── attack_classifier.pkl
│   ├── isolation_forest.pkl
│   └── iso_scaler.pkl
│
├── data/
│   ├── raw/                       # WSN-DS.csv and other raw datasets
│   └── processed/                 # processed_data.csv
│
├── outputs/                       # All pipeline results as JSON (served by api_server.py)
│   ├── dashboard_data.json
│   ├── gnn_node_predictions.json
│   ├── energy_forecast.json
│   ├── routing_simulation.json
│   ├── anomaly_explanations_shap.json
│   ├── final_pipeline_result.json
│   └── ... (evaluation, mitigation, recalibration reports, etc.)
│
├── requirements.txt                # fastapi, uvicorn
│
└── frontend/dashboard/              # React + Vite dashboard (deployed to Vercel)
    ├── package.json
    ├── vite.config.js
    ├── public/
    │   └── dashboard_data.json
    └── src/
        ├── App.jsx / main.jsx
        ├── components/            # Sidebar, KPICard, Ticker, shared
        ├── context/ThemeContext.jsx
        ├── data/pipelineData.js
        └── pages/
            ├── NetworkOverview.jsx
            ├── AttackDetection.jsx
            ├── RoutingSimulation.jsx
            ├── EnergyForecast.jsx
            ├── DigitalTwin.jsx
            ├── GNNVisualization.jsx
            ├── FeedbackLoop.jsx
            ├── EvaluationPerformance.jsx
            ├── PipelineReport.jsx
            └── ArchitectureDiagram.jsx
```

## 🚀 Getting Started

### Prerequisites

- Python 3.x
- Node.js + npm
- [Ollama](https://ollama.com/) installed locally (for LLM-generated insights) with the configured model (Qwen2 or Mistral) pulled

### Backend Setup

```bash
# From the project root
pip install -r requirements.txt

# Start Ollama (needed for run_full_pipeline.py / LLM insights)
ollama serve

# Run the ML pipeline (optional — regenerates outputs/*.json)
python run_full_pipeline.py

# Start the API server
uvicorn api_server:app --reload
```

The API will be available at `http://localhost:8000`, exposing endpoints like `/dashboard-data`, `/gnn-node-predictions`, `/energy-forecast`, `/routing-simulation`, etc. (see `FILE_MAP` in `api_server.py` for the full list).

### Frontend Setup

```bash
cd frontend/dashboard
npm install
npm run dev
```

The dashboard runs at `http://localhost:5173` by default and talks to the FastAPI backend (update the API base URL for local dev if needed — CORS is currently scoped to the deployed Vercel domain and `localhost:5173`).

## 🧠 Explainability (SHAP)

`explain_anomalies_shap.py` generates SHAP-based explanations for anomaly predictions, making individual flagged nodes' scores interpretable. Output is written to `outputs/anomaly_explanations_shap.json` and surfaced in the dashboard.

## 🗺️ Roadmap

Finalize and merge `FeedbackLoop.jsx`
Fully integrate SHAP explainability into the live dashboard
Expand evaluation coverage for the GNN and attack classifiers

## 🤝 Contributing

Contributions, issues, and feature requests are welcome. Feel free to check the [issues page](https://github.com/Aashitaalsocodes/WSN_AI_Project/issues).


## 👩‍💻 Author

**Aashita** — B.Tech, Artificial Intelligence and Data Science, Global Academy of Technology, Bengaluru
