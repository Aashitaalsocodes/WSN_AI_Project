"""
recalibration_ablation.py
==========================
Priority 1 (Section VII.D): With/Without Recalibration Comparison.

Runs TWO conditions across the same 5 seeds (42, 7, 123, 2024, 99) used
throughout the paper, and reports PDR / compromised-routes % / detection
accuracy & recall for each:

  (a) WITHOUT recalibration — the original, pre-Task-8 flat heuristic
      guesses: detection_miss_rate = 0.18 for every attack type
      (from build_recalibration_report.py's ORIGINAL_DETECTION_MISS_RATE),
      and attack_risk_weight = {TDMA: 0.3, Flooding: 0.6, Grayhole: 0.8,
      Blackhole: 1.0} (ORIGINAL_ATTACK_RISK_WEIGHTS).

  (b) WITH recalibration — the current, converged values already live in
      digital_twin_sim.py's DETECTION_MISS_RATE_BY_TYPE and
      routing_cost.py's ATTACK_RISK_WEIGHT (post-7-cycle convergence).

This does NOT modify digital_twin_sim.py or routing_cost.py. It re-uses
their actual imported logic (TrustEngine, build_graph, route_with_trust,
simulate_packet_delivery, the routing_cost edge-cost formula) but drives
each with an explicit parameter dict instead of the hardcoded module-level
constant, so the two conditions are genuinely apples-to-apples on
everything except the recalibrated values themselves.

Two separate ablations are run, matching the two places recalibration
actually changes behavior in this codebase:

  1. Section VIII ablation (digital_twin_sim.py logic): detection-miss-rate
     changes what TA-DT actually excludes each round -> affects PDR,
     compromised-routes %, detection accuracy/recall.
  2. Section VI ablation (routing_cost.py logic): attack-risk-weight
     changes the routing cost formula's attack penalty -> affects the
     200-route cost-aware routing test's compromised-routes %.

PROGRESS LOGGING: prints after every round and every seed, with elapsed
time, so the terminal is never silent for more than a few seconds — if it
looks "stuck" with no output at all for minutes, something is actually
wrong (see troubleshooting notes at the bottom of this docstring), it is
not just slow.

QUICK MODE: run with `--quick` to do a fast smoke test first — 1 seed,
3 rounds instead of 5 seeds x 23 rounds — to confirm your outputs/ files
and imports are wired correctly before committing to the full run (which
can take anywhere from a few minutes to a long while depending on your
machine, since it's 10 full simulations back to back).

    python recalibration_ablation.py --quick     # ~30 seconds, sanity check
    python recalibration_ablation.py              # full run, all 5 seeds

Requires: same working directory / outputs/ layout as digital_twin_sim.py
and routing_cost.py (routing_simulation.json, routing_simulation_seed{N}.json,
energy_forecast_ibrl.json, attack_classification_results.json,
preprocessed_nodes.json, attack_classifier_predictions.json), and the
project's own trust_engine.py, config.py, trust_aware_routing.py,
packet_transmission_model.py importable on the path (i.e. run this from
the same folder as digital_twin_sim.py).

TROUBLESHOOTING if it prints the section header and then truly nothing
for a very long time with no round-by-round lines at all:
  - Most likely cause: outputs/routing_simulation.json or
    outputs/energy_forecast_ibrl.json is much larger than expected, or
    TrustEngine.update_trust() is doing something expensive per call.
    Add `print(..., flush=True)` isn't the issue here since this version
    already flushes every line — if you see zero lines, the hang is
    inside build_graph()/load_dt_inputs() before the round loop starts.
  - Try `--quick` first; if that also hangs with zero output, the problem
    is in setup (file loading / graph building), not the round loop.
"""

import argparse
import json
import math
import os
import random
import statistics
import statistics as stats
import time

import networkx as nx
import pandas as pd

from trust_engine import TrustEngine
from config import TRUST_THRESHOLD
from trust_aware_routing import build_graph, route_with_trust
from packet_transmission_model import simulate_packet_delivery

_parser = argparse.ArgumentParser()
_parser.add_argument("--quick", action="store_true",
                      help="Fast smoke test: 1 seed, 3 rounds instead of 5 seeds x 23 rounds.")
