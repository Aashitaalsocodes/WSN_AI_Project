"""
run_routing_multiseed.py

Runs the full routing/baseline chain once per seed:
  wsn_routing_sim.py --seed N
  routing_cost.py --seed N
  baseline_leach.py --seed N
  baseline_heed.py --seed N
  baseline_tbr.py --seed N
  baseline_ai_sr.py --seed N
  trust_aware_routing.py --seed N

Seeds match the DT sweep exactly: 42, 7, 123, 2024, 99.
Stops immediately if any stage exits non-zero for any seed -- does not
continue to the next seed on a partial failure, so you never get a
silently incomplete seed's worth of output files.
"""
import subprocess
import sys

SEEDS = [42, 7, 123, 2024, 99]

STAGES = [
    "wsn_routing_sim.py",
    "routing_cost.py",
    "baseline_leach.py",
    "baseline_heed.py",
    "baseline_tbr.py",
    "baseline_ai_sr.py",
    "trust_aware_routing.py",
]

for seed in SEEDS:
    print(f"\n===== SEED {seed} =====")
    for stage in STAGES:
        cmd = [sys.executable, stage, "--seed", str(seed)]
        print(f"  running: {' '.join(cmd)}")
        result = subprocess.run(cmd)
        if result.returncode != 0:
            print(f"\nFAILED at seed={seed}, stage={stage} (exit code {result.returncode})")
            print("Stopping -- fix the error above before re-running.")
            sys.exit(1)
    print(f"  seed {seed} complete.")

print("\nAll 5 seeds completed successfully.")
print("Expected output files per seed (N in", SEEDS, "):")
print("  outputs/routing_simulation_seed{N}.json")
print("  outputs/routing_cost_results_seed{N}.json")
print("  outputs/baseline_leach_results_seed{N}.json")
print("  outputs/baseline_heed_results_seed{N}.json")
print("  outputs/baseline_tbr_results_seed{N}.json")
print("  outputs/baseline_ai_sr_results_seed{N}.json")
print("  outputs/trust_aware_routing_results_seed{N}.json")