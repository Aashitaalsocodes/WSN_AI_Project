"""
preprocess_pipeline.py
======================
WSN AI Security Pipeline — Explicit Data Preprocessing Stage (Task 1)

Real columns in WSN-DS with actual variation:
  - timestamp, is_cluster_head, is_faulty
  - packets_sent, packets_received, distance_to_ch

Flat/placeholder columns (all zero or constant — NOT used):
  - energy_remaining (always 50.0)
  - power_mW, cumulative_energy_mJ, interval_energy_mJ (always 0.0)
  - energy_decay_rate, rolling_energy_avg (always 0.0 / 50.0)

Energy data comes from LSTM IBRL forecast (energy_forecast_ibrl.json),
NOT from the WSN-DS CSV columns.

Inputs:
  - data/processed/processed_data.csv
  - outputs/anomaly_detection_results.json
  - outputs/attack_classifier_predictions.json
  - outputs/energy_forecast_ibrl.json

Outputs:
  - outputs/preprocessed_nodes.json
  - outputs/preprocessing_report.json

Output schema per node (feeds Task 2 attack classification + Task 5 GNN):
{
  "node_id":                    str,
  "raw_anomaly_score":          float,
  "normalized_anomaly_score":   float,
  "attack_probability":         float,
  "predicted_attacked":         int,
  "packet_delivery_ratio":      float,
  "distance_to_ch_norm":        float,
  "is_cluster_head":            int,
  "is_faulty":                  int,
  "historical_accuracy":        float,
  "protocol_compliance":        float,
  "neighbor_recommendation":    float,
  "composite_risk_score":       float,
  "energy_risk":                float,
}
"""

import json
import os
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime

BASE_DIR        = Path(__file__).parent
DATA_PATH       = BASE_DIR / "data" / "processed" / "processed_data.csv"
OUTPUTS         = BASE_DIR / "outputs"
ANOMALY_PATH    = OUTPUTS / "anomaly_detection_results.json"
CLASSIFIER_PATH = OUTPUTS / "attack_classifier_predictions.json"
ENERGY_PATH     = OUTPUTS / "energy_forecast_ibrl.json"
OUT_NODES       = OUTPUTS / "preprocessed_nodes.json"
OUT_REPORT      = OUTPUTS / "preprocessing_report.json"

IF_MIN = -0.291202
IF_MAX =  0.149915


def normalize_isolation_forest(raw_score):
    return (IF_MAX - raw_score) / (IF_MAX - IF_MIN)


def derive_historical_accuracy(pdr):
    pdr_clipped = np.clip(pdr, 0.0, 1.0)
    return float(0.05 + 0.90 * pdr_clipped)


def derive_protocol_compliance(pdr, distance_norm):
    pdr_factor      = np.clip(pdr, 0.0, 1.0)
    distance_factor = 1.0 - distance_norm
    compliance      = 0.7 * pdr_factor + 0.3 * distance_factor
    return float(np.clip(compliance, 0.05, 0.95))