_parser.add_argument("--section-vi-only", action="store_true",
                      help="Skip Section VIII (digital_twin_sim.py ablation) entirely and "
                           "only run Section VI (routing_cost.py ablation). Use this if "
                           "Section VIII already completed successfully in a previous run "
                           "and you just need to re-run Section VI after a fix.")
_args = _parser.parse_args()

SEEDS = [42] if _args.quick else [42, 7, 123, 2024, 99]
NUM_ROUNDS = 3 if _args.quick else 23
DEAD_ENERGY_THRESHOLD = 0.0

OUTPUT_PATH = "outputs/recalibration_ablation_summary.json" if not _args.quick \
    else "outputs/recalibration_ablation_summary_QUICKTEST.json"

ATTACK_TYPE_WEIGHTS = {
    "none": 90.8,
    "blackhole": 2.7,
    "grayhole": 3.9,
    "tdma": 1.8,
    "flooding": 0.9,
}
ATTACK_TYPES = list(ATTACK_TYPE_WEIGHTS.keys())
ATTACK_WEIGHTS = list(ATTACK_TYPE_WEIGHTS.values())

ATTACK_ENERGY_PENALTY = {
    "blackhole": 0.35,
    "grayhole": 0.25,
    "flooding": 0.45,
    "tdma": 0.15,
}

# --- Section VIII (digital_twin_sim.py) recalibration values ---
# "Without recalibration": flat, uncalibrated heuristic guess used before
# Task 8 (from build_recalibration_report.py:ORIGINAL_DETECTION_MISS_RATE)
ORIGINAL_DETECTION_MISS_RATE = {
    "blackhole": 0.18, "grayhole": 0.18, "flooding": 0.18, "tdma": 0.18,
}
# "With recalibration": current converged per-type values, copied verbatim
# from the live DETECTION_MISS_RATE_BY_TYPE in digital_twin_sim.py
# (verified against recalibration_report.json's "currently_applied" values).
CURRENT_DETECTION_MISS_RATE = {
    "blackhole": 0.2469, "grayhole": 0.1038, "flooding": 0.0103, "tdma": 0.1343,
}

# --- Section VI (routing_cost.py) recalibration values ---
# "Without recalibration": original flat/heuristic attack-risk weights
# (build_recalibration_report.py:ORIGINAL_ATTACK_RISK_WEIGHTS), keyed to
# match routing_cost.py's Title-case attack_type strings.
ORIGINAL_ATTACK_RISK_WEIGHT = {
    "Normal": 0.0, "TDMA": 0.3, "Flooding": 0.6, "Grayhole": 0.8, "Blackhole": 1.0,
}
# "With recalibration": current converged weights, copied verbatim from the
# live ATTACK_RISK_WEIGHT in routing_cost.py.
CURRENT_ATTACK_RISK_WEIGHT = {
    "Normal": 0.0, "TDMA": 0.1354, "Flooding": 0.0052, "Grayhole": 0.2969, "Blackhole": 0.5938,
}

W_DISTANCE = 1.0
W_ENERGY = 1.0
W_ATTACK = 2.0


def mean_std(values):
    return {
        "mean": round(stats.mean(values), 4),
        "std": round(stats.pstdev(values), 4) if len(values) > 1 else 0.0,
        "raw": [round(v, 4) for v in values],
    }


# =====================================================================
# SECTION VIII ablation — digital_twin_sim.py logic, parameterized by
# a detection_miss_rate dict instead of the hardcoded module constant.
# =====================================================================

def load_dt_inputs():
    print("    loading outputs/routing_simulation.json and energy_forecast_ibrl.json...", flush=True)
    with open("outputs/routing_simulation.json") as f:
        sim = json.load(f)
    with open("outputs/energy_forecast_ibrl.json") as f:
        energy = json.load(f)
    print(f"    loaded: {len(sim['node_ids'])} nodes, {len(sim['baseline_routes'])} baseline routes", flush=True)
    return sim, energy


def build_energy_trend(energy_forecast):
    voltages = list(energy_forecast["next_voltage_forecast_volts"].values())
    mean_v = statistics.mean(voltages)
    std_v = statistics.stdev(voltages)
    return mean_v, std_v


