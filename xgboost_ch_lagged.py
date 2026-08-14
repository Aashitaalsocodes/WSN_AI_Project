"""
CH-prediction, fixed properly this time.

Root cause of every leaky attempt so far: every candidate feature (packets_sent,
ADV_S/DATA_R/etc., and now Expaned Energy) reflects what a node did DURING the
round it's being labeled for -- which is downstream of already being CH, not
predictive of becoming CH.

The fix: use each node's energy state going INTO a round (i.e. its cumulative
Expaned Energy as of the END of the PREVIOUS round), to predict THIS round's
Is_CH label. This is exactly the kind of information LEACH-style probabilistic
CH selection is actually based on (residual energy), and it is structurally
impossible for it to leak this round's activity, because it is fixed before
this round starts.

Requires the raw WSN-DS_with_faults.csv (has 'id' = node id, 'Time' = round).
"""
import pandas as pd
import numpy as np
from sklearn.model_selection import GroupKFold
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
import xgboost as xgb

df = pd.read_csv('data/raw/WSN-DS_with_faults.csv')
df.columns = df.columns.str.strip()
df = df.rename(columns={'Is_CH': 'is_cluster_head'})

# Sort by node then round so lag features are computed correctly per node.
df = df.sort_values(['id', 'Time']).reset_index(drop=True)

# --- Build genuinely pre-selection features (lagged by 1 round, per node) ---
grp = df.groupby('id')

# Energy already expended as of the END of last round (i.e. BEFORE this
# round's CH decision). This is the core fix.
df['prior_expended_energy'] = grp['Expaned Energy'].shift(1)

# Rate of energy use over the last couple of rounds (slope), also lagged --
# uses only data from rounds strictly before the current one.
df['prior_energy_decay_rate'] = grp['Expaned Energy'].diff().shift(1)

# Rolling average of expended energy over the last 3 rounds, lagged so the
# current round is excluded.
df['prior_rolling_energy_avg'] = (
    grp['Expaned Energy'].shift(1).rolling(3, min_periods=1).mean()
)

# How many rounds this node has been alive/observed so far -- legitimate,
# known before the round starts, and plausibly relevant (older nodes have
# accumulated more wear).
df['prior_round_count'] = grp.cumcount()

SAFE_FEATURES = [
    'prior_expended_energy',
    'prior_energy_decay_rate',
    'prior_rolling_energy_avg',
    'prior_round_count',
]

# Drop the first round per node (no prior history exists yet -- NaN lag).
clean = df.dropna(subset=SAFE_FEATURES).copy()
print(f"Rows before dropping first-round-per-node: {len(df)}")
print(f"Rows after (usable rows with real history): {len(clean)}")
print(f"CH rate in usable rows: {clean['is_cluster_head'].mean():.4f}")
print()

X = clean[SAFE_FEATURES]
y = clean['is_cluster_head']
groups = clean['Time']  # group by round, so folds never share a round

gkf = GroupKFold(n_splits=5)
accs, f1s, aucs = [], [], []

for train_idx, test_idx in gkf.split(X, y, groups):
    X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
    y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

    model = xgb.XGBClassifier(eval_metric='logloss', random_state=42)
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    proba = model.predict_proba(X_test)[:, 1]

    accs.append(accuracy_score(y_test, preds))
    f1s.append(f1_score(y_test, preds, zero_division=0))
    aucs.append(roc_auc_score(y_test, proba))

print(f"Accuracy: {np.mean(accs):.4f} +/- {np.std(accs):.4f}")
print(f"F1:       {np.mean(f1s):.4f} +/- {np.std(f1s):.4f}")
print(f"ROC-AUC:  {np.mean(aucs):.4f} +/- {np.std(aucs):.4f}")

# Feature importance -- sanity check. If one feature totally dominates again
# (>80-90%), re-examine it the same way "Expaned Energy" was examined.
final_model = xgb.XGBClassifier(eval_metric='logloss', random_state=42)
final_model.fit(X, y)
importances = pd.Series(final_model.feature_importances_, index=SAFE_FEATURES)
print("\nFeature importances:")
print(importances.sort_values(ascending=False))

# Extra sanity check: confirm these lagged features do NOT correlate with
# same-round role/traffic fields (they shouldn't, by construction, but worth
# a real check rather than assuming).
role_cols = ['ADV_S', 'ADV_R', 'JOIN_S', 'JOIN_R', 'SCH_S', 'SCH_R',
             'DATA_S', 'DATA_R', 'Data_Sent_To_BS']
print("\nSanity check -- correlation of prior_expended_energy with THIS")
print("round's role/traffic fields (should be small, well under the ~0.4-0.5")
print("seen for same-round Expaned Energy):")
for rc in role_cols:
    if rc in clean.columns:
        corr = clean['prior_expended_energy'].corr(
            pd.to_numeric(clean[rc], errors='coerce'))
        print(f"  corr(prior_expended_energy, {rc}) = {corr:.3f}")