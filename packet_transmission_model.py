"""
packet_transmission_model.py

Per-packet transmission/loss model, meant to be called once per round from
inside digital_twin_sim_recalibrated.py and each baseline_*.py file, using
the SAME path each already computes (route_with_trust() result / nx path)
-- this does NOT replace routing, it sits downstream of it and asks:
"given this path was chosen, how many packets sent along it actually
arrive?"

This replaces the current packet_delivery_ratio_pct, which is really just
(successful_routes / total_routes) -- i.e. "did a path exist at all,"
which is ~always true on a connected 500-node topology and is why PDR is
flat across every protocol and every round.

Model
-----
Each source/destination pair sends PACKETS_PER_ROUND packets along its
already-computed path. Each packet is walked hop-by-hop; at each
intermediate node it has a probability of being dropped, drawn from:

  - a small baseline drop rate for ANY node (channel noise / collision),
    representative of low-traffic 802.15.4-style WSN links
  - an attack-specific drop probability if that hop is an attacked node,
    calibrated to standard attacker-model behavior (Karlof & Wagner-style):
      blackhole  -> near-total drop
      grayhole   -> selective drop
      tdma       -> collision-based drop
      flooding   -> doesn't drop directly, but raises congestion drop
                    probability at its downstream neighbor
  - only ONE draw per packet per hop, independent across hops (packet
    survives a hop with probability (1 - drop_prob), fails the whole
    transmission if it's dropped at any hop)

Per-hop transit time is also accumulated (transmission + propagation +
queuing delay) so avg_delay and throughput become genuinely measured
quantities instead of hop_count * constant.

Usage (per round, per protocol file):

    from packet_transmission_model import simulate_packet_delivery

    packet_result = simulate_packet_delivery(
        baseline_routes, paths_this_round, attacked_node_types
    )
    # packet_result["pdr_pct"], ["avg_delay_ms"], ["throughput_kbps"]
    # replace the old packet_delivery_ratio_pct / hop-derived delay fields

`paths_this_round` is just {(source, destination): path_list_or_None},
which every protocol file already produces inside its route loop -- no
new routing logic required, this only consumes what's already computed.
"""

import random

# ---------------------------------------------------------------------------
# Calibration constants
# ---------------------------------------------------------------------------

PACKETS_PER_ROUND = 20          # packets sent per source/destination pair
PACKET_SIZE_BITS = 4096         # 512-byte packet, typical WSN payload

# Baseline per-hop drop probability for a NORMAL (non-attacked) node --
# channel noise / collision, not attack behavior.
BASELINE_DROP_PROB = 0.015

# Per-attack-type drop probability when a packet passes through an
# attacked node. These are deliberately distinct from ATTACK_RISK_WEIGHT
# in routing_cost.py (which scores route DESIRABILITY for the router) --
# these instead score actual packet SURVIVAL, so blackhole still doesn't
# hit exactly 1.0 (a "perfect" blackhole is unrealistic and also makes
# the metric degenerate).
ATTACK_DROP_PROB = {
    "blackhole": 0.95,
    "grayhole": 0.40,
    "tdma": 0.15,     # slot collision, not intentional dropping
    "flooding": 0.05, # flooding itself rarely drops the packet directly
}

# Flooding congestion penalty applied to the flooding node's direct
# neighbors on the path (queue buildup from replayed/duplicated traffic),
# on top of whatever their own baseline/attack drop prob already is.
FLOODING_NEIGHBOR_CONGESTION_PENALTY = 0.20

# Timing model (loosely IEEE 802.15.4-ish, not claimed to be exact --
# order-of-magnitude realistic so delay/throughput are non-trivial and
# internally consistent, not just relabeled hop counts).
TX_TIME_MS_PER_HOP = 4.0        # radio transmission time per hop
PROPAGATION_MS_PER_HOP = 0.5    # negligible but non-zero
QUEUING_MS_PER_HOP_BASE = 2.0   # base queuing delay
QUEUING_MS_CONGESTED_EXTRA = 8.0  # extra queuing delay at a congested hop


