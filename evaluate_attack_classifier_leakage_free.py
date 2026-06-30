"""
evaluate_attack_classifier.py (leakage-free version)

Independently verifies the supervised attack classifier's performance using
ONLY the held-out test-set rows (outputs/attack_classifier_test_indices.json),
not the full dataset predictions file. This avoids data leakage: the full
predictions file includes rows the model was trained on, which would give an
artificially inflated score if used for evaluation.

Inputs:
  outputs/attack_classifier_predictions.json   -> {"predicted_attacked": 0/1, "attack_probability": float}
  outputs/attack_ground_truth.json             -> {"is_attacked": 0/1, "attack_type": str}
  outputs/attack_classifier_test_indices.json  -> list of row indices (ints) that were held out as the test set
"""

import json
from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix

PREDICTIONS_FILE = "outputs/attack_classifier_predictions.json"
GROUND_TRUTH_FILE = "outputs/attack_ground_truth.json"
TEST_INDICES_FILE = "outputs/attack_classifier_test_indices.json"


def main():
    with open(PREDICTIONS_FILE) as f:
        predictions = json.load(f)
    with open(GROUND_TRUTH_FILE) as f:
        ground_truth = json.load(f)
    with open(TEST_INDICES_FILE) as f:
        test_indices = json.load(f)

    # Restrict evaluation to ONLY the held-out test rows
    test_keys = sorted({str(i) for i in test_indices}, key=int)
    shared_keys = [k for k in test_keys if k in predictions and k in ground_truth]

    print(f"Test set size (from training script): {len(test_indices)}")
    print(f"Evaluated on: {len(shared_keys)} rows (held-out, not seen during training)")

    if len(shared_keys) != len(test_indices):
        print("WARNING: some test indices were missing from predictions/ground truth files")

    y_true = []
    y_pred = []
    attack_types = []

    for node_id in shared_keys:
        y_true.append(int(ground_truth[node_id]["is_attacked"]))
        y_pred.append(int(predictions[node_id]["predicted_attacked"]))
        attack_types.append(ground_truth[node_id]["attack_type"])

    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()

    print("\n=== Leakage-Free Detection Performance (test-set only) ===")
    print(f"Precision: {precision:.4f}")
    print(f"Recall:    {recall:.4f}")
    print(f"F1 Score:  {f1:.4f}")
    print(f"True Positives:  {tp}")
    print(f"False Positives: {fp}")
    print(f"True Negatives:  {tn}")
    print(f"False Negatives: {fn}")

    print("\n=== Detection Rate by Attack Type (test-set only) ===")
    attack_type_set = sorted(set(attack_types) - {"none"})
    for atype in attack_type_set:
        type_indices = [i for i, t in enumerate(attack_types) if t == atype]
        type_pred = [y_pred[i] for i in type_indices]
        detected = sum(type_pred)
        total = len(type_indices)
        rate = detected / total if total > 0 else 0
        print(f"  {atype:12s}: {detected}/{total} detected ({rate*100:.1f}%)")

    results = {
        "model": "supervised_attack_classifier",
        "evaluation_method": "held_out_test_set_only",
        "test_set_size": len(shared_keys),
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
                    y_pred[i] for i in range(len(attack_types)) if attack_types[i] == atype
                ),
                "total": sum(1 for t in attack_types if t == atype),
            }
            for atype in attack_type_set
        },
    }

    with open("outputs/attack_classifier_evaluation_leakage_free.json", "w") as f:
        json.dump(results, f, indent=2)

    print("\nResults written to outputs/attack_classifier_evaluation_leakage_free.json")
    print(f"\nCompare to Person B's reported F1 (from their own train/test split): 0.94")
    print(f"This independent test-set-only F1: {f1:.4f}")


if __name__ == "__main__":
    main()