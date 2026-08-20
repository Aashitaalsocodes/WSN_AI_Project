"""
routing_cost_uav.py
====================
UAV relay deployment, evaluated against the ACTUAL Section VI production
router: routing_cost.py's edge_cost() (real distance + real energy_risk +
real attack_risk, calibrated ATTACK_RISK_WEIGHT, divided by real trust_score),
NOT trust_aware_routing.py's route_with_soft_cost (that was the wrong target
-- see synthetic_trust_routing_grid_v4.py, now dead/unused).

This does NOT modify routing_cost.py. It re-uses its exact real-data
pipeline (position reconstruction, TrustEngine on real preprocessed_nodes.json
inputs, real classifier attack_type/confidence, the edge_cost formula and its
calibrated ATTACK_RISK_WEIGHT) but adds one new step: after routing the 200
baseline routes normally, if pct_compromised_routes for that seed crosses
UAV_TRIGGER_PCT, deploy a single UAV relay node and re-route.

MULTI-SEED: runs across the same 5 seeds used throughout the paper
(42, 7, 123, 2024, 99), matching the existing multi-seed validation standard
(per the bridge-node lesson -- a single-seed result is not sufficient
validation for a journal paper). Reports per-seed results plus mean+-std
across seeds for both the pre-UAV and post-UAV compromised-route percentage.

HOW THE UAV WORKS (same reactive design as the abandoned v4, re-targeted at
the real cost function):
1. Route all 200 baseline routes with edge_cost(), exactly as routing_cost.py
   does. This reproduces the existing Section VI number for this seed.
2. If pct_compromised_routes > UAV_TRIGGER_PCT, deploy a UAV:
     - placement: centroid of the real (reconstructed) positions of nodes
       with attack_risk > 0 in the region -- specifically, the node with the
       highest LOCAL DENSITY of positive-attack_risk neighbors within
       UAV_DENSITY_RADIUS (an observed-risk signal built the same way
       compute_cluster_density works in trust_aware_routing.py: proximity to
       classifier-flagged nodes, not oracle ground truth about which nodes
       are "really" compromised vs just flagged).
     - connects to its K nearest real nodes (by real reconstructed distance)
       within UAV_CONNECT_RADIUS
     - given node features that make edge_cost want to use it: distance=0
       on its edges is impossible to fake honestly (real hover position has
       real distance to each neighbor), so instead its OWN feature contribution
       is: energy_risk=0.0 (freshly charged, not battery-depleted like a
       ground sensor), attack_risk=0.0 (not a candidate for compromise,
       defender-controlled), trust_score=1.0 (max). Distance is computed
       honestly from its real hover coordinates to each connected neighbor,
       same as every other edge in the graph.
3. Re-route all 200 routes with the UAV in the graph, report
   uav_pct_compromised_routes for that seed.

Requires the same working directory / outputs/ layout as routing_cost.py:
outputs/routing_simulation_seed{N}.json, outputs/attack_classification_results.json,
outputs/preprocessed_nodes.json, outputs/attack_classifier_predictions.json
(for position reconstruction), and trust_engine.py importable on the path.

Usage:
    python routing_cost_uav.py --quick     # 1 seed (42), sanity check
    python routing_cost_uav.py              # full run, all 5 seeds
"""

import argparse
import json
import math
import os
import random
import time

import networkx as nx
import pandas as pd

try:
    import numpy as np
except ImportError:
    np = None

from trust_engine import TrustEngine

_parser = argparse.ArgumentParser()
_parser.add_argument("--quick", action="store_true",
                      help="Fast sanity check: seed 42 only instead of all 5 seeds.")
_args = _parser.parse_args()

SEEDS = [42] if _args.quick else [42, 7, 123, 2024, 99]

OUTPUTS_DIR = "outputs"
OUTPUT_PATH = f"{OUTPUTS_DIR}/routing_cost_uav_summary.json" if not _args.quick \
    else f"{OUTPUTS_DIR}/routing_cost_uav_summary_QUICKTEST.json"

