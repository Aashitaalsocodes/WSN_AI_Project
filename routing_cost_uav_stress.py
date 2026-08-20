"""
routing_cost_uav_stress.py
============================
UAV Stress-Test Validation (companion to routing_cost_uav.py).

routing_cost_uav.py proved the production router (routing_cost.py's real
edge_cost(), calibrated ATTACK_RISK_WEIGHT, real trust/energy/distance) gets
0.0% compromised routes on real attack density (~9.2% attacked nodes) across
all 5 seeds -- meaning the UAV has nothing to fix under real conditions.

This script asks a different, complementary question: if attack density were
much worse than reality -- specifically, the same 25%-clustered condition
that originally produced the 21.4% number on the synthetic hard-exclusion
router -- would the UAV help the REAL router cope? This is a stress test,
not a real-conditions result: it does NOT claim 25% clustered attackers is
realistic. It exists to show the UAV is a working fallback if conditions
ever got that bad, using the actual router you ship, not a deprecated one.

Does NOT touch routing_cost.py, routing_cost_uav.py, or the synthetic grid
scripts. Reuses routing_cost.py's real pipeline exactly (position
reconstruction, real preprocessed_nodes.json energy/trust inputs, real
classifier attack_type/confidence, edge_cost() formula) up through node
feature construction, then adds ONE new step before routing: synthetic
attacker injection on top of the real attack set, clustered spatially near
a chokepoint, to bring total attacked-node percentage from ~9.2% (real) up
to TARGET_MALICIOUS_PCT (25%, matching the original clustered-attacker
condition this whole investigation started from).

Injected nodes are drawn from real attack-type ratios (ATTACK_TYPE_WEIGHTS,
same distribution as digital_twin_sim.py -- i.e. still mostly blackhole/
grayhole/tdma/flooding in realistic proportion to each other, just more of
them), not a single attack type, so the stress condition isn't distorted
toward whichever attack edge_cost happens to penalize hardest.

Multi-seed: same 5 seeds as the rest of the paper (42, 7, 123, 2024, 99).

For each seed, reports FOUR numbers:
  - baseline_pct_compromised          : real attack density, no injection, no UAV (= routing_cost_uav.py's pre-UAV number, reproduced here as a sanity check)
  - stressed_pct_compromised          : 25% clustered (real + injected), no UAV
  - stressed_uav_pct_compromised      : 25% clustered, WITH UAV deployed
  - improvement_percentage_points     : stressed_pct_compromised - stressed_uav_pct_compromised

Usage:
    python routing_cost_uav_stress.py --quick     # seed 42 only
    python routing_cost_uav_stress.py              # full 5-seed run
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
OUTPUT_PATH = f"{OUTPUTS_DIR}/routing_cost_uav_stress_summary.json" if not _args.quick \
    else f"{OUTPUTS_DIR}/routing_cost_uav_stress_summary_QUICKTEST.json"

# Same calibrated weights as the live routing_cost.py -- the stress test
# evaluates the REAL router, just under a harder attack condition, so the
# router's own weights must stay identical to routing_cost_uav.py's.
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

# --- Stress-injection config ---
TARGET_MALICIOUS_PCT = 0.25   # matches the original clustered-attacker condition (21.4% figure)
# Real relative attack-type ratios (from digital_twin_sim.py's ATTACK_TYPE_WEIGHTS,
# excluding "none"), used so injected nodes aren't all one attack type.
INJECTED_ATTACK_TYPE_WEIGHTS = {
    "Blackhole": 2.7,
    "Grayhole": 3.9,
    "TDMA": 1.8,
    "Flooding": 0.9,
}
INJECTED_TYPES = list(INJECTED_ATTACK_TYPE_WEIGHTS.keys())
INJECTED_WEIGHTS = list(INJECTED_ATTACK_TYPE_WEIGHTS.values())
INJECTED_CONFIDENCE_RANGE = (0.80, 0.95)  # realistic high-confidence detection range

# --- UAV relay config ---
UAV_TRIGGER_PCT = 15.0
UAV_NODE_ID = "UAV"          # base id; deployed instances are UAV_0, UAV_1, ...
UAV_ENERGY_RISK = 0.0
UAV_ATTACK_RISK = 0.0
UAV_TRUST_SCORE = 1.0
UAV_MAX_COUNT = 10            # deploy at up to this many top chokepoints


def mean_std(values):
    vals = [v for v in values if v is not None]
    if not vals:
        return {"mean": None, "std": 0.0, "raw": values}
    m = sum(vals) / len(vals)
    return {
        "mean": round(m, 4),
        "std": round((sum((v - m) ** 2 for v in vals) / len(vals)) ** 0.5, 4) if len(vals) > 1 else 0.0,
        "raw": [round(v, 4) if v is not None else None for v in values],
    }


def reconstruct_positions(seed):
    """UNCHANGED from routing_cost.py."""
    with open(f"{OUTPUTS_DIR}/attack_classifier_predictions.json") as f:
        attack_preds = json.load(f)
    all_ids = list(attack_preds.keys())
    random.seed(seed)
    sampled_ids = random.sample(all_ids, 500)
    positions = {nid: (random.uniform(0, 1), random.uniform(0, 1)) for nid in sampled_ids}
    return positions


def build_node_features(node_ids, classifier, nodes_raw):
    """UNCHANGED from routing_cost.py -- builds the REAL feature rows before
    any stress injection happens."""
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


# ============================================================
# NEW FUNCTION: inject_stress_attackers()
#
# Takes the real feature DataFrame and adds synthetic attacked nodes,
# clustered spatially near a random chokepoint (same clustering method
# v2/v3's pick_malicious_nodes used: nearest-to-a-random-center), until
# total malicious percentage reaches TARGET_MALICIOUS_PCT. Only Normal
# (real, non-attacked) nodes are eligible for injection -- already-real-
# attacked nodes are left alone.
# ============================================================
def inject_stress_attackers(df, positions, seed):
    rng = random.Random(seed + 9999)  # separate stream from position reconstruction

    node_ids = df["node_id"].tolist()
    already_attacked = set(df.loc[df["attack_type"] != "Normal", "node_id"])
    total_nodes = len(node_ids)
    target_total_malicious = round(total_nodes * TARGET_MALICIOUS_PCT)
    num_to_inject = max(0, target_total_malicious - len(already_attacked))

    normal_ids = [nid for nid in node_ids if nid not in already_attacked]

    if num_to_inject == 0 or not normal_ids:
        return df, set(), already_attacked

    center = (rng.uniform(0, 1), rng.uniform(0, 1))
    ranked = sorted(
        normal_ids,
        key=lambda nid: math.hypot(
            positions[nid][0] - center[0], positions[nid][1] - center[1]
        ),
    )
    injected_ids = set(ranked[:num_to_inject])

    df = df.copy()
    # Iterate the deterministic RANKED LIST, not the injected_ids set --
    # Python set iteration order for strings is hash-randomized per process
    # (PYTHONHASHSEED), so iterating the set here made which node received
    # which random draw non-reproducible even with rng properly seeded.
    for nid in ranked[:num_to_inject]:
        attack_type = rng.choices(INJECTED_TYPES, weights=INJECTED_WEIGHTS, k=1)[0]
        confidence = rng.uniform(*INJECTED_CONFIDENCE_RANGE)
        attack_risk = ATTACK_RISK_WEIGHT[attack_type] * confidence
        idx = df.index[df["node_id"] == nid][0]
        df.at[idx, "attack_type"] = attack_type
        df.at[idx, "attack_risk"] = attack_risk
        df.at[idx, "anomaly_score"] = attack_risk  # feeds TrustEngine, same as real pipeline

    final_malicious = already_attacked | injected_ids
    return df, injected_ids, final_malicious


def route_all(G, sim, node_feat, label="", uav_ids=None):
    """Identical to routing_cost_uav.py's route_all, plus (NEW) diagnostics:
    tracks how many computed paths actually pass through any node in
    uav_ids, so we can tell whether a deployed UAV is being used at all
    versus just sitting in the graph unused."""
    uav_ids = uav_ids or set()

    def edge_cost(u, v, edge_attrs):
        fu, fv = node_feat[u], node_feat[v]
        avg_energy = (fu.energy_risk + fv.energy_risk) / 2
        avg_attack = (fu.attack_risk + fv.attack_risk) / 2
        avg_trust = max((fu.trust_score + fv.trust_score) / 2, 0.01)
        distance = edge_attrs["distance"]
        return (W_DISTANCE * distance + W_ENERGY * avg_energy + W_ATTACK * avg_attack) / avg_trust

    results = []
    uav_used_count = 0
    uav_used_and_still_compromised = 0
    for route in sim["baseline_routes"]:
        src, dst = route["source"], route["destination"]
        try:
            path = nx.dijkstra_path(G, src, dst, weight=edge_cost)
            attacked_in_path = [n for n in path if node_feat[n].attack_type != "Normal" and n not in (src, dst)]
            used_uav = any(n in uav_ids for n in path)
            is_compromised = len(attacked_in_path) > 0
            if used_uav:
                uav_used_count += 1
                if is_compromised:
                    uav_used_and_still_compromised += 1
            results.append({
                "route_id": route["route_id"], "source": src, "destination": dst,
                "path": path, "hop_count": len(path) - 1,
                "passes_through_attacked_node": is_compromised,
                "used_uav": used_uav,
                "path_found": True,
            })
        except nx.NetworkXNoPath:
            results.append({
                "route_id": route["route_id"], "source": src, "destination": dst,
                "path": [], "hop_count": -1, "passes_through_attacked_node": False,
                "used_uav": False, "path_found": False,
            })

    found = [r for r in results if r["path_found"]]
    compromised = sum(1 for r in found if r["passes_through_attacked_node"])
    pct_compromised = round(100 * compromised / len(found), 2) if found else None
    avg_hops = round(sum(r["hop_count"] for r in found) / len(found), 2) if found else None
    print(f"    [{label}] {len(found)}/{len(results)} routes found, "
          f"{compromised} compromised ({pct_compromised}%)"
          + (f" -- {uav_used_count}/{len(found)} routes used a UAV node "
             f"({uav_used_and_still_compromised} of those still compromised)"
             if uav_ids else ""), flush=True)
    return results, pct_compromised, avg_hops, uav_used_count


def route_surgical(G_uav, sim, node_feat_uav, stressed_results, uav_ids):
    """Surgical UAV routing: only routes that were ALREADY COMPROMISED under
    stress get recomputed on the UAV-augmented graph. Routes that were clean
    keep their original stressed-no-UAV path verbatim -- they are never
    given the chance to discover a UAV detour, so a clean route cannot be
    disturbed into a worse one. This isolates whether the UAV design fixes
    targeted routes without the collateral damage seen when Dijkstra is
    allowed to globally re-optimize every route against the augmented graph.
    """
    def edge_cost(u, v, edge_attrs):
        fu, fv = node_feat_uav[u], node_feat_uav[v]
        avg_energy = (fu.energy_risk + fv.energy_risk) / 2
        avg_attack = (fu.attack_risk + fv.attack_risk) / 2
        avg_trust = max((fu.trust_score + fv.trust_score) / 2, 0.01)
        distance = edge_attrs["distance"]
        return (W_DISTANCE * distance + W_ENERGY * avg_energy + W_ATTACK * avg_attack) / avg_trust

    results = []
    uav_used_count = 0
    recomputed_count = 0
    for r in stressed_results:
        if not r["path_found"]:
            results.append(dict(r, used_uav=False))
            continue

        if not r["passes_through_attacked_node"]:
            # Clean route -- keep its original path untouched. Do not let
            # Dijkstra re-route it just because a UAV now exists somewhere
            # in the graph.
            results.append(dict(r, used_uav=False))
            continue

        # Compromised route -- try to fix it via the UAV-augmented graph.
        recomputed_count += 1
        src, dst = r["source"], r["destination"]
        try:
            path = nx.dijkstra_path(G_uav, src, dst, weight=edge_cost)
            attacked_in_path = [n for n in path if node_feat_uav[n].attack_type != "Normal" and n not in (src, dst)]
            used_uav = any(n in uav_ids for n in path)
            is_compromised = len(attacked_in_path) > 0
            if used_uav:
                uav_used_count += 1
            results.append({
                "route_id": r["route_id"], "source": src, "destination": dst,
                "path": path, "hop_count": len(path) - 1,
                "passes_through_attacked_node": is_compromised,
                "used_uav": used_uav,
                "path_found": True,
            })
        except nx.NetworkXNoPath:
            results.append(dict(r, used_uav=False))

    found = [r for r in results if r["path_found"]]
    compromised = sum(1 for r in found if r["passes_through_attacked_node"])
    pct_compromised = round(100 * compromised / len(found), 2) if found else None
    avg_hops = round(sum(r["hop_count"] for r in found) / len(found), 2) if found else None
    print(f"    [stressed-with-UAV-surgical] {len(found)}/{len(results)} routes found, "
          f"{compromised} compromised ({pct_compromised}%) -- only recomputed "
          f"{recomputed_count} previously-compromised routes, "
          f"{uav_used_count} of those now use a UAV node", flush=True)
    return results, pct_compromised, avg_hops, uav_used_count


def find_chokepoints(results, node_feat, top_n):
    """NEW: identify the malicious node(s) actually causing compromise,
    ranked by how often each currently-compromised route passes through it.
    Replaces the old generic density-centroid placement, which put the UAV
    near attackers geographically but not necessarily ON any real route's
    actual path -- that's why it went unused (0/200 routes used it)."""
    from collections import Counter
    counter = Counter()
    for r in results:
        if not r.get("passes_through_attacked_node"):
            continue
        for n in r["path"][1:-1]:
            if node_feat[n].attack_type != "Normal":
                counter[n] += 1
    return [nid for nid, _ in counter.most_common(top_n)], counter


