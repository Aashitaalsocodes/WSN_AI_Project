"""
Figure 12 regeneration script — WSN AI Security Pipeline
Reads: outputs/digital_twin_results.json
Writes: outputs/figure12.png

Matches the 23-round simulation data now in Conference_paper_v27.docx.
"""

import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
import os

# ── Load data ────────────────────────────────────────────────────────────────
DATA_PATH = os.path.join("outputs", "digital_twin_results.json")
OUT_PATH  = os.path.join("outputs", "figure12.png")

with open(DATA_PATH, "r") as f:
    data = json.load(f)

rounds = data["rounds"]

x                   = [r["round"]                   for r in rounds]
compromised_pct     = [r["compromised_routes_pct"]  for r in rounds]
avg_trust           = [r["avg_trust_score"]          for r in rounds]
avg_energy          = [r["avg_energy_remaining"]     for r in rounds]
num_dead            = [r["num_dead_nodes"]           for r in rounds]
excluded_count      = [r["excluded_node_count"]      for r in rounds]
missed_count        = [len(r["missed_detections"])   for r in rounds]

# ── Style ─────────────────────────────────────────────────────────────────────
COLORS = {
    "compromised": "#D62728",   # red
    "trust":       "#1F77B4",   # blue
    "energy":      "#2CA02C",   # green
    "dead":        "#9467BD",   # purple
    "excluded":    "#FF7F0E",   # orange
    "missed":      "#8C564B",   # brown
}

plt.rcParams.update({
    "font.family":   "serif",
    "font.size":     10,
    "axes.titlesize": 11,
    "axes.labelsize": 10,
    "legend.fontsize": 9,
    "figure.dpi":    150,
})

# ── Layout: 2×2 subplots ─────────────────────────────────────────────────────
fig = plt.figure(figsize=(12, 8))
gs  = gridspec.GridSpec(2, 2, figure=fig, hspace=0.42, wspace=0.32)

ax1 = fig.add_subplot(gs[0, 0])
ax2 = fig.add_subplot(gs[0, 1])
ax3 = fig.add_subplot(gs[1, 0])
ax4 = fig.add_subplot(gs[1, 1])

# ── (a) Compromised Routes % ─────────────────────────────────────────────────
ax1.plot(x, compromised_pct, color=COLORS["compromised"], linewidth=1.8,
         marker="o", markersize=3.5, label="Compromised routes %")
ax1.fill_between(x, compromised_pct, alpha=0.12, color=COLORS["compromised"])
ax1.axhline(np.mean(compromised_pct), color=COLORS["compromised"],
            linewidth=0.9, linestyle="--", alpha=0.7,
            label=f"Mean = {np.mean(compromised_pct):.2f}%")
ax1.set_title("(a) Compromised Routes per Round")
ax1.set_xlabel("Round")
ax1.set_ylabel("Compromised Routes (%)")
ax1.set_xlim(0, 22)
ax1.legend(loc="upper right", framealpha=0.7)
ax1.grid(True, linestyle=":", alpha=0.5)

# ── (b) Average Trust Score ───────────────────────────────────────────────────
ax2.plot(x, avg_trust, color=COLORS["trust"], linewidth=1.8,
         marker="s", markersize=3.5, label="Avg trust score")
ax2.fill_between(x, avg_trust, alpha=0.12, color=COLORS["trust"])
ax2.axhline(np.mean(avg_trust), color=COLORS["trust"],
            linewidth=0.9, linestyle="--", alpha=0.7,
            label=f"Mean = {np.mean(avg_trust):.4f}")
ax2.set_title("(b) Average Trust Score per Round")
ax2.set_xlabel("Round")
ax2.set_ylabel("Avg Trust Score")
ax2.set_xlim(0, 22)
ax2.set_ylim(0.70, 0.76)
ax2.legend(loc="lower left", framealpha=0.7)
ax2.grid(True, linestyle=":", alpha=0.5)

