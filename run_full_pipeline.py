"""
WSN Security Pipeline — loads ML artifacts, runs TrustEngine + LLMInterface,
writes outputs/final_pipeline_result.json.
"""

import json
from pathlib import Path

import pandas as pd

from config import TRUST_THRESHOLD
from ollama_llm import LLMInterface
from trust_engine import TrustEngine

OUTPUTS_DIR = Path(__file__).resolve().parent / "outputs"
ANOMALY_ALERT_THRESHOLD = 0.34
TOP_N_FOR_LLM = 20


def load_jsons():
    """Load Person B ML artifact JSON files directly."""
    with open(OUTPUTS_DIR / "anomaly_detection_results.json", encoding="utf-8") as f:
        anomaly_data = json.load(f)
    with open(OUTPUTS_DIR / "ch_scores.json", encoding="utf-8") as f:
        ch_scores = json.load(f)
    with open(OUTPUTS_DIR / "energy_forecast.json", encoding="utf-8") as f:
        energy_forecast = json.load(f)
    return anomaly_data, ch_scores, energy_forecast


def normalize_anomaly_scores(raw_scores: dict) -> tuple[dict[int, float], float, float]:
    """Convert raw Isolation Forest scores to [0,1] where 1 = highly anomalous."""
    if not raw_scores:
        return {}, 0.0, 0.0

    values = list(raw_scores.values())
    min_score = min(values)
    max_score = max(values)
    span = max_score - min_score

    normalized = {}
    for node_id_str, raw in raw_scores.items():
        node_id = int(node_id_str)
        if span == 0:
            normalized[node_id] = 0.0
        else:
            normalized[node_id] = (max_score - raw) / span
    return normalized, min_score, max_score


def build_trust_dataframe(node_anomaly_scores: dict) -> pd.DataFrame:
    """Build per-node DataFrame for TrustEngine from anomaly scores only."""
    normalized, _, _ = normalize_anomaly_scores(node_anomaly_scores)
    node_ids = sorted(normalized.keys())

    df = pd.DataFrame({
        "node_id": node_ids,
        "historical_accuracy": 0.8,
        "protocol_compliance": 0.8,
        "neighbor_recommendation": 0.5,
        "anomaly_score": [normalized[nid] for nid in node_ids],
    })
    return df


def count_above_threshold(scores: pd.Series, thresholds: dict[str, float]) -> dict[str, int]:
    return {label: int((scores > value).sum()) for label, value in thresholds.items()}


def build_top_anomalies(df: pd.DataFrame, threshold: float, top_n: int) -> list[dict]:
    flagged = df[df["anomaly_score"] > threshold].copy()
    flagged = flagged.sort_values("anomaly_score", ascending=False).head(top_n)
    return [
        {
            "node_id": int(row.node_id),
            "anomaly_score": round(float(row.anomaly_score), 4),
            "is_anomaly": 1,
        }
        for row in flagged.itertuples(index=False)
    ]


def energy_forecast_summary(energy_forecast: dict) -> dict:
    values = list(energy_forecast["24h_energy_forecast_mJ"].values())
    return {
        "avg_24h_energy_forecast_mJ": sum(values) / len(values),
        "min_24h_energy_forecast_mJ": min(values),
        "max_24h_energy_forecast_mJ": max(values),
        "energy_forecast_val_mse": energy_forecast["val_mse"],
    }


def derive_recent_attacks(flagged_pct: float) -> list[str]:
    if flagged_pct >= 5.0:
        return ["anomalous_node_cluster"]
    return []


def is_llm_error(text: str) -> bool:
    return text.startswith("[LLM Error]")


def main():
    anomaly_data, ch_scores, energy_forecast = load_jsons()
    node_anomaly_scores = anomaly_data["node_anomaly_scores"]

    df = build_trust_dataframe(node_anomaly_scores)
    df = TrustEngine().update_trust(df)

    flagged_by_threshold = count_above_threshold(
        df["anomaly_score"],
        {"0.34": 0.34, "0.41": 0.41, "0.70": 0.70},
    )

    primary_count = flagged_by_threshold["0.34"]
    total_nodes = len(df)
    flagged_pct = 100.0 * primary_count / total_nodes

    energy_stats = energy_forecast_summary(energy_forecast)

    network_state = {
        "total_nodes": total_nodes,
        "flagged_anomalous_nodes": primary_count,
        "flagged_pct": round(flagged_pct, 2),
        "avg_trust_score": round(float(df["trust_score"].mean()), 4),
        "low_trust_node_count": int(df["suspicious_flag"].sum()),
        "trust_threshold": TRUST_THRESHOLD,
        **{k: round(v, 6) if isinstance(v, float) else v for k, v in energy_stats.items()},
    }

    ml_predictions = {
        "top_cluster_head_candidates": ch_scores["top_candidates"],
        "ch_model_accuracy": ch_scores["accuracy"],
        "ch_model_f1": ch_scores["f1_score"],
        "ch_model_roc_auc": ch_scores["roc_auc"],
    }

    top_anomalies = build_top_anomalies(df, ANOMALY_ALERT_THRESHOLD, TOP_N_FOR_LLM)
    trust_scores = {
        int(row.node_id): round(float(row.trust_score), 4)
        for row in df.itertuples(index=False)
    }

    llm = LLMInterface()
    health_report = llm.network_health_report(network_state, ml_predictions)
    attack_alert_text = llm.attack_alert(top_anomalies, trust_scores)

    performance_metrics = {
        "avg_trust_score": network_state["avg_trust_score"],
        "flagged_pct": network_state["flagged_pct"],
        "low_trust_node_count": network_state["low_trust_node_count"],
        "avg_24h_energy_forecast_mJ": network_state["avg_24h_energy_forecast_mJ"],
        "energy_forecast_val_mse": network_state["energy_forecast_val_mse"],
    }
    recent_attacks = derive_recent_attacks(flagged_pct)
    adaptive_policy_text = llm.adaptive_policy(performance_metrics, recent_attacks)

    result = {
        "network_state": network_state,
        "ml_predictions": ml_predictions,
        "health_report": health_report,
        "attack_alert": attack_alert_text,
        "adaptive_policy": adaptive_policy_text,
        "flagged_node_count_by_threshold": flagged_by_threshold,
    }

    output_path = OUTPUTS_DIR / "final_pipeline_result.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print("=== WSN Security Pipeline Summary ===")
    print(f"Total nodes:              {total_nodes:,}")
    print(f"Flagged (>0.34):          {flagged_by_threshold['0.34']:,} ({flagged_pct:.2f}%)")
    print(f"Flagged (>0.41):          {flagged_by_threshold['0.41']:,}")
    print(f"Flagged (>0.70):          {flagged_by_threshold['0.70']:,}")
    print(f"Avg trust score:          {network_state['avg_trust_score']:.4f}")
    print(f"Low-trust nodes (flag):   {network_state['low_trust_node_count']:,}")
    print(f"Top anomalies sent to LLM: {len(top_anomalies)}")
    print(f"Output written to:        {output_path}")
    print()
    print("LLM call status:")
    for label, text in [
        ("health_report", health_report),
        ("attack_alert", attack_alert_text),
        ("adaptive_policy", adaptive_policy_text),
    ]:
        status = "ERROR" if is_llm_error(text) else "OK"
        preview = text[:80].replace("\n", " ")
        print(f"  {label}: {status} — {preview}...")


if __name__ == "__main__":
    main()