# Same calibrated weights as the live routing_cost.py (post-recalibration).
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

# --- NEW: UAV relay config ---
UAV_TRIGGER_PCT = 15.0          # deploy UAV if pct_compromised_routes exceeds this
UAV_NODE_ID = "UAV"
UAV_ENERGY_RISK = 0.0           # freshly charged, defender-controlled
UAV_ATTACK_RISK = 0.0           # not a candidate for compromise
UAV_TRUST_SCORE = 1.0           # max trust
UAV_DENSITY_RADIUS = 0.15       # unit-square radius used to find the attack-dense region
UAV_CONNECT_K = 6               # connect UAV to its K nearest real nodes
UAV_CONNECT_RADIUS = 0.35       # aerial relay range in the same unit-square coordinate system


def mean_std(values):
    vals = [v for v in values if v is not None]
    if not vals:
        return {"mean": None, "std": 0.0, "raw": values}
    return {
        "mean": round(sum(vals) / len(vals), 4),
        "std": round((sum((v - sum(vals) / len(vals)) ** 2 for v in vals) / len(vals)) ** 0.5, 4) if len(vals) > 1 else 0.0,
        "raw": [round(v, 4) if v is not None else None for v in values],
    }


def reconstruct_positions(seed):
    """UNCHANGED from routing_cost.py: deterministically reproduces the
    exact 2D positions used to build routing_simulation.json."""
    with open(f"{OUTPUTS_DIR}/attack_classifier_predictions.json") as f:
        attack_preds = json.load(f)
    all_ids = list(attack_preds.keys())
    random.seed(seed)
    sampled_ids = random.sample(all_ids, 500)
    positions = {nid: (random.uniform(0, 1), random.uniform(0, 1)) for nid in sampled_ids}
    return positions


def build_node_features(node_ids, classifier, nodes_raw):
    """UNCHANGED from routing_cost.py."""
    rows = []
    for nid in node_ids:
        node_record = nodes_raw.get(nid, {})
        pred = classifier.get(nid, {})

        historical_accuracy = node_record.get("historical_accuracy", 0.5)
        protocol_compliance = node_record.get("protocol_compliance", 0.5)
        neighbor_recommendation = node_record.get("neighbor_recommendation", 0.5)
        energy_risk = node_record.get("energy_risk", 0.5)

        attack_type = pred.get("attack_type", "Normal")
        confidence = pred.get("confidence", 0.5)
        attack_risk = ATTACK_RISK_WEIGHT.get(attack_type, 0.5) * confidence

        rows.append({
            "node_id": nid,
            "historical_accuracy": historical_accuracy,
            "protocol_compliance": protocol_compliance,
            "neighbor_recommendation": neighbor_recommendation,
            "anomaly_score": attack_risk,
            "energy_risk": energy_risk,
            "attack_risk": attack_risk,
            "attack_type": attack_type,
        })
    return pd.DataFrame(rows)


def route_all(G, sim, node_feat, label=""):
    """Route all baseline routes with edge_cost, exactly as routing_cost.py
    does. Returns (results, pct_compromised, avg_hops)."""

    def edge_cost(u, v, edge_attrs):
        fu, fv = node_feat[u], node_feat[v]
        avg_energy = (fu.energy_risk + fv.energy_risk) / 2
        avg_attack = (fu.attack_risk + fv.attack_risk) / 2
        avg_trust = max((fu.trust_score + fv.trust_score) / 2, 0.01)
        distance = edge_attrs["distance"]
        return (W_DISTANCE * distance + W_ENERGY * avg_energy + W_ATTACK * avg_attack) / avg_trust

    results = []
    for route in sim["baseline_routes"]:
        src, dst = route["source"], route["destination"]
        try:
            path = nx.dijkstra_path(G, src, dst, weight=edge_cost)
            attacked_in_path = [n for n in path if node_feat[n].attack_type != "Normal" and n not in (src, dst)]
            results.append({
                "route_id": route["route_id"], "source": src, "destination": dst,
                "path": path, "hop_count": len(path) - 1,
                "passes_through_attacked_node": len(attacked_in_path) > 0,
                "path_found": True,
            })
        except nx.NetworkXNoPath:
            results.append({
                "route_id": route["route_id"], "source": src, "destination": dst,
                "path": [], "hop_count": -1, "passes_through_attacked_node": False,
                "path_found": False,
            })

    found = [r for r in results if r["path_found"]]
    compromised = sum(1 for r in found if r["passes_through_attacked_node"])
    pct_compromised = round(100 * compromised / len(found), 2) if found else None
    avg_hops = round(sum(r["hop_count"] for r in found) / len(found), 2) if found else None
    print(f"    [{label}] {len(found)}/{len(results)} routes found, "
          f"{compromised} compromised ({pct_compromised}%)", flush=True)
    return results, pct_compromised, avg_hops