def simulate_round_dt(round_num, node_ids, energy_state, mean_v, std_v,
                       decay_multiplier, detection_miss_rate):
    attacked_nodes = []
    attacked_node_types = {}
    classifier = {}
    row_ids = []
    rows = []

    base_decay = 0.03 + (round_num * 0.004)

    for nid in node_ids:
        attack_type = random.choices(ATTACK_TYPES, weights=ATTACK_WEIGHTS, k=1)[0]
        is_attacked = attack_type != "none"
        if is_attacked:
            attacked_nodes.append(nid)
            attacked_node_types[nid] = attack_type

        jitter = random.gauss(0, std_v) / mean_v
        node_decay = base_decay * decay_multiplier[nid]
        if is_attacked:
            node_decay *= (1.0 + ATTACK_ENERGY_PENALTY[attack_type])
        energy_state[nid] = max(0.0, energy_state[nid] - node_decay + (jitter * 0.01))

        if is_attacked:
            detected = random.random() > detection_miss_rate[attack_type]
        else:
            detected = False

        base_anomaly = random.uniform(0.75, 1.0) if detected else random.uniform(0.0, 0.2)
        energy_penalty = 0.15 if energy_state[nid] < 0.2 else 0.0
        anomaly_score = min(1.0, base_anomaly + energy_penalty)

        classifier[nid] = {
            "attack_probability": anomaly_score,
            "predicted_attacked": 1 if detected else 0,
        }

        row_ids.append(nid)
        rows.append({
            "historical_accuracy": 0.8,
            "protocol_compliance": 0.8,
            "neighbor_recommendation": 0.5,
            "anomaly_score": anomaly_score,
        })

    return attacked_nodes, attacked_node_types, classifier, row_ids, rows


def run_digital_twin(seed, detection_miss_rate, label):
    """One full digital_twin_sim.py run, parameterized by
    detection_miss_rate. Returns per-round PDR / compromised% plus
    tp/fp/tn totals for accuracy & recall, matching aggregate_routing_
    multiseed.py's formula exactly. `label` is just for progress printing."""
    random.seed(seed)

    sim, energy_forecast = load_dt_inputs()
    node_ids = sim["node_ids"]
    edges = sim["edges"]
    baseline_routes = sim["baseline_routes"]

    print(f"    building graph ({len(node_ids)} nodes, {len(edges)} edges)...", flush=True)
    G = build_graph(node_ids, edges)
    mean_v, std_v = build_energy_trend(energy_forecast)

    energy_state = {nid: 1.0 for nid in node_ids}
    engine = TrustEngine()

    print("    computing forwarding-centrality decay multiplier...", flush=True)
    forwarding_count = {nid: 0 for nid in node_ids}
    for route in baseline_routes:
        src, dst = route["source"], route["destination"]
        try:
            path = nx.shortest_path(G, src, dst)
            for nid in path[1:-1]:
                forwarding_count[nid] += 1
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            continue
    max_fc = max(forwarding_count.values()) if forwarding_count.values() else 1
    max_fc = max(max_fc, 1)

    decay_multiplier = {
        nid: 0.7 + 0.3 * min(forwarding_count[nid] / max_fc, 1.0) + random.uniform(-0.05, 0.05)
        for nid in node_ids
    }

    total_nodes = len(node_ids)
    pdr_vals, compromised_vals = [], []
    total_tp = total_fp = total_tn = total_attacked = 0
    t_start = time.time()

    print(f"    [{label}] starting {NUM_ROUNDS}-round simulation...", flush=True)
    for round_num in range(NUM_ROUNDS):
        attacked_nodes, attacked_node_types, classifier, row_ids, rows = simulate_round_dt(
            round_num, node_ids, energy_state, mean_v, std_v, decay_multiplier, detection_miss_rate
        )

        df = pd.DataFrame(rows)
        trust_df = engine.update_trust(df)
        trust_scores = dict(zip(row_ids, trust_df["trust_score"].values))

        excluded = {
            nid for nid in node_ids
            if classifier[nid]["predicted_attacked"] == 1
            or trust_scores.get(nid, 1.0) < TRUST_THRESHOLD
        }
        true_attacked_set = set(attacked_nodes)
        missed_detections = sorted(true_attacked_set - excluded)

        compromised = 0
        paths_this_round = {}
        for route in baseline_routes:
            result = route_with_trust(G, route["source"], route["destination"], excluded, classifier)
            if result.get("path_found"):
                path = result.get("path", [])
                paths_this_round[(route["source"], route["destination"])] = path
                intermediate_nodes = path[1:-1] if len(path) > 2 else []
                attacked_intermediates = [nid for nid in intermediate_nodes if nid in true_attacked_set]
                if attacked_intermediates:
                    compromised += 1
            else:
                paths_this_round[(route["source"], route["destination"])] = None

        compromised_pct = round((compromised / len(baseline_routes)) * 100, 2)
        compromised_vals.append(compromised_pct)

        packet_result = simulate_packet_delivery(baseline_routes, paths_this_round, attacked_node_types)
        pdr_vals.append(packet_result["pdr_pct"])

        # tp/fp/tn accumulation — identical formula to aggregate_routing_multiseed.py
        attacked_count = len(attacked_nodes)
        excluded_count = len(excluded)
        missed_count = len(missed_detections)
        tp = attacked_count - missed_count
        fp = excluded_count - tp
        tn = total_nodes - attacked_count - fp
        total_tp += tp
        total_fp += fp
        total_tn += tn
        total_attacked += attacked_count

        elapsed = time.time() - t_start
        print(f"    [{label}] round {round_num + 1}/{NUM_ROUNDS}  "
              f"compromised={compromised_pct}%  pdr={packet_result['pdr_pct']}%  "
              f"elapsed={elapsed:.1f}s", flush=True)

    detection_accuracy = (total_tp + total_tn) / (total_nodes * NUM_ROUNDS) * 100
    detection_recall = (total_tp / total_attacked * 100) if total_attacked else None

    return {
        "avg_pdr_pct": round(sum(pdr_vals) / len(pdr_vals), 4),
        "avg_compromised_routes_pct": round(sum(compromised_vals) / len(compromised_vals), 4),
        "detection_accuracy_pct": round(detection_accuracy, 4),
        "detection_recall_pct": round(detection_recall, 4) if detection_recall is not None else None,
    }


