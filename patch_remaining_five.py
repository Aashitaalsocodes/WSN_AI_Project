"""
patch_remaining_five.py
Patches the last 5 files: baseline_leach.py, baseline_heed.py,
baseline_tbr.py, baseline_ai_sr.py, trust_aware_routing.py.
wsn_routing_sim.py and routing_cost.py are already done -- do not re-run
patch_multiseed_routing.py, it will fail on those two now.
"""

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

patch("trust_aware_routing.py", [
    ("import json", "import json\n" + ARGPARSE_HEADER, "insert argparse header"),
    ('with open(OUTPUTS_DIR / "routing_simulation.json", encoding="utf-8") as f:',
     'with open(OUTPUTS_DIR / f"routing_simulation_seed{SEED}.json", encoding="utf-8") as f:',
     "read path"),
    ('output_path = OUTPUTS_DIR / "trust_aware_routing_results.json"',
     'output_path = OUTPUTS_DIR / f"trust_aware_routing_results_seed{SEED}.json"',
     "write path"),
])

print("\nAll 5 remaining files patched successfully.")