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
            response = requests.post(self.api_url, json=payload, timeout=90)
            response.raise_for_status()
            return response.json().get("response", "")
        except Exception as e:
            return f"[LLM Error] {str(e)}"

    def _add_range_caveat_if_needed(self, text: str) -> str:
        """Append a caveat if the LLM suggested an unrealistic extreme threshold value."""
        import re
        matches = re.findall(r'threshold[^0-9]{0,15}(\d*\.?\d+)', text, re.IGNORECASE)
        for m in matches:
            try:
                val = float(m)
                if val <= 0.05 or val >= 0.95:
                    return text + "\n\n[Note: This response suggested an extreme threshold value near 0 or 1, which may not be operationally realistic. Please review before applying.]"
            except ValueError:
                continue
        return text

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

Important context: trust_score and trust_threshold values are bounded between 0 and 1, where 0 = no trust and 1 = maximum strictness (a threshold of 1.0 would flag nearly all nodes as suspicious, which is not a sensible recommendation). Realistic trust_threshold values for this system typically range from 0.3 to 0.7. anomaly_score values are also normalized between 0 (normal) and 1 (highly anomalous). When suggesting threshold or score-related changes, only recommend values within these realistic ranges and briefly justify why.

Data:
{json.dumps(context, indent=2)}

Report:
"""
        return self._add_range_caveat_if_needed(self._call_llm(prompt))

    def attack_alert(self, anomalies: list, trust_scores: dict) -> str:
        """
        anomalies: list of dicts with node_id, anomaly_score, is_anomaly
        trust_scores: dict {node_id: trust_score}
        Returns an attack response plan.
        """
        prompt = f"""
You are a security analyst. The following nodes show anomalous behavior and/or low trust scores.
Write a short alert (1‑2 sentences) and recommend two immediate actions.

Important context: trust_scores in this system range from 0 (untrustworthy) to 1 (fully trusted), with a current operating threshold of approximately 0.4. anomaly_score values range from 0 (normal) to 1 (highly anomalous). Frame your alert and recommendations using these realistic bounds — do not suggest absolute extremes like 0 or 1 as practical thresholds.

Anomalies: {json.dumps(anomalies[:5])}
Trust scores (sample): {json.dumps({k: trust_scores.get(k, 0) for k in list(trust_scores.keys())[:10]})}

Alert & Actions:
"""
        return self._add_range_caveat_if_needed(self._call_llm(prompt))

    def adaptive_policy(self, performance_metrics: dict, recent_attacks: list) -> str:
        """
        Suggest policy changes based on performance and attack history.
        """
        prompt = f"""
You are a network policy optimizer. Based on recent performance and attacks, 
suggest changes to routing, trust thresholds, or duty cycling.

Important context: All trust and anomaly-related scores in this system are normalized between 0 and 1. Realistic, actionable threshold values typically fall between 0.3 and 0.7 — avoid recommending extreme values like 0 or 1.0 as if they were practical settings, since these represent "no trust required" and "maximum strictness" respectively, neither of which is operationally useful. Keep recommendations grounded in this realistic range.

Performance: {json.dumps(performance_metrics, indent=2)}
Recent attacks: {recent_attacks}

Policy recommendations (bullet points):
"""
        return self._add_range_caveat_if_needed(self._call_llm(prompt))


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