# =====================================================================
# SECTION VI ablation — routing_cost.py logic, parameterized by an
# attack_risk_weight dict instead of the hardcoded module constant.
# =====================================================================

def reconstruct_positions(seed):
    with open("outputs/attack_classifier_predictions.json") as f:
        attack_preds = json.load(f)
    all_ids = list(attack_preds.keys())
    random.seed(seed)
    sampled_ids = random.sample(all_ids, 500)
    positions = {nid: (random.uniform(0, 1), random.uniform(0, 1)) for nid in sampled_ids}
    return positions


def run_routing_cost(seed, attack_risk_weight, label):
    """One full 200-route cost-aware routing pass, parameterized by
    attack_risk_weight, matching routing_cost.py's edge_cost formula."""
    print(f"    [{label}] loading routing_simulation_seed{seed}.json...", flush=True)
    with open(f"outputs/routing_simulation_seed{seed}.json") as f:
        sim = json.load(f)
    with open("outputs/attack_classification_results.json") as f:
        classifier = json.load(f)
    try:
        with open("outputs/preprocessed_nodes.json") as f:
            nodes_raw = json.load(f)
    except FileNotFoundError:
        print("    !! outputs/preprocessed_nodes.json not found — falling back to "
              "0.5 defaults for historical_accuracy/protocol_compliance/"
              "neighbor_recommendation/energy_risk for ALL nodes (matches "
              "routing_cost.py's own .get(..., 0.5) fallback behavior). This is "
              "applied identically to both WITH and WITHOUT conditions, so the "
              "attack_risk_weight comparison itself remains valid; only the "
              "absolute compromised-route percentages may differ slightly from "
              "a run that had real preprocessed_nodes.json data.", flush=True)
        nodes_raw = {}
    positions = reconstruct_positions(seed)

    node_ids = sim["node_ids"]
    rows = []
    for nid in node_ids:
        node_record = nodes_raw.get(nid, {})
        pred = classifier.get(nid, {})
        attack_type = pred.get("attack_type", "Normal")
        confidence = pred.get("confidence", 0.5)
        attack_risk = attack_risk_weight.get(attack_type, 0.5) * confidence
        rows.append({
            "node_id": nid,
            "historical_accuracy": node_record.get("historical_accuracy", 0.5),
            "protocol_compliance": node_record.get("protocol_compliance", 0.5),
            "neighbor_recommendation": node_record.get("neighbor_recommendation", 0.5),
            "anomaly_score": attack_risk,
            "energy_risk": node_record.get("energy_risk", 0.5),
            "attack_risk": attack_risk,
            "attack_type": attack_type,
        })
    df = pd.DataFrame(rows)
    df = TrustEngine().update_trust(df)
    node_feat = {row.node_id: row for row in df.itertuples(index=False)}

    print(f"    [{label}] building graph with recovered positions...", flush=True)
    G = nx.Graph()
    G.add_nodes_from(node_ids)
    for u, v in sim["edges"]:
        ux, uy = positions[u]
        vx, vy = positions[v]
        dist = math.sqrt((ux - vx) ** 2 + (uy - vy) ** 2)
        G.add_edge(u, v, distance=dist)

    def edge_cost(u, v, edge_attrs):
        fu, fv = node_feat[u], node_feat[v]
        avg_energy = (fu.energy_risk + fv.energy_risk) / 2
        avg_attack = (fu.attack_risk + fv.attack_risk) / 2
        avg_trust = max((fu.trust_score + fv.trust_score) / 2, 0.01)
        distance = edge_attrs["distance"]
        return (W_DISTANCE * distance + W_ENERGY * avg_energy + W_ATTACK * avg_attack) / avg_trust

    print(f"    [{label}] routing {len(sim['baseline_routes'])} baseline routes...", flush=True)
    found, compromised, hops = 0, 0, []
    t_start = time.time()
    for i, route in enumerate(sim["baseline_routes"]):
        src, dst = route["source"], route["destination"]
        try:
            path = nx.dijkstra_path(G, src, dst, weight=edge_cost)
            found += 1
            hops.append(len(path) - 1)
            attacked_in_path = [n for n in path if node_feat[n].attack_type != "Normal" and n not in (src, dst)]
            if attacked_in_path:
                compromised += 1
        except nx.NetworkXNoPath:
            continue
        if (i + 1) % 50 == 0:
            print(f"    [{label}] {i + 1}/{len(sim['baseline_routes'])} routes done, "
                  f"elapsed={time.time() - t_start:.1f}s", flush=True)

    pct_compromised = round(100 * compromised / found, 2) if found else None
    avg_hops = round(sum(hops) / len(hops), 2) if hops else None
    print(f"    [{label}] done: {found} routes found, {compromised} compromised ({pct_compromised}%)", flush=True)
    return {"pct_compromised_routes": pct_compromised, "avg_hop_count": avg_hops, "routes_found": found}