def derive_neighbor_recommendation(node_idx, total_rows, attack_probs, window=50):
    start = max(0, node_idx - window // 2)
    end   = min(total_rows - 1, node_idx + window // 2)
    neighbor_probs = []
    for idx in range(start, end + 1):
        if idx != node_idx:
            prob = attack_probs.get(str(idx), {}).get("attack_probability", 0.0)
            neighbor_probs.append(prob)
    if not neighbor_probs:
        return 0.5
    avg_neighbor_risk = float(np.mean(neighbor_probs))
    return float(np.clip(1.0 - avg_neighbor_risk, 0.05, 0.95))


def load_energy_forecast():
    if not ENERGY_PATH.exists():
        print("      WARNING: energy_forecast_ibrl.json not found — energy_risk defaulting to estimated")
        return {}
    with open(ENERGY_PATH) as f:
        energy_data = json.load(f)
    voltage_data = energy_data.get("next_voltage_forecast_volts", {})
    if not voltage_data:
        return {}
    voltages = list(voltage_data.values())
    v_min = min(voltages)
    v_max = max(voltages)
    energy_risk = {}
    for node_id, voltage in voltage_data.items():
        if v_max > v_min:
            norm_v = (voltage - v_min) / (v_max - v_min)
        else:
            norm_v = 0.5
        energy_risk[str(node_id)] = round(1.0 - norm_v, 6)
    return energy_risk


def validate_dataframe(df):
    required_cols = [
        "node_id", "packets_sent", "packets_received",
        "distance_to_ch", "is_cluster_head", "is_faulty"
    ]
    flat_cols = [
        "energy_remaining", "power_mW", "cumulative_energy_mJ",
        "interval_energy_mJ", "energy_decay_rate", "rolling_energy_avg"
    ]
    return {
        "total_rows":               len(df),
        "total_columns":            len(df.columns),
        "columns_found":            df.columns.tolist(),
        "missing_required_columns": [c for c in required_cols if c not in df.columns],
        "flat_columns_excluded":    [c for c in flat_cols if c in df.columns],
        "null_counts":              {k: int(v) for k, v in df.isnull().sum().items()},
        "total_nulls":              int(df.isnull().sum().sum()),
        "attack_type_distribution": df["attack_type"].value_counts().to_dict()
                                    if "attack_type" in df.columns else {},
        "cluster_head_count":       int(df["is_cluster_head"].sum())
                                    if "is_cluster_head" in df.columns else 0,
        "faulty_node_count":        int(df["is_faulty"].sum())
                                    if "is_faulty" in df.columns else 0,
        "packets_sent_stats": {
            "mean": float(df["packets_sent"].mean()),
            "min":  float(df["packets_sent"].min()),
            "max":  float(df["packets_sent"].max()),
        },
        "distance_to_ch_stats": {
            "mean": float(df["distance_to_ch"].mean()),
            "min":  float(df["distance_to_ch"].min()),
            "max":  float(df["distance_to_ch"].max()),
        },
    }


def run_preprocessing(sample_size=None, neighbor_window=50):
    print("=" * 60)
    print("WSN AI Security Pipeline — Data Preprocessing Stage")
    print("=" * 60)

    print(f"\n[1/6] Loading raw data from {DATA_PATH}...")
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"processed_data.csv not found at {DATA_PATH}")
    df         = pd.read_csv(DATA_PATH, nrows=sample_size)
    total_rows = len(df)
    print(f"      Loaded {total_rows:,} rows x {len(df.columns)} columns")

    print("\n[2/6] Validating data quality...")
    quality_report = validate_dataframe(df)
    if quality_report["missing_required_columns"]:
        print(f"      WARNING: Missing columns: {quality_report['missing_required_columns']}")
    else:
        print(f"      All required columns present")
    print(f"      Flat/excluded columns: {quality_report['flat_columns_excluded']}")
    print(f"      Attack distribution: {quality_report['attack_type_distribution']}")
    print(f"      Cluster heads: {quality_report['cluster_head_count']:,} ({quality_report['cluster_head_count']/total_rows*100:.1f}%)")
    print(f"      Faulty nodes:  {quality_report['faulty_node_count']:,} ({quality_report['faulty_node_count']/total_rows*100:.1f}%)")
    if quality_report["total_nulls"] > 0:
        print(f"      WARNING: {quality_report['total_nulls']:,} nulls - filling with medians")
        df = df.fillna(df.median(numeric_only=True))
    else:
        print(f"      No null values")

    print("\n[3/6] Loading ML model outputs...")
    with open(ANOMALY_PATH) as f:
        anomaly_raw = json.load(f)
    anomaly_scores = anomaly_raw.get("node_anomaly_scores", anomaly_raw)
    print(f"      Anomaly scores:     {len(anomaly_scores):,} entries")
    with open(CLASSIFIER_PATH) as f:
        attack_preds = json.load(f)
    print(f"      Attack predictions: {len(attack_preds):,} entries")
    energy_risk_map = load_energy_forecast()
    print(f"      LSTM energy risks:  {len(energy_risk_map)} nodes (IBRL forecast)")

    print("\n[4/6] Computing normalization constants...")
    dist_min  = float(df["distance_to_ch"].min())
    dist_max  = float(df["distance_to_ch"].max())
    print(f"      Distance to CH: min={dist_min:.4f}, max={dist_max:.4f}")
    print(f"      Note: energy_remaining and power_mW are flat in WSN-DS - using IBRL LSTM for energy")
    quality_report["normalization_constants"] = {
        "distance_to_ch":   {"min": dist_min, "max": dist_max},
        "isolation_forest": {"min": IF_MIN,   "max": IF_MAX},
        "energy_source":    "IBRL LSTM forecast (WSN-DS energy columns are flat/unusable)"
    }

    print(f"\n[5/6] Building preprocessed node records...")
    print(f"      Processing {total_rows:,} nodes (neighbor window={neighbor_window})...")

    preprocessed = {}
    skipped      = 0
    zero_pdr     = 0

    for idx, row in df.iterrows():
        node_key = str(idx)

        raw_anomaly = anomaly_scores.get(node_key, IF_MAX)
        if isinstance(raw_anomaly, dict):
            raw_anomaly = raw_anomaly.get("anomaly_score", IF_MAX)
        raw_anomaly  = float(raw_anomaly)
        norm_anomaly = normalize_isolation_forest(raw_anomaly)
        clf           = attack_preds.get(node_key, {})
        attack_prob   = float(clf.get("attack_probability", 0.0))
        pred_attacked = int(clf.get("predicted_attacked", 0))
        packets_sent  = float(row.get("packets_sent", 0))
        
        packets_recv = float(row.get("packets_received", 0))
        is_ch        = int(row.get("is_cluster_head", 0))

        # PDR is type-aware: CHs receive (not send), members send (not receive)
        # Cluster heads: packets_sent is always 0 — use packets_received normalized
        # Member nodes:  packets_received is mostly 0 — use packets_sent normalized
        CH_MAX_RECV     = 1372.0   # max observed packets_received for cluster heads
        MEMBER_MAX_SENT = 241.0    # max observed packets_sent for member nodes

        if is_ch == 1:
            pdr = float(np.clip(packets_recv / CH_MAX_RECV, 0.0, 1.0))
            if packets_recv == 0:
                skipped += 1
        else:
            if packets_sent <= 0:
                pdr = 0.0
                skipped += 1
            else:
                pdr = float(np.clip(packets_sent / MEMBER_MAX_SENT, 0.0, 1.0))
                if pdr == 0.0:
                    zero_pdr += 1
        distance = float(row.get("distance_to_ch", 0.0))
        dist_norm = (distance - dist_min) / (dist_max - dist_min) if dist_max > dist_min else 0.5

        energy_risk = energy_risk_map.get(node_key, -1.0)
        if energy_risk < 0:
            energy_risk = float(0.4 * attack_prob + 0.3 * norm_anomaly + 0.3 * dist_norm)
        energy_risk = float(np.clip(energy_risk, 0.0, 1.0))

        historical_accuracy     = derive_historical_accuracy(pdr)
        protocol_compliance     = derive_protocol_compliance(pdr, dist_norm)
        neighbor_recommendation = derive_neighbor_recommendation(idx, total_rows, attack_preds, neighbor_window)

        composite_risk = (
            0.50 * attack_prob +
            0.25 * norm_anomaly +
            0.15 * energy_risk +
            0.10 * dist_norm
        )

        preprocessed[node_key] = {
            "row_index":                 node_key,
            "node_id":                   str(row.get("node_id", "")),
            "raw_anomaly_score":         round(raw_anomaly, 6),
            "normalized_anomaly_score":  round(norm_anomaly, 6),
            "attack_probability":        round(attack_prob, 6),
            "predicted_attacked":        int(clf.get("predicted_attacked", 0)),
            "packet_delivery_ratio":     round(pdr, 6),
            "distance_to_ch_norm":       round(float(dist_norm), 6),
            "is_cluster_head":           int(row.get("is_cluster_head", 0)),
            "is_faulty_RAW_DO_NOT_USE_AS_FEATURE": int(row.get("is_faulty", 0)), 
            "historical_accuracy":       round(historical_accuracy, 6),
            "protocol_compliance":       round(protocol_compliance, 6),
            "neighbor_recommendation":   round(neighbor_recommendation, 6),
            "energy_risk":               round(energy_risk, 6),
            "composite_risk_score":      round(float(composite_risk), 6),
        }

        if idx % 50000 == 0 and idx > 0:
            print(f"      ... {idx:,} / {total_rows:,} processed")

    print(f"      Done. {len(preprocessed):,} nodes preprocessed")
    print(f"      Skipped (zero packets_sent): {skipped}")
    print(f"      Zero PDR (all packets lost): {zero_pdr}")

    print(f"\n[6/6] Writing outputs...")
    OUTPUTS.mkdir(exist_ok=True)
    with open(OUT_NODES, "w") as f:
        json.dump(preprocessed, f)
    size_mb = OUT_NODES.stat().st_size / (1024 * 1024)
    print(f"      preprocessed_nodes.json: {size_mb:.1f} MB")

    all_pdrs       = [v["packet_delivery_ratio"]      for v in preprocessed.values()]
    all_risks      = [v["composite_risk_score"]        for v in preprocessed.values()]
    all_hist_acc   = [v["historical_accuracy"]         for v in preprocessed.values()]
    all_compliance = [v["protocol_compliance"]         for v in preprocessed.values()]
    all_neighbor   = [v["neighbor_recommendation"]     for v in preprocessed.values()]

    quality_report.update({
        "preprocessing_timestamp":  datetime.now().isoformat(),
        "nodes_preprocessed":       len(preprocessed),
        "nodes_skipped":            skipped,
        "nodes_zero_pdr":           zero_pdr,
        "sample_size_used":         sample_size or total_rows,
        "neighbor_window":          neighbor_window,
        "trust_factor_sources": {
            "historical_accuracy":
                "Derived from PDR (packets_received / packets_sent). Replaces hardcoded 0.8.",
            "protocol_compliance":
                "Derived from PDR + distance_to_ch. Replaces hardcoded 0.8. "
                "Note: power_mW is flat in WSN-DS so energy-based compliance not computable.",
            "neighbor_recommendation":
                f"Derived from mean attack_probability of {neighbor_window} adjacent row-index nodes. "
                "Replaces hardcoded 0.5.",
            "energy_risk":
                "IBRL LSTM voltage forecast for 57 known nodes. "
                "Estimated from composite risk for all others."
        },
        "output_stats": {
            "avg_pdr":                     round(float(np.mean(all_pdrs)), 4),
            "avg_composite_risk":          round(float(np.mean(all_risks)), 4),
            "avg_historical_accuracy":     round(float(np.mean(all_hist_acc)), 4),
            "avg_protocol_compliance":     round(float(np.mean(all_compliance)), 4),
            "avg_neighbor_recommendation": round(float(np.mean(all_neighbor)), 4),
            "pct_high_risk":               round(
                sum(1 for r in all_risks if r > 0.5) / len(all_risks) * 100, 2
            ),
        },
        "sample_records": {k: preprocessed[k] for k in list(preprocessed.keys())[:5]},
    })

    with open(OUT_REPORT, "w") as f:
        json.dump(quality_report, f, indent=2)
    print(f"      preprocessing_report.json written")

    print("\n" + "=" * 60)
    print("PREPROCESSING COMPLETE")
    print("=" * 60)
    print(f"  Nodes processed:           {len(preprocessed):,}")
    print(f"  Nodes skipped:             {skipped}")
    print(f"  Avg PDR:                   {quality_report['output_stats']['avg_pdr']:.4f}")
    print(f"  Avg composite risk:        {quality_report['output_stats']['avg_composite_risk']:.4f}")
    print(f"  Avg historical accuracy:   {quality_report['output_stats']['avg_historical_accuracy']:.4f}")
    print(f"  Avg protocol compliance:   {quality_report['output_stats']['avg_protocol_compliance']:.4f}")
    print(f"  Avg neighbor recommend:    {quality_report['output_stats']['avg_neighbor_recommendation']:.4f}")
    print(f"  % high risk nodes (>0.5):  {quality_report['output_stats']['pct_high_risk']}%")
    print(f"  Trust factors derived:     3/4 (replaces placeholders in TrustEngine)")
    print(f"  Output: outputs/preprocessed_nodes.json")
    print(f"  Report: outputs/preprocessing_report.json")
    print("=" * 60)

    return {
        "nodes_preprocessed":  len(preprocessed),
        "nodes_skipped":       skipped,
        "total_nulls_handled": quality_report["total_nulls"],
        "output_stats":        quality_report["output_stats"],
        "output_path":         str(OUT_NODES),
        "report_path":         str(OUT_REPORT),
    }


if __name__ == "__main__":
    import sys
    sample = None
    if "--sample" in sys.argv:
        idx    = sys.argv.index("--sample")
        sample = int(sys.argv[idx + 1])
        print(f"Running in SAMPLE mode: {sample:,} rows only")
    result = run_preprocessing(sample_size=sample, neighbor_window=50)
    print(f"\nSummary: {result}")