def _hop_drop_probability(node_id, attacked_node_types, flooding_neighbors):
    """Drop probability for a single hop, given what's attacking it."""
    if node_id in attacked_node_types:
        p = ATTACK_DROP_PROB.get(attacked_node_types[node_id], BASELINE_DROP_PROB)
    else:
        p = BASELINE_DROP_PROB

    if node_id in flooding_neighbors:
        p = min(1.0, p + FLOODING_NEIGHBOR_CONGESTION_PENALTY)

    return p


def _hop_delay_ms(node_id, attacked_node_types, flooding_neighbors):
    """Transit time contribution of a single hop, congestion-aware."""
    congested = node_id in flooding_neighbors or (
        attacked_node_types.get(node_id) == "flooding"
    )
    queuing = QUEUING_MS_PER_HOP_BASE + (
        QUEUING_MS_CONGESTED_EXTRA if congested else 0.0
    )
    return TX_TIME_MS_PER_HOP + PROPAGATION_MS_PER_HOP + queuing


def _flooding_neighbor_set(path, attacked_node_types):
    """Nodes on this path adjacent to a flooding attacker on this path."""
    neighbors = set()
    for i, nid in enumerate(path):
        if attacked_node_types.get(nid) == "flooding":
            if i > 0:
                neighbors.add(path[i - 1])
            if i < len(path) - 1:
                neighbors.add(path[i + 1])
    return neighbors


def simulate_packet_delivery(baseline_routes, paths_this_round, attacked_node_types,
                              packets_per_round=PACKETS_PER_ROUND, rng=random):
    """
    baseline_routes: the same list of {"source":..., "destination":...} dicts
                      every protocol file already iterates over.
    paths_this_round: dict {(source, destination): path_list or None}
                       -- None / missing means no route existed this round
                       (old-style total failure, still counted as 0 delivered).
    attacked_node_types: {node_id: "blackhole"/"grayhole"/"tdma"/"flooding"}
                          for this round (already computed upstream).

    Returns dict with pdr_pct, avg_delay_ms, throughput_kbps, plus raw
    counts so evaluation_metrics.py / the comparison table can aggregate
    across rounds/seeds the same way it does everything else.
    """
    total_sent = 0
    total_delivered = 0
    delay_samples_ms = []

    for route in baseline_routes:
        src, dst = route["source"], route["destination"]
        path = paths_this_round.get((src, dst))

        if not path or len(path) < 2:
            # no route at all this round -> every packet for this pair fails
            total_sent += packets_per_round
            continue

        intermediate_hops = path[1:-1]  # source/dest themselves aren't "dropped"
        flooding_neighbors = _flooding_neighbor_set(path, attacked_node_types)

        for _ in range(packets_per_round):
            total_sent += 1
            delivered = True
            elapsed_ms = 0.0

            for nid in intermediate_hops:
                elapsed_ms += _hop_delay_ms(nid, attacked_node_types, flooding_neighbors)
                drop_p = _hop_drop_probability(nid, attacked_node_types, flooding_neighbors)
                if rng.random() < drop_p:
                    delivered = False
                    break  # packet dies here, doesn't continue further hops

            if delivered:
                # account for the final hop into the destination too
                elapsed_ms += TX_TIME_MS_PER_HOP + PROPAGATION_MS_PER_HOP
                total_delivered += 1
                delay_samples_ms.append(elapsed_ms)

    pdr_pct = round(100 * total_delivered / total_sent, 4) if total_sent else 0.0
    avg_delay_ms = round(sum(delay_samples_ms) / len(delay_samples_ms), 4) if delay_samples_ms else None

    # throughput: successfully delivered bits per second across the round.
    # Treat one round's worth of sends as happening over
    # (packets_per_round * TX_TIME_MS_PER_HOP) ms of channel time as a
    # rough round-duration proxy -- consistent within this model, not
    # claimed to match a specific MAC protocol's real timing.
    round_duration_s = max(
        (packets_per_round * TX_TIME_MS_PER_HOP) / 1000.0, 1e-6
    )
    throughput_kbps = round(
        (total_delivered * PACKET_SIZE_BITS / 1000.0) / round_duration_s, 4
    )

    return {
        "pdr_pct": pdr_pct,
        "avg_delay_ms": avg_delay_ms,
        "throughput_kbps": throughput_kbps,
        "total_packets_sent": total_sent,
        "total_packets_delivered": total_delivered,
    }