def deploy_uav_relays(G, positions, chokepoints):
    """Deploy one UAV PER chokepoint, each placed at that chokepoint's own
    real coordinates and wired to that chokepoint's own real graph
    neighbors. This makes each UAV a literal clean twin of a specific
    malicious node: identical distance to every neighbor that node already
    has (so the route doesn't get more expensive by detouring), but zero
    energy_risk/attack_risk (so the route gets cheaper by using the UAV
    instead). A route that currently goes ...->A->chokepoint->B->... can
    now go ...->A->UAV_i->B->... at the same distance cost, strictly
    lower total cost, without needing to discover any new path shape --
    the twin sits exactly where the risky hop already was.
    """
    G_uav = G.copy()
    positions = dict(positions)
    uav_ids = []

    for i, chokepoint in enumerate(chokepoints):
        uav_id = f"{UAV_NODE_ID}_{i}"
        uav_ids.append(uav_id)
        cx, cy = positions[chokepoint]
        positions[uav_id] = (cx, cy)
        G_uav.add_node(uav_id)
        for neighbor in G.neighbors(chokepoint):
            nx_, ny_ = positions[neighbor]
            dist = math.hypot(cx - nx_, cy - ny_)
            G_uav.add_edge(uav_id, neighbor, distance=dist)

    return G_uav, positions, uav_ids


