"""
patch_routing_cost_only.py
Finishes patching routing_cost.py only (the other 6 files are untouched
and still need the original patch_multiseed_routing.py run for them).
Uses a multi-line anchor so the docstring's mention of random.seed(42)
on line 16 is never matched -- only the real code.
"""

ARGPARSE_HEADER = '''import argparse
_parser = argparse.ArgumentParser()
_parser.add_argument("--seed", type=int, default=42)
_args, _ = _parser.parse_known_args()
SEED = _args.seed
'''

path = "routing_cost.py"
with open(path, "r", encoding="utf-8") as f:
    src = f.read()
original = src

edits = [
    ("import random", "import random\n" + ARGPARSE_HEADER, "insert argparse header"),
    (
        "    random.seed(42)\n    sampled_ids = random.sample(all_ids, 500)",
        "    random.seed(SEED)\n    sampled_ids = random.sample(all_ids, 500)",
        "reconstruct_positions seed (unique 2-line anchor)",
    ),
    ('SIM_PATH = OUTPUTS / "routing_simulation.json"',
     'SIM_PATH = OUTPUTS / f"routing_simulation_seed{SEED}.json"', "read path"),
    ('RESULT_PATH = OUTPUTS / "routing_cost_results.json"',
     'RESULT_PATH = OUTPUTS / f"routing_cost_results_seed{SEED}.json"', "write path"),
]

for old, new, label in edits:
    assert old in src, f"NOT FOUND: {label}\n---\n{old}\n---"
    assert src.count(old) == 1, f"NOT UNIQUE ({src.count(old)}x): {label}"
    src = src.replace(old, new, 1)
    assert new in src, f"EDIT DID NOT APPLY: {label}"

assert src != original, "no changes were made"
with open(path, "w", encoding="utf-8") as f:
    f.write(src)
print("OK  patched routing_cost.py (4 edits)")