# ollama_llm.py
import json
import requests
from config import OLLAMA_API_URL, OLLAMA_MODEL

class LLMInterface:
    """
    Interface to a local Ollama LLM (Qwen2 or Mistral).
    Sends network state + ML predictions as JSON and returns plain-English insights.
    """
    def __init__(self, model=None, api_url=None):
        self.model = model or OLLAMA_MODEL
        self.api_url = api_url or OLLAMA_API_URL
        self._check_ollama_running()

    def _check_ollama_running(self):
        """Simple check if Ollama server is reachable."""
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            if response.status_code != 200:
                print("Warning: Ollama server not responding. Start it with 'ollama serve'")
        except requests.exceptions.ConnectionError:
            print("Warning: Ollama not running. Please start Ollama (ollama serve)")

    def _call_llm(self, prompt: str) -> str:
        """Send prompt to Ollama and return response text."""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.3, "top_p": 0.9}
        }
        try:
            response = requests.post(self.api_url, json=payload, timeout=30)
            response.raise_for_status()
            return response.json().get("response", "")
        except Exception as e:
            return f"[LLM Error] {str(e)}"

    def network_health_report(self, network_state: dict, ml_predictions: dict) -> str:
        """
        Generate plain‑English health analysis.
        network_state: e.g. {"alive_nodes": 87, "dead_nodes": 13, "average_energy": 0.45, ...}
        ml_predictions: e.g. {"failure_risk": {"node_15": 0.92}, ...}
        """
        context = {
            "network_state": network_state,
            "ml_predictions": ml_predictions
        }
        prompt = f"""
You are a network health analyst for a wireless sensor network (WSN). 
Based on the data below, write a short health report (2‑3 sentences). 
Highlight the most critical issue and give one actionable recommendation.

Data:
{json.dumps(context, indent=2)}

Report:
"""
        return self._call_llm(prompt)

    def attack_alert(self, anomalies: list, trust_scores: dict) -> str:
        """
        anomalies: list of dicts with node_id, anomaly_score, is_anomaly
        trust_scores: dict {node_id: trust_score}
        Returns an attack response plan.
        """
        prompt = f"""
You are a security analyst. The following nodes show anomalous behavior and/or low trust scores.
Write a short alert (1‑2 sentences) and recommend two immediate actions.

Anomalies: {json.dumps(anomalies[:5])}
Trust scores (sample): {json.dumps({k: trust_scores.get(k, 0) for k in list(trust_scores.keys())[:10]})}

Alert & Actions:
"""
        return self._call_llm(prompt)

    def adaptive_policy(self, performance_metrics: dict, recent_attacks: list) -> str:
        """
        Suggest policy changes based on performance and attack history.
        """
        prompt = f"""
You are a network policy optimizer. Based on recent performance and attacks, 
suggest changes to routing, trust thresholds, or duty cycling.

Performance: {json.dumps(performance_metrics, indent=2)}
Recent attacks: {recent_attacks}

Policy recommendations (bullet points):
"""
        return self._call_llm(prompt)


# Quick test when run directly (requires Ollama running)
if __name__ == "__main__":
    llm = LLMInterface()

    # Example network state
    net_state = {
        "alive_nodes": 87,
        "dead_nodes": 13,
        "average_energy": 0.45,
        "round": 1200,
        "packet_delivery_ratio": 0.92
    }
    ml_preds = {
        "failure_risk": {"node_15": 0.92, "node_32": 0.78},
        "ch_scores": {"node_5": 0.87, "node_22": 0.34}
    }
    print("=== Health Report ===")
    print(llm.network_health_report(net_state, ml_preds))

    # Example anomalies
    anomalies = [
        {"node_id": 12, "anomaly_score": 0.92, "is_anomaly": 1},
        {"node_id": 27, "anomaly_score": 0.88, "is_anomaly": 1}
    ]
    trust = {12: 0.32, 27: 0.28, 5: 0.91}
    print("\n=== Attack Alert ===")
    print(llm.attack_alert(anomalies, trust))

    # Example policy generation
    metrics = {"network_lifetime_remaining": 800, "energy_efficiency": 62}
    attacks = ["blackhole", "sybil"]
    print("\n=== Policy Recommendations ===")
    print(llm.adaptive_policy(metrics, attacks))