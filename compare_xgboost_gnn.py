"""
Compare XGBoost (per-record) vs GraphSAGE (per-node) malicious/attack predictions
on the held-out test set, to assess whether GraphSAGE catches cases XGBoost misses.

Run from project root: python compare_xgboost_gnn.py
"""
import json
import pandas as pd

# --- Load data ---
df = pd.read_csv('data/processed/processed_data.csv')  # index = row number, has node_id
test_indices = json.load(open('outputs/attack_classifier_test_indices.json'))
xgb_preds = json.load(open('outputs/attack_classifier_predictions.json'))
ground_truth = json.load(open('outputs/attack_ground_truth.json'))
gnn_preds = json.load(open('outputs/gnn_node_predictions.json'))

print(f"Total rows in processed_data.csv: {len(df)}")
print(f"Test set size: {len(test_indices)}")
print(f"GraphSAGE nodes: {len(gnn_preds)}")

# --- Build comparison rows ---
rows = []
missing_node = 0
for idx in test_indices:
    idx_str = str(idx)
    if idx_str not in xgb_preds or idx_str not in ground_truth:
        continue

    node_id_raw = df.iloc[idx]['node_id']
    node_key = node_id_raw  # CSV node_id already matches gnn_node_predictions.json key format

    if node_key not in gnn_preds:
        missing_node += 1
        continue

    true_label = ground_truth[idx_str]['is_attacked']
    xgb_pred = xgb_preds[idx_str]['predicted_attacked']
    gnn_pred = gnn_preds[node_key]['gnn_predicted_malicious']

    rows.append({
        'row_idx': idx,
        'node_id': node_id_raw,
        'true_label': true_label,
        'xgb_pred': xgb_pred,
        'gnn_pred': gnn_pred,
        'xgb_correct': xgb_pred == true_label,
        'gnn_correct': gnn_pred == true_label,
    })

result = pd.DataFrame(rows)
print(f"\nMatched rows (test set, has GraphSAGE node coverage): {len(result)}")
print(f"Test rows skipped (node_id not in GraphSAGE output): {missing_node}")

# --- Core comparison ---
both_correct = ((result.xgb_correct) & (result.gnn_correct)).sum()
both_wrong = ((~result.xgb_correct) & (~result.gnn_correct)).sum()
xgb_right_gnn_wrong = ((result.xgb_correct) & (~result.gnn_correct)).sum()
gnn_right_xgb_wrong = ((~result.xgb_correct) & (result.gnn_correct)).sum()

n = len(result)
print("\n=== Agreement / Complementarity Table ===")
print(f"Both correct:              {both_correct:6d}  ({100*both_correct/n:.2f}%)")
print(f"Both wrong:                {both_wrong:6d}  ({100*both_wrong/n:.2f}%)")
print(f"XGBoost right, GNN wrong:  {xgb_right_gnn_wrong:6d}  ({100*xgb_right_gnn_wrong/n:.2f}%)")
print(f"GNN right, XGBoost wrong:  {gnn_right_xgb_wrong:6d}  ({100*gnn_right_xgb_wrong/n:.2f}%)  <-- decisive number")

print(f"\nOverall XGBoost accuracy on matched set: {100*result.xgb_correct.mean():.2f}%")
print(f"Overall GraphSAGE accuracy on matched set: {100*result.gnn_correct.mean():.2f}%")

# --- Breakdown of the decisive cases: what do they look like? ---
decisive = result[(~result.xgb_correct) & (result.gnn_correct)]
if len(decisive) > 0:
    print(f"\n=== Sample of {min(10, len(decisive))} cases where GraphSAGE corrected XGBoost ===")
    print(decisive.head(10).to_string(index=False))
    print(f"\nTrue label distribution in these decisive cases:")
    print(decisive.true_label.value_counts())
else:
    print("\nNo cases found where GraphSAGE was right and XGBoost was wrong.")

result.to_csv('outputs/xgboost_gnn_comparison.csv', index=False)
print("\nSaved full comparison to outputs/xgboost_gnn_comparison.csv")