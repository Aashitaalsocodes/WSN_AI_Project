import json
import matplotlib.pyplot as plt
import numpy as np
from collections import defaultdict

with open("outputs/synthetic_trust_routing_grid_results.json") as f:
    data = json.load(f)

results = data["results"]

by_nodes = defaultdict(lambda: {"trust": [], "baseline": []})
by_malicious = defaultdict(lambda: {"trust": [], "baseline": []})
by_dist = defaultdict(lambda: {"trust": [], "baseline": []})

for r in results:
    by_nodes[r["num_nodes"]]["trust"].append(r["trust_aware_compromised_pct_mean"])
    by_nodes[r["num_nodes"]]["baseline"].append(r["baseline_compromised_pct_mean"])
    by_malicious[r["malicious_pct"]]["trust"].append(r["trust_aware_compromised_pct_mean"])
    by_malicious[r["malicious_pct"]]["baseline"].append(r["baseline_compromised_pct_mean"])
    by_dist[r["distribution"]]["trust"].append(r["trust_aware_compromised_pct_mean"])
    by_dist[r["distribution"]]["baseline"].append(r["baseline_compromised_pct_mean"])

# Chart 1 — By Node Count
nodes = sorted(by_nodes.keys())
trust_vals = [np.mean(by_nodes[n]["trust"]) for n in nodes]
base_vals = [np.mean(by_nodes[n]["baseline"]) for n in nodes]

plt.figure(figsize=(7, 4))
plt.plot(nodes, trust_vals, "b-o", label="TA-DT (ours)")
plt.plot(nodes, base_vals, "r-o", label="Baseline")
plt.xlabel("Number of Nodes")
plt.ylabel("Compromised Routes (%)")
plt.title("Compromised Routes vs Network Size")
plt.legend()
plt.tight_layout()
plt.savefig("outputs/chart1_node_count.png", dpi=150)
plt.close()
print("Chart 1 saved")

# Chart 2 — By Malicious %
mal_pcts = sorted(by_malicious.keys())
trust_vals2 = [np.mean(by_malicious[m]["trust"]) for m in mal_pcts]
base_vals2 = [np.mean(by_malicious[m]["baseline"]) for m in mal_pcts]

plt.figure(figsize=(7, 4))
plt.plot([m*100 for m in mal_pcts], trust_vals2, "b-o", label="TA-DT (ours)")
plt.plot([m*100 for m in mal_pcts], base_vals2, "r-o", label="Baseline")
plt.xlabel("Malicious Nodes (%)")
plt.ylabel("Compromised Routes (%)")
plt.title("Compromised Routes vs Attacker Percentage")
plt.legend()
plt.tight_layout()
plt.savefig("outputs/chart2_malicious_pct.png", dpi=150)
plt.close()
print("Chart 2 saved")

# Chart 3 — By Distribution
labels = ["Random", "Clustered"]
keys = ["random", "clustered"]
trust_vals3 = [np.mean(by_dist[k]["trust"]) for k in keys]
base_vals3 = [np.mean(by_dist[k]["baseline"]) for k in keys]

x = np.arange(len(labels))
width = 0.35
plt.figure(figsize=(6, 4))
plt.bar(x - width/2, trust_vals3, width, label="TA-DT (ours)", color="blue")
plt.bar(x + width/2, base_vals3, width, label="Baseline", color="red")
plt.xticks(x, labels)
plt.ylabel("Compromised Routes (%)")
plt.title("Compromised Routes by Attacker Distribution")
plt.legend()
plt.tight_layout()
plt.savefig("outputs/chart3_distribution.png", dpi=150)
plt.close()
print("Chart 3 saved")

print("All 3 charts saved to outputs/")
