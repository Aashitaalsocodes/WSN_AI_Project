import json

graph = json.load(open("outputs/gnn_graph_data.json"))["nodes"]
preds = json.load(open("outputs/gnn_node_predictions.json"))

attacked = [nid for nid, rec in graph.items() if rec["label"] == 1][:10]

print("--- Spot check: 10 known-attacked nodes vs model predictions ---\n")
for nid in attacked:
    print(nid, "| true label: 1 | predicted:", preds[nid])

print("\n--- Model report ---\n")
report = json.load(open("outputs/gnn_model_report.json"))
print(json.dumps(report, indent=2))