# =====================================================================
# Main
# =====================================================================

def main():
    if _args.quick:
        print("*** QUICK MODE: 1 seed, 3 rounds — sanity check only, not for the paper ***\n", flush=True)

    if _args.section_vi_only:
        print("*** --section-vi-only: SKIPPING Section VIII, using your already-completed "
              "results from the prior successful run ***\n", flush=True)
        # Hardcoded from your actual completed run (both runs matched exactly,
        # confirming determinism): seeds 42, 7, 123, 2024, 99.
        dt_without = [
            {'avg_pdr_pct': 92.1228, 'avg_compromised_routes_pct': 5.9565, 'detection_accuracy_pct': 98.2783, 'detection_recall_pct': 81.1429},
            {'avg_pdr_pct': 92.3674, 'avg_compromised_routes_pct': 6.3478, 'detection_accuracy_pct': 98.5043, 'detection_recall_pct': 83.9102},
            {'avg_pdr_pct': 92.2957, 'avg_compromised_routes_pct': 5.8261, 'detection_accuracy_pct': 98.2348, 'detection_recall_pct': 80.3675},
            {'avg_pdr_pct': 92.0293, 'avg_compromised_routes_pct': 6.3043, 'detection_accuracy_pct': 98.2522, 'detection_recall_pct': 81.8756},
            {'avg_pdr_pct': 92.9565, 'avg_compromised_routes_pct': 4.4783, 'detection_accuracy_pct': 98.5739, 'detection_recall_pct': 84.8007},
        ]
        dt_with = [
            {'avg_pdr_pct': 91.6739, 'avg_compromised_routes_pct': 4.4783, 'detection_accuracy_pct': 98.7043, 'detection_recall_pct': 86.0225},
            {'avg_pdr_pct': 92.0739, 'avg_compromised_routes_pct': 4.7826, 'detection_accuracy_pct': 98.6435, 'detection_recall_pct': 84.9421},
            {'avg_pdr_pct': 92.0185, 'avg_compromised_routes_pct': 4.5217, 'detection_accuracy_pct': 98.6783, 'detection_recall_pct': 85.2713},
            {'avg_pdr_pct': 92.3522, 'avg_compromised_routes_pct': 4.9348, 'detection_accuracy_pct': 98.7304, 'detection_recall_pct': 86.6178},
            {'avg_pdr_pct': 92.1413, 'avg_compromised_routes_pct': 4.8478, 'detection_accuracy_pct': 98.8957, 'detection_recall_pct': 87.8236},
        ]
    else:
        print("=" * 70)
        print("SECTION VIII ABLATION (digital_twin_sim.py logic)")
        print("=" * 70, flush=True)
        dt_without, dt_with = [], []
        for seed in SEEDS:
            print(f"\n-- seed {seed} --", flush=True)
            r_without = run_digital_twin(seed, ORIGINAL_DETECTION_MISS_RATE, "WITHOUT recal")
            print(f"  WITHOUT recalibration: {r_without}", flush=True)
            r_with = run_digital_twin(seed, CURRENT_DETECTION_MISS_RATE, "WITH recal")
            print(f"  WITH recalibration:    {r_with}", flush=True)
            dt_without.append(r_without)
            dt_with.append(r_with)

    print("\n" + "=" * 70)
    print("SECTION VI ABLATION (routing_cost.py logic)")
    print("=" * 70, flush=True)
    rc_without, rc_with = [], []
    for seed in SEEDS:
        print(f"\n-- seed {seed} --", flush=True)
        r_without = run_routing_cost(seed, ORIGINAL_ATTACK_RISK_WEIGHT, "WITHOUT recal")
        print(f"  WITHOUT recalibration: {r_without}", flush=True)
        r_with = run_routing_cost(seed, CURRENT_ATTACK_RISK_WEIGHT, "WITH recal")
        print(f"  WITH recalibration:    {r_with}", flush=True)
        rc_without.append(r_without)
        rc_with.append(r_with)

    summary = {
        "quick_mode": _args.quick,
        "seeds_used": SEEDS,
        "num_rounds": NUM_ROUNDS,
        "section_viii_digital_twin": {
            "without_recalibration": {
                "avg_pdr_pct": mean_std([r["avg_pdr_pct"] for r in dt_without]),
                "avg_compromised_routes_pct": mean_std([r["avg_compromised_routes_pct"] for r in dt_without]),
                "detection_accuracy_pct": mean_std([r["detection_accuracy_pct"] for r in dt_without]),
                "detection_recall_pct": mean_std([r["detection_recall_pct"] for r in dt_without]),
            },
            "with_recalibration": {
                "avg_pdr_pct": mean_std([r["avg_pdr_pct"] for r in dt_with]),
                "avg_compromised_routes_pct": mean_std([r["avg_compromised_routes_pct"] for r in dt_with]),
                "detection_accuracy_pct": mean_std([r["detection_accuracy_pct"] for r in dt_with]),
                "detection_recall_pct": mean_std([r["detection_recall_pct"] for r in dt_with]),
            },
        },
        "section_vi_routing_cost": {
            "without_recalibration": {
                "pct_compromised_routes": mean_std([r["pct_compromised_routes"] for r in rc_without]),
                "avg_hop_count": mean_std([r["avg_hop_count"] for r in rc_without]),
            },
            "with_recalibration": {
                "pct_compromised_routes": mean_std([r["pct_compromised_routes"] for r in rc_with]),
                "avg_hop_count": mean_std([r["avg_hop_count"] for r in rc_with]),
            },
        },
    }

    os.makedirs("outputs", exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "=" * 70)
    print(f"Wrote {OUTPUT_PATH}")
    print("=" * 70)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()