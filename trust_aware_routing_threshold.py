"""
trust_aware_routing_threshold.py

Mitigation 5: Clustering-Aware Trust THRESHOLD Adaptation.

Distinct from the density-weighted edge PENALTY in trust_aware_routing.py's
route_with_trust_clustering_aware(), which only reroutes around already-
excluded nodes. This module instead adapts the trust EXCLUSION THRESHOLD
itself, using spatial density computed from ALL node positions (not just
already-excluded nodes) -- so it can catch undetected attackers with trust
scores in the 0.25-0.4 band that a fixed 0.4 threshold lets through.

Does not modify trust_aware_routing.py in any way. Import both modules
side by side.
"""

import math
import networkx as nx


def compute_spatial_density_from_positions(node_ids, positions, radius):
    """
    Physical node density for every node, from (x, y) positions --
    NOT from excluded/flagged status.

    node_ids: list of node ids
    positions: dict {node_id: (x, y)}
    radius: communication/neighbor radius (same scale as positions)

    Returns: {node_id: density} where density = neighbor_count / area
    """
    density = {}
    node_list = list(node_ids)
    area = math.pi * (radius ** 2)

    for a in node_list:
        ax, ay = positions[a]
        count = 0
        for b in node_list:
            if a == b:
                continue
            bx, by = positions[b]
            if math.hypot(ax - bx, ay - by) <= radius:
                count += 1
        density[a] = count / area if area > 0 else 0.0

    return density


def compute_density_percentile_breakpoints(density_map, low_pct=30, high_pct=70):
    """
    Converts raw density values into percentile-based breakpoints for a
    specific topology, so dens_low/dens_high aren't hardcoded absolute
    numbers that may not match this graph's density scale.

    Run once per topology; feed results into adaptive_trust_threshold's
    dens_low/dens_high.
    """
    values = sorted(density_map.values())
    if not values:
        return 0.0, 0.0

    def percentile(vals, pct):
        k = (len(vals) - 1) * (pct / 100)
        f = int(k)
        c = min(f + 1, len(vals) - 1)
        if f == c:
            return vals[f]
        return vals[f] + (vals[c] - vals[f]) * (k - f)

    return percentile(values, low_pct), percentile(values, high_pct)


def adaptive_trust_threshold(
    density,
    dens_low=0.3,
    dens_high=0.7,
    thresh_high=0.5,
    thresh_mid=0.35,
    thresh_low=0.25,
):
    """
    Maps local spatial density to a trust exclusion threshold.
    Sparse regions keep the normal threshold (0.5); dense regions
    (likely attacker clusters/chokepoints) get a stricter threshold
    (0.25), catching undetected attackers with trust in the 0.25-0.4
    band that a fixed 0.4 threshold would let through.
    """
    if density < dens_low:
        return thresh_high
    elif density > dens_high:
        return thresh_low
    else:
        return thresh_mid


def build_excluded_with_adaptive_trust(
    node_ids,
    classifier,
    trust_scores,
    density_map,
    dens_low=0.3,
    dens_high=0.7,
    thresh_high=0.5,
    thresh_mid=0.35,
    thresh_low=0.25,
):
    """
    Threshold-adaptive replacement for get_excluded_nodes(). Same
    classifier-flag exclusion, but the trust cutoff depends on local
    spatial density instead of being a fixed constant.

    Returns: (excluded_set, threshold_used_dict)
    """
    excluded = set()
    threshold_used = {}

    for nid in node_ids:
        pred = classifier.get(nid, {})
        if pred.get("predicted_attacked", 0) == 1:
            excluded.add(nid)
            threshold_used[nid] = None  # excluded via classifier, not trust
            continue

        density = density_map.get(nid, 0.0)
        threshold = adaptive_trust_threshold(
            density,
            dens_low=dens_low,
            dens_high=dens_high,
            thresh_high=thresh_high,
            thresh_mid=thresh_mid,
            thresh_low=thresh_low,
        )
        threshold_used[nid] = threshold

        ts = trust_scores.get(int(nid), trust_scores.get(nid, 1.0))
        if ts < threshold:
            excluded.add(nid)

    return excluded, threshold_used


def route_with_trust_threshold_adaptive(G, source, destination, excluded_adaptive, classifier):
    """
    Routing using the threshold-adaptively-excluded node set. Plain
    shortest_path on the pruned graph -- no edge-weight penalty (that's
    the other mitigation, untouched in trust_aware_routing.py). Falls
    back to baseline if no path exists.
    """
    nodes_to_remove = excluded_adaptive - {source, destination}
    G_trusted = G.copy()
    G_trusted.remove_nodes_from(nodes_to_remove)

    try:
        path = nx.shortest_path(G_trusted, source=source, target=destination)
        attacked_in_path = [
            n for n in path
            if classifier.get(n, {}).get("predicted_attacked", 0) == 1
            and n not in (source, destination)
        ]
        return {
            "path": path,
            "hop_count": len(path) - 1,
            "passes_through_attacked_node": len(attacked_in_path) > 0,
            "attacked_nodes_in_path": attacked_in_path,
            "routing_mode": "trust_threshold_adaptive",
            "path_found": True,
        }
    except nx.NetworkXNoPath:
        try:
            path = nx.shortest_path(G, source=source, target=destination)
            attacked_in_path = [
                n for n in path
                if classifier.get(n, {}).get("predicted_attacked", 0) == 1
            ]
            return {
                "path": path,
                "hop_count": len(path) - 1,
                "passes_through_attacked_node": len(attacked_in_path) > 0,
                "attacked_nodes_in_path": attacked_in_path,
                "routing_mode": "fallback_no_trusted_path_adaptive",
                "path_found": True,
            }
        except nx.NetworkXNoPath:
            return {
                "path": [],
                "hop_count": -1,
                "passes_through_attacked_node": False,
                "attacked_nodes_in_path": [],
                "routing_mode": "no_path",
                "path_found": False,
            }