# ============================================================
# NEW FUNCTION: deploy_uav_relay()
#
# Reactive: only called after pct_compromised_routes for this seed is
# already known to have crossed UAV_TRIGGER_PCT. Placement uses a local
# density of classifier-flagged (attack_risk > 0) real nodes -- the same
# "observed risk" signal trust_aware_routing.py's compute_cluster_density
# is built from -- not oracle knowledge of which flags are "really" true
# attacks vs false positives.
# ============================================================
def deploy_uav_relay(G, positions, node_feat, node_ids):
    flagged = [nid for nid in node_ids if node_feat[nid].attack_risk > 0.0]

    def local_flagged_density(nid):
        nx_, ny_ = positions[nid]
        count = 0
        for other in flagged:
            if other == nid:
                continue
            ox, oy = positions[other]
            if math.hypot(nx_ - ox, ny_ - oy) <= UAV_DENSITY_RADIUS:
                count += 1
        return count

    if flagged:
        anchor = max(node_ids, key=local_flagged_density)
    else:
        anchor = node_ids[0]
    ax, ay = positions[anchor]
    uav_pos = (min(1.0, max(0.0, ax)), min(1.0, max(0.0, ay)))
    positions = dict(positions)
    positions[UAV_NODE_ID] = uav_pos

    candidates = []
    for nid in node_ids:
        nx_, ny_ = positions[nid]
        dist = math.hypot(uav_pos[0] - nx_, uav_pos[1] - ny_)
        if dist <= UAV_CONNECT_RADIUS:
            candidates.append((dist, nid))
    candidates.sort(key=lambda t: t[0])

    G_uav = G.copy()
    G_uav.add_node(UAV_NODE_ID)
    for dist, nid in candidates[:UAV_CONNECT_K]:
        G_uav.add_edge(UAV_NODE_ID, nid, distance=dist)

    return G_uav, positions, anchor


