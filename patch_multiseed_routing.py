"""
patch_multiseed_routing.py

Assertion-guarded patch: adds --seed CLI support to the 7 scripts in the
routing/baseline chain so Section VI (200-route test) and Section VIII
(5-protocol comparison) can be re-run across multiple seeds, mirroring the
pattern already used in digital_twin_sim_multiseed.py.

Run from the project root:  python patch_multiseed_routing.py
Each edit is checked before AND after — if any expected string is missing,
the script stops immediately rather than silently skipping that file.
"""
import re

def patch(path, edits):
    with open(path, "r", encoding="utf-8") as f:
        src = f.read()
    original = src
    for old, new, label in edits:
        assert old in src, f"[{path}] NOT FOUND before edit: {label}\n---\n{old}\n---"
        assert src.count(old) == 1, f"[{path}] NOT UNIQUE ({src.count(old)}x): {label}"
        src = src.replace(old, new, 1)
        assert new in src, f"[{path}] EDIT DID NOT APPLY: {label}"
    assert src != original, f"[{path}] no changes were made"
    with open(path, "w", encoding="utf-8") as f:
        f.write(src)
    print(f"OK  patched {path} ({len(edits)} edits)")


ARGPARSE_HEADER = '''import argparse
_parser = argparse.ArgumentParser()
_parser.add_argument("--seed", type=int, default=42)
_args, _ = _parser.parse_known_args()
SEED = _args.seed
'''

# ---------------------------------------------------------------- wsn_routing_sim.py
patch("wsn_routing_sim.py", [
    ("random.seed(42)", "SEED_PLACEHOLDER_REMOVE_ME", "remove old fixed seed (temp marker)"),
])
# second pass: insert argparse block once, then point the placeholder at SEED
with open("wsn_routing_sim.py", encoding="utf-8") as f:
    src = f.read()
assert "import random" in src, "wsn_routing_sim.py: 'import random' not found to anchor header insert"
src = src.replace("import random", "import random\n" + ARGPARSE_HEADER, 1)
src = src.replace("SEED_PLACEHOLDER_REMOVE_ME", "random.seed(SEED)")
src = src.replace(
    "with open('outputs/routing_simulation.json', 'w') as f:",
    "with open(f'outputs/routing_simulation_seed{SEED}.json', 'w') as f:",
)
with open("wsn_routing_sim.py", "w", encoding="utf-8") as f:
    f.write(src)
print("OK  patched wsn_routing_sim.py (seed + output path)")

# ---------------------------------------------------------------- routing_cost.py
patch("routing_cost.py", [
    ("import random", "import random\n" + ARGPARSE_HEADER, "insert argparse header"),
    ("random.seed(42)", "random.seed(SEED)", "reconstruct_positions seed"),
    ('SIM_PATH = OUTPUTS / "routing_simulation.json"',
     'SIM_PATH = OUTPUTS / f"routing_simulation_seed{SEED}.json"', "read path"),
    ('RESULT_PATH = OUTPUTS / "routing_cost_results.json"',
     'RESULT_PATH = OUTPUTS / f"routing_cost_results_seed{SEED}.json"', "write path"),
])

# ---------------------------------------------------------------- baselines (leach/heed/tbr/ai_sr)
for fname, out_stub in [
    ("baseline_leach.py", "baseline_leach_results"),
    ("baseline_heed.py", "baseline_heed_results"),
    ("baseline_tbr.py", "baseline_tbr_results"),
    ("baseline_ai_sr.py", "baseline_ai_sr_results"),
]:
    patch(fname, [
        ("import random", "import random\n" + ARGPARSE_HEADER, "insert argparse header"),
        ("random.seed(42)", "random.seed(SEED)", "baseline seed"),
        (f'OUTPUT_PATH = "outputs/{out_stub}.json"',
         f'OUTPUT_PATH = f"outputs/{out_stub}_seed{{SEED}}.json"', "write path"),
        ('with open("outputs/routing_simulation.json") as f:',
         'with open(f"outputs/routing_simulation_seed{SEED}.json") as f:', "read path"),
    ])

# ---------------------------------------------------------------- trust_aware_routing.py
patch("trust_aware_routing.py", [
    ("import json", "import json\n" + ARGPARSE_HEADER, "insert argparse header"),
    ('with open(OUTPUTS_DIR / "routing_simulation.json", encoding="utf-8") as f:',
     'with open(OUTPUTS_DIR / f"routing_simulation_seed{SEED}.json", encoding="utf-8") as f:',
     "read path"),
    ('output_path = OUTPUTS_DIR / "trust_aware_routing_results.json"',
     'output_path = OUTPUTS_DIR / f"trust_aware_routing_results_seed{SEED}.json"',
     "write path"),
])

print("\nAll 7 files patched successfully.")