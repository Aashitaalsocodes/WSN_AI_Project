"""
check_energy_format.py
Quick diagnostic: does our simulation output already have per-node energy?
"""
import json
from pathlib import Path

OUTPUT_DIR = Path("outputs")
SEEDS = [42, 7, 99, 123, 2024]

for seed in SEEDS:
    json_path = OUTPUT_DIR / f"digital_twin_results_packetmodel_seed{seed}.json"
    if not json_path.exists():
        print(f"seed {seed}: FILE NOT FOUND at {json_path}")
        continue

    with open(json_path, 'r') as f:
        data = json.load(f)

    if 'rounds' not in data or len(data['rounds']) == 0:
        print(f"seed {seed}: no 'rounds' key found — top-level keys: {list(data.keys())}")
        continue

    first_round = data['rounds'][0]
    print(f"\nseed {seed}: {len(data['rounds'])} rounds")
    print(f"  keys in each round entry: {list(first_round.keys())}")
    if 'node_energy_snapshot' in first_round:
        n_nodes = len(first_round['node_energy_snapshot'])
        print(f"  ✅ node_energy_snapshot present, {n_nodes} nodes")
    else:
        print(f"  ❌ no per-node energy — only avg_energy_remaining: {first_round.get('avg_energy_remaining', 'MISSING')}")