def run_seed(seed):
    print(f"\n-- seed {seed} --", flush=True)
    t_start = time.time()

    # NEW: pin global randomness before TrustEngine.update_trust() runs --
    # see routing_cost_uav_stress.py for the determinism bug this fixes.
    random.seed(seed)
    if np is not None:
        np.random.seed(seed)

    with open(f"{OUTPUTS_DIR}/routing_simulation_seed{seed}.json") as f:
        sim = json.load(f)
    with open(f"{OUTPUTS_DIR}/attack_classification_results.json") as f:
        classifier = json.load(f)
    try:
        with open(f"{OUTPUTS_DIR}/preprocessed_nodes.json") as f:
            nodes_raw = json.load(f)
    except FileNotFoundError:
        print("    !! preprocessed_nodes.json not found -- falling back to 0.5 defaults "
              "(matches routing_cost.py's own .get(..., 0.5) behavior). Applied identically "
              "before and after UAV deployment, so the comparison remains valid.", flush=True)
        nodes_raw = {}
    positions = reconstruct_positions(seed)

    node_ids = sim["node_ids"]
    print(f"    building real feature set for {len(node_ids)} nodes...", flush=True)
    df = build_node_features(node_ids, classifier, nodes_raw)
    df = TrustEngine().update_trust(df)
    node_feat = {row.node_id: row for row in df.itertuples(index=False)}

    G = nx.Graph()
    G.add_nodes_from(node_ids)
    for u, v in sim["edges"]:
        ux, uy = positions[u]
        vx, vy = positions[v]
        dist = math.sqrt((ux - vx) ** 2 + (uy - vy) ** 2)
        G.add_edge(u, v, distance=dist)

    print(f"    routing 200 baseline routes (pre-UAV, matches routing_cost.py)...", flush=True)
    _, pct_compromised, avg_hops = route_all(G, sim, node_feat, label="pre-UAV")

    uav_deployed = pct_compromised is not None and pct_compromised >= UAV_TRIGGER_PCT
    uav_pct_compromised = None
    uav_avg_hops = None
    uav_anchor = None

    if uav_deployed:
        print(f"    pct_compromised={pct_compromised}% > {UAV_TRIGGER_PCT}% trigger -- deploying UAV", flush=True)
        G_uav, positions_uav, uav_anchor = deploy_uav_relay(G, positions, node_feat, node_ids)

        node_feat_uav = dict(node_feat)
        # Lightweight namedtuple-like stand-in for the UAV's own feature row,
        # matching the attributes edge_cost() reads (energy_risk, attack_risk,
        # trust_score, attack_type).
        class _UavFeat:
            energy_risk = UAV_ENERGY_RISK
            attack_risk = UAV_ATTACK_RISK
            trust_score = UAV_TRUST_SCORE
            attack_type = "Normal"
        node_feat_uav[UAV_NODE_ID] = _UavFeat()

        print(f"    routing 200 baseline routes (post-UAV)...", flush=True)
        _, uav_pct_compromised, uav_avg_hops = route_all(G_uav, sim, node_feat_uav, label="post-UAV")
    else:
        print(f"    pct_compromised={pct_compromised}% <= {UAV_TRIGGER_PCT}% trigger -- UAV not deployed", flush=True)

    elapsed = time.time() - t_start
    print(f"    seed {seed} done in {elapsed:.1f}s", flush=True)

    return {
        "seed": seed,
        "pct_compromised_routes": pct_compromised,
        "avg_hop_count": avg_hops,
        "uav_deployed": uav_deployed,
        "uav_anchor_node": uav_anchor,
        "uav_pct_compromised_routes": uav_pct_compromised,
        "uav_avg_hop_count": uav_avg_hops,
    }


def main():
    if _args.quick:
        print("*** QUICK MODE: seed 42 only -- sanity check, not for the paper ***\n", flush=True)

    print("=" * 70)
    print("UAV RELAY vs routing_cost.py's edge_cost() (Section VI production router)")
    print("=" * 70, flush=True)

    per_seed = [run_seed(seed) for seed in SEEDS]

    trig = [r for r in per_seed if r["uav_deployed"]]

    summary = {
        "quick_mode": _args.quick,
        "seeds_used": SEEDS,
        "uav_trigger_pct": UAV_TRIGGER_PCT,
        "uav_connect_k": UAV_CONNECT_K,
        "uav_connect_radius": UAV_CONNECT_RADIUS,
        "weights_used": {
            "W_DISTANCE": W_DISTANCE, "W_ENERGY": W_ENERGY, "W_ATTACK": W_ATTACK,
            "attack_risk_weights_by_type": ATTACK_RISK_WEIGHT,
        },
        "per_seed_results": per_seed,
        "pre_uav_pct_compromised_routes": mean_std([r["pct_compromised_routes"] for r in per_seed]),
        "uav_trigger_count": len(trig),
        "uav_pct_compromised_routes_among_triggered": mean_std([r["uav_pct_compromised_routes"] for r in trig]),
        "pre_uav_pct_compromised_routes_among_triggered": mean_std([r["pct_compromised_routes"] for r in trig]),
    }

    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "=" * 70)
    print(f"Wrote {OUTPUT_PATH}")
    print("=" * 70)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()