def build_graph(node_ids, sim, positions):
    G = nx.Graph()
    G.add_nodes_from(node_ids)
    for u, v in sim["edges"]:
        ux, uy = positions[u]
        vx, vy = positions[v]
        dist = math.sqrt((ux - vx) ** 2 + (uy - vy) ** 2)
        G.add_edge(u, v, distance=dist)
    return G


def run_seed(seed):
    print(f"\n-- seed {seed} --", flush=True)
    t_start = time.time()

    # Explicit global seeding before ANY randomness this run touches.
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
        print("    !! preprocessed_nodes.json not found -- falling back to 0.5 defaults, "
              "applied identically across all conditions.", flush=True)
        nodes_raw = {}
    positions = reconstruct_positions(seed)
    node_ids = sim["node_ids"]

    # --- Real features + real baseline (reproduces routing_cost_uav.py's pre-UAV number) ---
    print(f"    building real feature set for {len(node_ids)} nodes...", flush=True)
    df_real = build_node_features(node_ids, classifier, nodes_raw)
    df_real_trust = TrustEngine().update_trust(df_real)
    node_feat_real = {row.node_id: row for row in df_real_trust.itertuples(index=False)}
    G = build_graph(node_ids, sim, positions)

    print("    routing 200 baseline routes (real attack density, no injection, no UAV)...", flush=True)
    _, baseline_pct, baseline_hops, _ = route_all(G, sim, node_feat_real, label="real-baseline")

    # --- Stress injection: same real feature rows, extra synthetic attackers ---
    real_attacked_count = int((df_real["attack_type"] != "Normal").sum())
    print(f"    real attacked nodes: {real_attacked_count}/{len(node_ids)} "
          f"({100*real_attacked_count/len(node_ids):.1f}%) -- injecting up to "
          f"{TARGET_MALICIOUS_PCT:.0%} clustered...", flush=True)
    df_stressed, injected_ids, final_malicious = inject_stress_attackers(df_real, positions, seed)
    print(f"    injected {len(injected_ids)} synthetic attackers -- "
          f"total malicious now {len(final_malicious)}/{len(node_ids)} "
          f"({100*len(final_malicious)/len(node_ids):.1f}%)", flush=True)

    df_stressed_trust = TrustEngine().update_trust(df_stressed)
    node_feat_stressed = {row.node_id: row for row in df_stressed_trust.itertuples(index=False)}

    print("    routing 200 baseline routes (stressed 25% clustered, no UAV)...", flush=True)
    stressed_results, stressed_pct, stressed_hops, _ = route_all(G, sim, node_feat_stressed, label="stressed-no-UAV")

    # --- UAV deployment under stress ---
    uav_deployed = stressed_pct is not None and stressed_pct >= UAV_TRIGGER_PCT
    stressed_uav_pct = None
    stressed_uav_hops = None
    chokepoints = []
    uav_used_count = 0
    fixed = 0
    newly_broken = 0
    stressed_uav_surgical_pct = None
    stressed_uav_surgical_hops = None
    uav_used_count_surgical = 0
    fixed_surgical = 0
    newly_broken_surgical = 0

    if uav_deployed:
        chokepoints, chokepoint_counts = find_chokepoints(stressed_results, node_feat_stressed, UAV_MAX_COUNT)
        print(f"    stressed_pct={stressed_pct}% >= {UAV_TRIGGER_PCT}% trigger -- "
              f"top chokepoint nodes (routes compromised through each): "
              f"{[(n, chokepoint_counts[n]) for n in chokepoints]}", flush=True)

        G_uav, positions_uav, uav_ids = deploy_uav_relays(G, positions, chokepoints)

        node_feat_uav = dict(node_feat_stressed)
        class _UavFeat:
            energy_risk = UAV_ENERGY_RISK
            attack_risk = UAV_ATTACK_RISK
            trust_score = UAV_TRUST_SCORE
            attack_type = "Normal"
        for uid in uav_ids:
            node_feat_uav[uid] = _UavFeat()

        print(f"    routing 200 baseline routes (stressed 25% clustered, WITH {len(uav_ids)} UAV(s), GLOBAL reroute)...", flush=True)
        uav_results, stressed_uav_pct, stressed_uav_hops, uav_used_count = route_all(
            G_uav, sim, node_feat_uav, label="stressed-with-UAV-global", uav_ids=set(uav_ids)
        )

        # Per-route flip diagnostic -- did the UAV actually fix routes,
        # or just trade some compromised routes for other newly-compromised ones?
        before_by_id = {r["route_id"]: r["passes_through_attacked_node"] for r in stressed_results}
        after_by_id = {r["route_id"]: r["passes_through_attacked_node"] for r in uav_results}
        fixed = sum(1 for rid in before_by_id if before_by_id[rid] and not after_by_id.get(rid, before_by_id[rid]))
        newly_broken = sum(1 for rid in before_by_id if not before_by_id[rid] and after_by_id.get(rid, before_by_id[rid]))
        unchanged_compromised = sum(1 for rid in before_by_id if before_by_id[rid] and after_by_id.get(rid, before_by_id[rid]))
        print(f"    [flip diagnostic - GLOBAL reroute] fixed={fixed}, newly_broken={newly_broken}, "
              f"still_compromised={unchanged_compromised} "
              f"(net change = {fixed - newly_broken}, should equal stressed_pct - stressed_uav_pct in route counts)",
              flush=True)

        # NEW: surgical comparison -- only recompute routes that were already
        # compromised; clean routes keep their original path verbatim, so they
        # can never be disturbed into a worse one by the new UAV nodes.
        surgical_results, stressed_uav_surgical_pct, stressed_uav_surgical_hops, uav_used_count_surgical = route_surgical(
            G_uav, sim, node_feat_uav, stressed_results, set(uav_ids)
        )
        surgical_after_by_id = {r["route_id"]: r["passes_through_attacked_node"] for r in surgical_results}
        fixed_surgical = sum(1 for rid in before_by_id if before_by_id[rid] and not surgical_after_by_id.get(rid, before_by_id[rid]))
        newly_broken_surgical = sum(1 for rid in before_by_id if not before_by_id[rid] and surgical_after_by_id.get(rid, before_by_id[rid]))
        # (fixed_surgical / newly_broken_surgical now populate the outer-scope
        # variables initialized before this if-block, used in the return dict below)
        print(f"    [flip diagnostic - SURGICAL] fixed={fixed_surgical}, newly_broken={newly_broken_surgical} "
              f"(should be 0 by construction -- clean routes are never recomputed), "
              f"stressed_uav_surgical_pct={stressed_uav_surgical_pct}%", flush=True)
    else:
        print(f"    stressed_pct={stressed_pct}% < {UAV_TRIGGER_PCT}% trigger -- UAV not deployed "
              f"(stress injection did not push compromise rate above trigger for this seed)", flush=True)

    improvement = (
        round(stressed_pct - stressed_uav_pct, 2)
        if stressed_pct is not None and stressed_uav_pct is not None
        else None
    )
    improvement_surgical = (
        round(stressed_pct - stressed_uav_surgical_pct, 2)
        if stressed_pct is not None and stressed_uav_surgical_pct is not None
        else None
    )

    elapsed = time.time() - t_start
    print(f"    seed {seed} done in {elapsed:.1f}s", flush=True)

    return {
        "seed": seed,
        "real_attacked_count": real_attacked_count,
        "real_attacked_pct": round(100 * real_attacked_count / len(node_ids), 2),
        "injected_attacker_count": len(injected_ids),
        "final_malicious_pct": round(100 * len(final_malicious) / len(node_ids), 2),
        "baseline_pct_compromised": baseline_pct,
        "baseline_avg_hop_count": baseline_hops,
        "stressed_pct_compromised": stressed_pct,
        "stressed_avg_hop_count": stressed_hops,
        "uav_deployed": uav_deployed,
        "uav_chokepoint_nodes": chokepoints,
        "uav_used_by_route_count": uav_used_count,   # 0 here means the UAV(s) sat unused
        "uav_routes_fixed": fixed,                   # previously-compromised routes that became clean
        "uav_routes_newly_broken": newly_broken,      # previously-clean routes that became compromised
        "stressed_uav_pct_compromised": stressed_uav_pct,
        "stressed_uav_avg_hop_count": stressed_uav_hops,
        "improvement_percentage_points": improvement,
        # Surgical variant: only previously-compromised routes are recomputed
        # on the UAV graph; clean routes keep their original path verbatim.
        "stressed_uav_surgical_pct_compromised": stressed_uav_surgical_pct,
        "stressed_uav_surgical_avg_hop_count": stressed_uav_surgical_hops,
        "uav_used_by_route_count_surgical": uav_used_count_surgical,
        "uav_routes_fixed_surgical": fixed_surgical,
        "uav_routes_newly_broken_surgical": newly_broken_surgical,
        "improvement_percentage_points_surgical": improvement_surgical,
    }


