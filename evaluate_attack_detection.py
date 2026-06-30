"""
evaluate_attack_detection.py

Compares the Isolation Forest anomaly detector's flagged nodes against
real ground-truth attack labels (black-hole, grayhole, flooding, TDMA)
to compute actual detection performance (precision, recall, F1).

Inputs:
  outputs/anomaly_detection_results.json -> node_anomaly_scores (row-index keyed)
  outputs/attack_ground_truth.json       -> {"is_attacked": 0/1, "attack_type": str} (row-index keyed)

Both files use the SAME key convention: string row-index ("0", "1", ...),
NOT the "node_101000" style IDs. Confirmed with Person B.
"""

import json
from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix

ANOMALY_FILE = "outputs/anomaly_detection_results.json"
GROUND_TRUTH_FILE = "outputs/attack_ground_truth.json"
THRESHOLD = 0.34  # matches the model's own contamination rate (~9.23%)


def load_data():
    with open(ANOMALY_FILE) as f:
        anomaly_data = json.load(f)
    raw_scores = anomaly_data["node_anomaly_scores"]

    with open(GROUND_TRUTH_FILE) as f:
        ground_truth = json.load(f)

    return raw_scores, ground_truth


def normalize_scores(raw_scores: dict) -> dict:
    """Min-max invert so anomalous -> 1.0, normal -> 0.0."""
    values = list(raw_scores.values())
    min_score, max_score = min(values), max(values)
    span = max_score - min_score
    return {
        node_id: (max_score - raw) / span
        for node_id, raw in raw_scores.items()
    }


def main():
    raw_scores, ground_truth = load_data()
    normalized = normalize_scores(raw_scores)

    # Align on shared row-index keys, in case of any mismatch in coverage
    shared_keys = sorted(set(normalized.keys()) & set(ground_truth.keys()), key=int)
    missing_from_gt = set(normalized.keys()) - set(ground_truth.keys())
    missing_from_anomaly = set(ground_truth.keys()) - set(normalized.keys())

    print(f"Shared node count: {len(shared_keys)}")
    if missing_from_gt:
        print(f"WARNING: {len(missing_from_gt)} nodes in anomaly file have no ground truth label")
    if missing_from_anomaly:
        print(f"WARNING: {len(missing_from_anomaly)} nodes in ground truth have no anomaly score")

    y_true = []
    y_pred = []
    attack_types = []

    for node_id in shared_keys:
        y_true.append(int(ground_truth[node_id]["is_attacked"]))
        y_pred.append(1 if normalized[node_id] > THRESHOLD else 0)
        attack_types.append(ground_truth[node_id]["attack_type"])

    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()

    print("\n=== Overall Detection Performance (threshold > 0.34) ===")
    print(f"Precision: {precision:.4f}")
    print(f"Recall:    {recall:.4f}")
    print(f"F1 Score:  {f1:.4f}")
    print(f"True Positives:  {tp}")
    print(f"False Positives: {fp}")
    print(f"True Negatives:  {tn}")
    print(f"False Negatives: {fn}")

    # Per-attack-type breakdown: how well are we detecting EACH attack type specifically?
    print("\n=== Detection Rate by Attack Type ===")
    attack_type_set = sorted(set(attack_types) - {"none"})
    for atype in attack_type_set:
        type_indices = [i for i, t in enumerate(attack_types) if t == atype]
        type_true = [y_true[i] for i in type_indices]
        type_pred = [y_pred[i] for i in type_indices]
        detected = sum(1 for t, p in zip(type_true, type_pred) if p == 1)
        total = len(type_indices)
        rate = detected / total if total > 0 else 0
        print(f"  {atype:12s}: {detected}/{total} detected ({rate*100:.1f}%)")

    # Save results
    results = {
        "threshold": THRESHOLD,
        "total_nodes_evaluated": len(shared_keys),
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
        "confusion_matrix": {
            "true_positives": int(tp),
            "false_positives": int(fp),
            "true_negatives": int(tn),
            "false_negatives": int(fn),
        },
        "detection_rate_by_attack_type": {
            atype: {
                "detected": sum(
                    1 for i in range(len(attack_types))
                    if attack_types[i] == atype and y_pred[i] == 1
                ),
                "total": sum(1 for t in attack_types if t == atype),
            }
            for atype in attack_type_set
        },
    }

    with open("outputs/attack_detection_evaluation.json", "w") as f:
        json.dump(results, f, indent=2)

    print("\nResults written to outputs/attack_detection_evaluation.json")


if __name__ == "__main__":
    main()