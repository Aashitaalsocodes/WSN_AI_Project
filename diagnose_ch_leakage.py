"""
Diagnostic: does Expended_Energy (or any candidate feature) leak cluster-head
role, the same way packets_sent did?

Run this from the repo root (where data/raw/WSN-DS_with_faults.csv and
src/data_pipeline.py live).

Core test: WSN-DS is organized in per-round records. If Expended_Energy is
truly a PRE-SELECTION signal (residual energy state before the round's CH
vote), its distribution for is_cluster_head=1 nodes should NOT be
systematically different from is_cluster_head=0 nodes in a way that mirrors
CH workload -- it should just be residual battery state, same shape as e.g.
Energy_Remaining.

If Expended_Energy is actually CUMULATIVE energy consumed (i.e. monotonically
increases as a node performs its role, including CH duties within the round),
it will show a large, consistent gap between CH and non-CH nodes, and that
gap should scale with round-of-simulation / cluster size -- i.e. it is a
downstream consequence of CH status, not a predictor of it.
"""
import pandas as pd
import numpy as np

df = pd.read_csv('data/raw/WSN-DS_with_faults.csv')  # adjust path if needed

# This CSV has leading/trailing whitespace in most column names (e.g.
# " Is_CH", " ADV_S") -- strip them so the rest of the script can refer to
# clean names.
df.columns = df.columns.str.strip()

print("ALL columns in this CSV:", list(df.columns))
print()
print("Energy-related columns:", [c for c in df.columns if 'nergy' in c.lower()])
print()
if 'is_cluster_head' not in df.columns:
    # The real label column in this dataset is "Is_CH" (0/1), not
    # "is_cluster_head" -- alias it so the rest of the script works
    # unchanged.
    if 'Is_CH' in df.columns:
        df['is_cluster_head'] = df['Is_CH']
        print("Using 'Is_CH' column as is_cluster_head label.")
    else:
        print("WARNING: no CH label column found. CH-related columns:",
              [c for c in df.columns if 'cluster' in c.lower() or 'ch' in c.lower()])
        raise SystemExit(1)
print()

# NOTE: the raw WSN-DS CSV has a typo in this column name -- it's actually
# "Expaned Energy" (missing the 'd'), not "Expended Energy" as the paper
# text calls it. Checking both spellings just in case a cleaned copy exists.
# 1. Basic leakage smell test: does Expaned Energy separate CH from non-CH
#    almost perfectly? A genuine pre-selection feature should NOT separate
#    classes anywhere near this cleanly on its own.
for col in ['Expaned Energy', 'Expended Energy', 'Expended_Energy']:
    if col in df.columns:
        ch = df[df['is_cluster_head'] == 1][col]
        non_ch = df[df['is_cluster_head'] == 0][col]
        print(f"--- {col} ---")
        print(f"CH mean={ch.mean():.4f} std={ch.std():.4f}")
        print(f"non-CH mean={non_ch.mean():.4f} std={non_ch.std():.4f}")
        # Effect size: Cohen's d. Values > ~1.5-2 for a single feature are a
        # strong leakage smell -- real "predisposition" signals are rarely
        # this cleanly separated.
        pooled_std = np.sqrt((ch.std()**2 + non_ch.std()**2) / 2)
        cohens_d = (ch.mean() - non_ch.mean()) / pooled_std
        print(f"Cohen's d (CH vs non-CH): {cohens_d:.2f}")
        print()

# 2. Direct test: is Expended_Energy monotonically tied to round progression
#    or to whether packets were sent this round? If Expended_Energy jumps
#    specifically in the SAME round a node acts as CH (rather than reflecting
#    energy state BEFORE that round's CH assignment), it's leakage.
#    Check correlation with same-row packet/role fields.
role_cols = ['ADV_S', 'ADV_R', 'JOIN_S', 'JOIN_R', 'SCH_S', 'SCH_R',
             'DATA_S', 'DATA_R', 'Data_Sent_To_BS', 'dist_CH_To_BS',
             'Dist_To_CH', 'who CH', 'Rank']
present = [c for c in role_cols if c in df.columns]
for col in ['Expaned Energy', 'Expended Energy', 'Expended_Energy']:
    if col in df.columns:
        print(f"--- correlation of {col} with same-row role/traffic fields ---")
        for rc in present:
            try:
                corr = df[col].corr(pd.to_numeric(df[rc], errors='coerce'))
                print(f"  corr({col}, {rc}) = {corr:.3f}")
            except Exception as e:
                print(f"  corr({col}, {rc}) = skipped ({e})")
        print()

# 3. The real fix: check if the raw dataset has a field representing energy
#    state measured BEFORE this round's CH decision (e.g. residual/initial
#    energy at start of round), separate from cumulative/expended energy
#    which necessarily includes this round's CH workload if selected.
print("All energy-related columns for manual inspection:")
print([c for c in df.columns if 'energy' in c.lower() or 'Energy' in c])