def main():
    if _args.quick:
        print("*** QUICK MODE: seed 42 only -- sanity check, not for the paper ***\n", flush=True)

    print("=" * 70)
    print("UAV STRESS-TEST VALIDATION (real router edge_cost(), synthetic 25% clustered attack density)")
    print("=" * 70, flush=True)

    per_seed = [run_seed(seed) for seed in SEEDS]
    trig = [r for r in per_seed if r["uav_deployed"]]

    summary = {
        "quick_mode": _args.quick,
        "seeds_used": SEEDS,
        "target_malicious_pct": TARGET_MALICIOUS_PCT,
        "uav_trigger_pct": UAV_TRIGGER_PCT,
        "uav_max_count": UAV_MAX_COUNT,
        "weights_used": {
            "W_DISTANCE": W_DISTANCE, "W_ENERGY": W_ENERGY, "W_ATTACK": W_ATTACK,
            "attack_risk_weights_by_type": ATTACK_RISK_WEIGHT,
        },
        "per_seed_results": per_seed,
        "baseline_pct_compromised": mean_std([r["baseline_pct_compromised"] for r in per_seed]),
        "stressed_pct_compromised": mean_std([r["stressed_pct_compromised"] for r in per_seed]),
        "uav_trigger_count": len(trig),
        "stressed_uav_pct_compromised_among_triggered": mean_std([r["stressed_uav_pct_compromised"] for r in trig]),
        "improvement_percentage_points_among_triggered": mean_std([r["improvement_percentage_points"] for r in trig]),
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