# ── (c) Energy Remaining & Dead Nodes (dual axis) ────────────────────────────
ax3b = ax3.twinx()
l1, = ax3.plot(x, avg_energy, color=COLORS["energy"], linewidth=1.8,
               marker="^", markersize=3.5, label="Avg energy remaining")
l2, = ax3b.plot(x, num_dead, color=COLORS["dead"], linewidth=1.8,
                marker="v", markersize=3.5, linestyle="--", label="Dead nodes")
ax3.set_title("(c) Energy Depletion & Node Death")
ax3.set_xlabel("Round")
ax3.set_ylabel("Avg Energy Remaining (fraction)", color=COLORS["energy"])
ax3b.set_ylabel("Dead Nodes (count)", color=COLORS["dead"])
ax3.set_xlim(0, 22)
ax3.tick_params(axis="y", labelcolor=COLORS["energy"])
ax3b.tick_params(axis="y", labelcolor=COLORS["dead"])
lines = [l1, l2]
ax3.legend(lines, [l.get_label() for l in lines], loc="center left",
           framealpha=0.7)
ax3.grid(True, linestyle=":", alpha=0.5)

# Mark FND / HND / LND
fnd = data["energy_summary"]["first_node_death_round"]
hnd = data["energy_summary"]["half_node_death_round"]
lnd = data["energy_summary"]["last_node_death_round"]
for rnd, label, color in [(fnd, "FND", "#555"), (hnd, "HND", "#333"),
                           (lnd, "LND", "#111")]:
    ax3.axvline(rnd, color=color, linestyle=":", linewidth=0.9, alpha=0.6)
    ax3.text(rnd + 0.15, ax3.get_ylim()[1] * 0.92, label,
             fontsize=7, color=color, alpha=0.8)

# ── (d) Detection: Excluded vs Missed per Round ───────────────────────────────
width = 0.4
ax4.bar([xi - width/2 for xi in x], excluded_count, width=width,
        color=COLORS["excluded"], alpha=0.8, label="Excluded (detected)")
ax4.bar([xi + width/2 for xi in x], missed_count, width=width,
        color=COLORS["missed"], alpha=0.8, label="Missed detections")
ax4.set_title("(d) Attack Detection per Round")
ax4.set_xlabel("Round")
ax4.set_ylabel("Node Count")
ax4.set_xlim(-0.8, 22.8)
ax4.legend(loc="upper right", framealpha=0.7)
ax4.grid(True, linestyle=":", alpha=0.5, axis="y")

# ── Overall title & save ──────────────────────────────────────────────────────
fig.suptitle(
    "Figure 12: Digital Twin Simulation Results — 23-Round WSN Security Evaluation\n"
    "(500 nodes, multi-attack scenario: Blackhole / Grayhole / Flooding / TDMA)",
    fontsize=11, y=1.01
)

os.makedirs("outputs", exist_ok=True)
fig.savefig(OUT_PATH, dpi=150, bbox_inches="tight")
print(f"Saved: {OUT_PATH}")

# ── Print summary stats for paper verification ────────────────────────────────
print("\n── Summary stats (for paper cross-check) ──────────────────")
print(f"Rounds simulated:        {len(rounds)}")
print(f"Compromised routes — mean:  {np.mean(compromised_pct):.2f}%  "
      f"max: {max(compromised_pct):.1f}%  min: {min(compromised_pct):.1f}%")
print(f"Avg trust score   — mean:  {np.mean(avg_trust):.4f}  "
      f"min: {min(avg_trust):.4f}  max: {max(avg_trust):.4f}")
print(f"FND round: {fnd}   HND round: {hnd}   LND round: {lnd}")
total_missed   = sum(missed_count)
total_attacked = sum(r["attacked_count"] for r in rounds)
total_excluded = sum(excluded_count)
print(f"Total attacked:  {total_attacked}")
print(f"Total excluded:  {total_excluded}  ({100*total_excluded/total_attacked:.1f}% detection rate)")
print(f"Total missed:    {total_missed}   ({100*total_missed/total_attacked:.1f}% miss rate)")