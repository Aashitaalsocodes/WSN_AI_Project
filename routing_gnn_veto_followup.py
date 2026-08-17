"""
Routing follow-up: does letting GraphSAGE veto XGBoost-only exclusions
(i.e. un-exclude a node XGBoost flagged as attacked, if GraphSAGE independently
says that node is normal) reduce unnecessary exclusions/hop overhead without
letting real attackers back into trust-aware routing?

Reuses trust_aware_routing.py's real build_graph/route_with_trust so routing
logic is identical to the paper's existing Section VI test -- only the
exclusion-decision step is modified.

Run from project root: python routing_gnn_veto_followup.py
"""
import json
import pandas as pd
import networkx as nx

from trust_aware_routing import (
    build_graph,
    get_excluded_nodes,
    route_with_trust,
    load_inputs,
    TRUST_THRESHOLD,
)
from trust_engine import TrustEngine

# --- Load everything trust_aware_routing.py's main() loads ---
sim, classifier, pipeline = load_inputs()
node_ids = sim["node_ids"]  # NOTE: these are row-index strings into processed_data.csv, not "node_101000" IDs

# --- Load GraphSAGE predictions + row->real-node_id mapping + ground truth (for risk check) ---
df = pd.read_csv('data/processed/processed_data.csv')
gnn_preds = json.load(open('outputs/gnn_node_predictions.json'))
ground_truth = json.load(open('outputs/attack_ground_truth.json'))

G = build_graph(sim["node_ids"], sim["edges"])

# --- Recompute trust scores exactly as main() does ---
df_trust = pd.DataFrame({
    "node_id": [int(nid) for nid in node_ids],
    "historical_accuracy": 0.8,
    "protocol_compliance": 0.8,
    "neighbor_recommendation": 0.5,
    "anomaly_score": [
        float(classifier.get(nid, {}).get("attack_probability", 0.2))
        for nid in node_ids
    ],
})
df_trust = TrustEngine().update_trust(df_trust)
trust_scores = {int(row.node_id): float(row.trust_score) for row in df_trust.itertuples(index=False)}

# --- Baseline exclusion set (unchanged logic) ---
baseline_excluded = get_excluded_nodes(node_ids, classifier, trust_scores)

# --- Veto-filtered exclusion set ---
# A node stays excluded if: trust_score < TRUST_THRESHOLD (unaffected by veto), OR
# (classifier flags it AND GraphSAGE agrees it's malicious).
# If classifier flags it but GraphSAGE says normal -> veto the classifier-based exclusion.
veto_excluded = set()
vetoed_nodes = []          # row indices where we removed a classifier-based exclusion
vetoed_true_attacks = []   # subset of the above where ground truth says it WAS a real attack (risk case)

for nid in node_ids:
    ts = trust_scores.get(int(nid), 1.0)
    if ts < TRUST_THRESHOLD:
        veto_excluded.add(nid)  # trust-score exclusion unaffected by veto
        continue

    pred = classifier.get(nid, {})
    if pred.get("predicted_attacked", 0) != 1:
        continue  # not flagged by classifier at all, nothing to veto

    real_node_id = df.iloc[int(nid)]['node_id']
    gnn_says_malicious = gnn_preds.get(real_node_id, {}).get('gnn_predicted_malicious', 1)  # default: don't veto if unknown

    if gnn_says_malicious == 1:
        veto_excluded.add(nid)  # both agree -> keep excluded
    else:
        vetoed_nodes.append(nid)
        true_label = ground_truth.get(nid, {}).get('is_attacked', 0)
        if true_label == 1:
            vetoed_true_attacks.append(nid)

print(f"Total simulation nodes: {len(node_ids)}")
print(f"Baseline excluded: {len(baseline_excluded)} ({100*len(baseline_excluded)/len(node_ids):.1f}%)")
print(f"Veto-filtered excluded: {len(veto_excluded)} ({100*len(veto_excluded)/len(node_ids):.1f}%)")
print(f"Nodes un-excluded by veto: {len(vetoed_nodes)}")
print(f"Of those, real attacks let back in (risk case): {len(vetoed_true_attacks)}")

# --- Run the same 200 routes under both exclusion sets ---
def run_routes(excluded_set, label):
    routes = []
    for route in sim["baseline_routes"]:
        src, dst = route["source"], route["destination"]
        result = route_with_trust(G, src, dst, excluded_set, classifier)
        routes.append({"route_id": route["route_id"], **result})

    total = len(routes)
    found = sum(1 for r in routes if r["path_found"])
    compromised = sum(1 for r in routes if r["passes_through_attacked_node"])
    avg_hops = sum(r["hop_count"] for r in routes if r["hop_count"] >= 0) / max(found, 1)
    pct_compromised = round(100.0 * compromised / total, 2)

    print(f"\n=== {label} ===")
    print(f"Excluded nodes: {len(excluded_set)}")
    print(f"Routes found: {found}/{total}")
    print(f"Compromised routes: {compromised} ({pct_compromised}%)")
    print(f"Avg hop count: {round(avg_hops, 2)}")

    return {
        "excluded_count": len(excluded_set),
        "routes_found": found,
        "compromised_routes": compromised,
        "pct_compromised": pct_compromised,
        "avg_hop_count": round(avg_hops, 2),
    }

baseline_result = run_routes(baseline_excluded, "Baseline (classifier + trust-score exclusion)")
veto_result = run_routes(veto_excluded, "GraphSAGE-veto-filtered exclusion")

print("\n=== Summary ===")
print(f"Exclusion reduction: {baseline_result['excluded_count'] - veto_result['excluded_count']} fewer nodes excluded")
print(f"Hop count change: {veto_result['avg_hop_count'] - baseline_result['avg_hop_count']:+.2f}")
print(f"Compromised-route change: {veto_result['pct_compromised'] - baseline_result['pct_compromised']:+.2f} pp")
print(f"Real attacks let back in by veto: {len(vetoed_true_attacks)} (should be ~0 for veto to be safe)")

out = {
    "baseline": baseline_result,
    "veto_filtered": veto_result,
    "vetoed_node_count": len(vetoed_nodes),
    "vetoed_true_attack_count": len(vetoed_true_attacks),
    "vetoed_true_attack_row_indices": vetoed_true_attacks,
}
with open('outputs/gnn_veto_routing_followup.json', 'w') as f:
    json.dump(out, f, indent=2)
print("\nSaved to outputs/gnn_veto_routing_followup.json")