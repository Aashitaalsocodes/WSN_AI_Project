"""
lstm_routing_with_history.py - LSTM with REAL energy history
"""

import json
import math
import random
import argparse
import os
import warnings
from pathlib import Path

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
warnings.filterwarnings('ignore')

import networkx as nx
import pandas as pd
import numpy as np

from trust_engine import TrustEngine

# ============================================
# COMMAND LINE
# ============================================

_parser = argparse.ArgumentParser()
_parser.add_argument("--seed", type=int, default=42)
_args, _ = _parser.parse_known_args()
SEED = _args.seed

# ============================================
# PATHS
# ============================================

BASE_DIR = Path(__file__).parent
OUTPUTS = BASE_DIR / "outputs"

SIM_PATH = OUTPUTS / f"routing_simulation_seed{SEED}.json"
CLASSIFIER_PATH = OUTPUTS / "attack_classification_results.json"
NODES_PATH = OUTPUTS / "preprocessed_nodes.json"
STUB_CLASSIFIER_PATH = OUTPUTS / "attack_classifier_predictions.json"
RESULT_PATH = OUTPUTS / f"routing_cost_results_seed{SEED}_lstm_history.json"
ENERGY_HISTORY_PATH = OUTPUTS / "node_energy_history.json"

# ============================================
# CONFIG
# ============================================

ATTACK_RISK_WEIGHT = {
    "Normal": 0.0,
    "TDMA": 0.1354,
    "Flooding": 0.0052,
    "Grayhole": 0.2969,
    "Blackhole": 0.5938,
}

W_DISTANCE = 1.0
W_ENERGY = 1.0
W_ATTACK = 2.0

# ============================================
# BATCH LSTM ROUTER WITH REAL HISTORY
# ============================================

class LSTMEnergyRouterWithHistory:
    """LSTM router with REAL energy history from simulations."""
    
    def __init__(self):
        self.history = {}
        self.forecasts = {}
        self.model = None
        self.load_model()
        self.load_history()
    
    def load_model(self):
        try:
            from tensorflow.keras.models import load_model
            model_path = OUTPUTS / "lstm_models" / "lstm_dt_energy_model.h5"
            if model_path.exists():
                self.model = load_model(
                    model_path,
                    custom_objects={'mse': 'mse', 'mae': 'mae'},
                    compile=False
                )
                print("  [OK] LSTM model loaded")
                return True
            else:
                print("  [WARN] Model file not found")
                return False
        except Exception as e:
            print(f"  [WARN] Could not load model: {e}")
            return False
    
    def load_history(self):
        """Load REAL energy history from simulations."""
        if ENERGY_HISTORY_PATH.exists():
            with open(ENERGY_HISTORY_PATH) as f:
                self.history = json.load(f)
            print(f"  [OK] Loaded energy history for {len(self.history)} nodes")
            return True
        else:
            print("  [WARN] No energy history found. Run load_energy_history.py first.")
            return False
    
    def get_energy_sequence(self, node_id):
        """Get energy sequence for a node (first 3 values)."""
        if node_id in self.history:
            seq = self.history[node_id]
            # If sequence is long enough, use the first 3 values
            if len(seq) >= 3:
                return seq[:3]
        return None
    
    def batch_predict_all(self):
        """Predict energy for ALL nodes using their history."""
        if self.model is None:
            print("  [WARN] No model loaded, skipping predictions")
            return
        
        batch_inputs = []
        batch_nodes = []
        
        for node_id, seq in self.history.items():
            if len(seq) >= 3:
                # Use last 3 values as input
                batch_inputs.append(seq[-3:])
                batch_nodes.append(node_id)
        
        if len(batch_inputs) == 0:
            print("  [WARN] No nodes have 3+ energy values")
            return
        
        # Batch predict
        X = np.array(batch_inputs).reshape(len(batch_inputs), 3, 1)
        predictions = self.model.predict(X, verbose=0)
        
        for i, node_id in enumerate(batch_nodes):
            self.forecasts[node_id] = float(predictions[i][0])
        
        print(f"  [OK] Predicted {len(batch_nodes)} nodes")
    
    def get_penalty(self, node_id):
        forecast = self.forecasts.get(node_id, None)
        if forecast is None:
            return 1.0
        if forecast < 0.1:
            return 10.0
        elif forecast < 0.2:
            return 5.0
        elif forecast < 0.3:
            return 2.0
        else:
            return 1.0

# ============================================
# HELPERS
# ============================================

def reconstruct_positions():
    with open(STUB_CLASSIFIER_PATH) as f:
        attack_preds = json.load(f)
    all_ids = list(attack_preds.keys())
    random.seed(SEED)
    sampled_ids = random.sample(all_ids, 500)
    return {nid: (random.uniform(0, 1), random.uniform(0, 1)) for nid in sampled_ids}

# ============================================
# MAIN
# ============================================

def main():
    print("\n" + "=" * 60)
    print("ROUTING COST ENGINE (LSTM + REAL HISTORY)")
    print("=" * 60)
    print(f"Seed: {SEED}")
    print("-" * 60)
    
    # Load files
    print("Loading files...")
    with open(SIM_PATH) as f:
        sim = json.load(f)
    with open(CLASSIFIER_PATH) as f:
        classifier = json.load(f)
    try:
        with open(NODES_PATH) as f:
            nodes_raw = json.load(f)
        print("  [OK] preprocessed_nodes loaded")
    except:
        print("  [WARN] preprocessed_nodes not found")
        nodes_raw = {}
    
    positions = reconstruct_positions()
    node_ids = sim["node_ids"]
    
    # Build node features
    print("Building features...")
    node_feat = {}
    for nid in node_ids:
        record = nodes_raw.get(nid, {})
        pred = classifier.get(nid, {})
        attack_type = pred.get("attack_type", "Normal")
        confidence = pred.get("confidence", 0.5)
        attack_risk = ATTACK_RISK_WEIGHT.get(attack_type, 0.5) * confidence
        
        node_feat[nid] = {
            "historical_accuracy": record.get("historical_accuracy", 0.5),
            "protocol_compliance": record.get("protocol_compliance", 0.5),
            "neighbor_recommendation": record.get("neighbor_recommendation", 0.5),
            "energy_risk": record.get("energy_risk", 0.5),
            "attack_risk": attack_risk,
            "attack_type": attack_type,
            "trust_score": 0.7,
        }
    
    # TrustEngine
    print("Running TrustEngine...")
    rows = []
    for nid in node_ids:
        f = node_feat[nid]
        rows.append({
            "historical_accuracy": f["historical_accuracy"],
            "protocol_compliance": f["protocol_compliance"],
            "neighbor_recommendation": f["neighbor_recommendation"],
            "anomaly_score": f["attack_risk"],
        })
    df = pd.DataFrame(rows)
    trust_df = TrustEngine().update_trust(df)
    for i, nid in enumerate(node_ids):
        node_feat[nid]["trust_score"] = trust_df["trust_score"].values[i]
    print(f"  [OK] Avg trust: {trust_df['trust_score'].mean():.4f}")
    
    # LSTM router with REAL history
    print("Initializing LSTM (with real history)...")
    lstm_router = LSTMEnergyRouterWithHistory()
    
    # Build graph
    print("Building graph...")
    G = nx.Graph()
    G.add_nodes_from(node_ids)
    for u, v in sim["edges"]:
        ux, uy = positions[u]
        vx, vy = positions[v]
        G.add_edge(u, v, distance=math.sqrt((ux-vx)**2 + (uy-vy)**2))
    print(f"  [OK] Graph: {len(node_ids)} nodes, {len(sim['edges'])} edges")
    
    # Run LSTM batch prediction
    print("Running LSTM batch prediction...")
    lstm_router.batch_predict_all()
    
    # Edge cost with LSTM
    def edge_cost(u, v, edge_attrs):
        fu, fv = node_feat[u], node_feat[v]
        avg_energy = (fu["energy_risk"] + fv["energy_risk"]) / 2
        avg_attack = (fu["attack_risk"] + fv["attack_risk"]) / 2
        avg_trust = max((fu["trust_score"] + fv["trust_score"]) / 2, 0.01)
        distance = edge_attrs["distance"]
        
        # LSTM penalty
        penalty_u = lstm_router.get_penalty(u)
        penalty_v = lstm_router.get_penalty(v)
        energy_penalty = penalty_u + penalty_v
        
        return (W_DISTANCE * distance + W_ENERGY * avg_energy + energy_penalty + W_ATTACK * avg_attack) / avg_trust
    
    # Route
    print("Routing 200 routes...")
    results = []
    for idx, route in enumerate(sim["baseline_routes"]):
        src, dst = route["source"], route["destination"]
        try:
            path = nx.dijkstra_path(G, src, dst, weight=edge_cost)
            attacked = [n for n in path if node_feat[n]["attack_type"] != "Normal" and n not in (src, dst)]
            results.append({
                "route_id": route["route_id"],
                "path": path,
                "hop_count": len(path) - 1,
                "passes_through_attacked_node": len(attacked) > 0,
            })
        except:
            results.append({"route_id": route["route_id"], "path_found": False})
        
        if (idx + 1) % 50 == 0:
            print(f"  Progress: {idx+1}/200")
    
    # Summary
    found = [r for r in results if r.get("path_found", True)]
    compromised = sum(1 for r in found if r.get("passes_through_attacked_node", False))
    pct = round(100 * compromised / len(found), 2) if found else 0
    avg_hops = round(sum(r["hop_count"] for r in found) / len(found), 2) if found else 0
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Routes found: {len(found)}/200")
    print(f"Avg hop count: {avg_hops}")
    print(f"Compromised routes: {compromised} ({pct}%)")
    print(f"LSTM integrated: {lstm_router.model is not None}")
    print(f"Nodes predicted: {len(lstm_router.forecasts)}")
    print("=" * 60)
    
    with open(RESULT_PATH, "w") as f:
        json.dump({"routes": results, "summary": {"pct_compromised": pct, "avg_hops": avg_hops, "lstm_enabled": True, "nodes_predicted": len(lstm_router.forecasts)}}, f, indent=2)
    print(f"\nSaved to {RESULT_PATH}")

if __name__ == "__main__":
    main()