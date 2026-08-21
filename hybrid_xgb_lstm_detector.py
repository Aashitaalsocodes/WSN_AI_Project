"""
hybrid_xgb_lstm_detector.py

Priority 4: Hybrid XGBoost + LSTM attack detection for the WSN AI Security
Pipeline. Combines the existing XGBoost multiclass classifier (static,
per-record features) with an LSTM (temporal, per-node sequence patterns)
via a weighted ensemble, then reports recall on the held-out test set so
you can compare directly against the paper's 92-93% per-round recall figure.

USAGE (from C:\\Users\\Admin\\WSN_AI_Project, inside your venv):
    python hybrid_xgb_lstm_detector.py --csv path\\to\\WSN-DS.csv

This script does NOT touch any existing files. It is read-only w.r.t. your
pipeline (loads your saved XGBoost model if present, otherwise retrains one
using the exact hyperparameters from the paper so results stay comparable).
It writes its own outputs to ./hybrid_xgb_lstm_outputs/ so nothing collides
with your existing artifacts. Nothing here overwrites paper text -- verify
the printed metrics, then update the paper by hand (or ask me to do it once
you have real numbers).

Assumptions (ASSERT-checked, will fail loudly rather than silently guess):
  - Dataset is WSN-DS with 19 features + 'Attack_type' label column.
  - There is some column that identifies which node produced each row
    (commonly 'who_CH' or a node index). If none of the auto-detected
    candidates match your CSV, pass --node-col explicitly.
  - There is a round/time column (commonly 'Time' in WSN-DS) to sort rows
    chronologically per node before windowing.

If your local column names differ, run:
    python -c "import pandas as pd; print(pd.read_csv('WSN-DS.csv', nrows=5).columns.tolist())"
and pass --node-col / --time-col accordingly.
"""

import argparse
import json
import os
import pickle
import sys

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import recall_score, precision_score, f1_score, accuracy_score, classification_report
from sklearn.preprocessing import LabelEncoder, StandardScaler

try:
    import xgboost as xgb
except ImportError:
    sys.exit("xgboost not installed. Run: pip install xgboost")

try:
    import torch
    import torch.nn as nn
    from torch.utils.data import Dataset, DataLoader
except ImportError:
    sys.exit("torch not installed. Run: pip install torch")


OUT_DIR = "hybrid_xgb_lstm_outputs"
SEQ_LEN = 10          # rounds of history per sequence -- tune if recall is poor
XGB_WEIGHT = 0.6       # from your Priority-4 spec; treat as a starting point, not gospel
LSTM_WEIGHT = 0.4
RANDOM_STATE = 42

NODE_COL_CANDIDATES = ["id", "who_CH", "who CH", "node_id", "Node_ID", "NodeID"]
TIME_COL_CANDIDATES = ["Time", "time", "Round", "round"]
LABEL_COL_CANDIDATES = ["Attack_type", "Attack type", "attack_type", "attack type"]


def detect_column(df, candidates, label):
    for c in candidates:
        if c in df.columns:
            return c
    raise AssertionError(
        f"Could not auto-detect {label} column among {candidates}. "
        f"Available columns: {df.columns.tolist()}. Pass --{'node-col' if label=='node' else 'time-col'} explicitly."
    )


def load_dataset(csv_path, node_col, time_col):
    df = pd.read_csv(csv_path)
    df.columns = df.columns.str.strip()  # WSN-DS ships with stray leading/trailing spaces in headers
    for col in df.select_dtypes(include=["object", "string"]).columns:
        df[col] = df[col].astype(str).str.strip()

    label_col = next((c for c in LABEL_COL_CANDIDATES if c in df.columns), None)
    assert label_col is not None, (
        f"Could not find a label column among {LABEL_COL_CANDIDATES}. "
        f"Available columns: {df.columns.tolist()}"
    )
    if label_col != "Attack_type":
        df = df.rename(columns={label_col: "Attack_type"})

    # Columns that are numeric but got parsed as object dtype (common with stray
    # spaces in the raw values, e.g. ' send_code ') need coercing back, or
    # get_feature_columns will silently drop them from the feature set.
    for col in df.columns:
        if col == "Attack_type":
            continue
        if df[col].dtype == object:
            coerced = pd.to_numeric(df[col], errors="coerce")
            if coerced.notna().mean() > 0.95:  # genuinely numeric, not a real text column
                df[col] = coerced

    if node_col is None:
        node_col = detect_column(df, NODE_COL_CANDIDATES, "node")
    if time_col is None:
        time_col = detect_column(df, TIME_COL_CANDIDATES, "time")
    assert node_col in df.columns, f"--node-col '{node_col}' not in dataframe. Columns: {df.columns.tolist()}"
    assert time_col in df.columns, f"--time-col '{time_col}' not in dataframe. Columns: {df.columns.tolist()}"
    print(f"[load] {len(df)} rows, node_col='{node_col}', time_col='{time_col}', label_col='{label_col}'")
    return df, node_col, time_col


def get_feature_columns(df, node_col, time_col):
    drop_cols = {"Attack_type", node_col, time_col}
    feat_cols = [c for c in df.columns if c not in drop_cols and pd.api.types.is_numeric_dtype(df[c])]
    assert len(feat_cols) > 0, "No numeric feature columns found after dropping label/node/time."
    return feat_cols


def prep_static_features(df, feat_cols):
    X = df[feat_cols].copy()
    if "drop_ratio" in X.columns:
        X["drop_ratio"] = X["drop_ratio"].fillna(0.0).clip(0.0, 1.0)
    X = X.fillna(0.0)
    return X


def train_or_load_xgb(X_train, y_train, model_path):
    if os.path.exists(model_path):
        print(f"[xgb] loading existing model from {model_path}")
        with open(model_path, "rb") as f:
            return pickle.load(f)
    print("[xgb] no saved model found -- training fresh with paper hyperparameters")
    classes, counts = np.unique(y_train, return_counts=True)
    n_classes = len(classes)
    total = len(y_train)
    class_weight = {c: total / (n_classes * cnt) for c, cnt in zip(classes, counts)}
    sample_weight = np.array([class_weight[y] for y in y_train])

    model = xgb.XGBClassifier(
        n_estimators=300, max_depth=7, learning_rate=0.08,
        random_state=RANDOM_STATE, eval_metric="mlogloss",
    )
    model.fit(X_train, y_train, sample_weight=sample_weight)
    with open(model_path, "wb") as f:
        pickle.dump(model, f)
    return model


class SequenceDataset(Dataset):
    def __init__(self, sequences, labels):
        self.sequences = sequences  # (N, seq_len, n_features)
        self.labels = labels

    def __len__(self):
        return len(self.sequences)

    def __getitem__(self, idx):
        return (
            torch.tensor(self.sequences[idx], dtype=torch.float32),
            torch.tensor(self.labels[idx], dtype=torch.long),
        )


class LSTMDetector(nn.Module):
    def __init__(self, n_features, n_classes, hidden_size=64, num_layers=2, dropout=0.3):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=n_features, hidden_size=hidden_size, num_layers=num_layers,
            batch_first=True, dropout=dropout if num_layers > 1 else 0.0,
        )
        self.head = nn.Sequential(
            nn.Linear(hidden_size, 32), nn.ReLU(), nn.Dropout(dropout),
            nn.Linear(32, n_classes),
        )

    def forward(self, x):
        out, (h_n, _) = self.lstm(x)
        last_hidden = h_n[-1]
        return self.head(last_hidden)


def make_split(df, node_col, time_col, y_encoded, mode, time_frac, node_frac, seed):
    """Leak-safe split. Returns a boolean 'is_train' Series aligned to df.index.

    mode='time'  : global round threshold -- ALL nodes present in both train
                   and test, split at the time_frac-th percentile of the time
                   column. This is the safer default: it mirrors real
                   deployment (train on past rounds, detect on future rounds)
                   and matches how the paper already frames per-round
                   detection.
    mode='node'  : entire nodes held out -- tests generalisation to unseen
                   devices. Splits node IDs, not rows or time.
    Either way, sequences are built AFTER this split and only from rows
    inside a single partition, so no window can span the train/test
    boundary and no window is built from a mix of both.
    """
    if mode == "time":
        threshold = df[time_col].quantile(time_frac)
        is_train = df[time_col] <= threshold
        print(f"[split] mode=time, threshold(round)={threshold}, "
              f"train_rows={is_train.sum()}, test_rows={(~is_train).sum()}")
    elif mode == "node":
        rng = np.random.RandomState(seed)
        nodes = df[node_col].unique()
        rng.shuffle(nodes)
        n_train_nodes = int(len(nodes) * node_frac)
        train_nodes = set(nodes[:n_train_nodes])
        is_train = df[node_col].isin(train_nodes)
        print(f"[split] mode=node, train_nodes={n_train_nodes}/{len(nodes)}, "
              f"train_rows={is_train.sum()}, test_rows={(~is_train).sum()}")
    else:
        raise AssertionError(f"Unknown --split-mode '{mode}', expected 'time' or 'node'.")

    assert is_train.sum() > 0 and (~is_train).sum() > 0, (
        "Split produced an empty train or test partition -- adjust --time-frac / --node-frac."
    )
    return is_train


def build_sequences(df_partition, feat_cols, node_col, time_col, y_encoded_partition, seq_len):
    """Slide a window of seq_len rounds per node, using ONLY the rows passed
    in (i.e. one side of the train/test split -- caller must partition
    first). Label of a window = label of its LAST row."""
    df = df_partition.copy()
    df["_label_enc"] = y_encoded_partition
    df = df.sort_values([node_col, time_col])

    sequences, labels, row_indices = [], [], []
    for _, group in df.groupby(node_col):
        feats = group[feat_cols].values
        labs = group["_label_enc"].values
        idxs = group.index.values
        if len(group) < seq_len:
            continue
        for i in range(seq_len - 1, len(group)):
            sequences.append(feats[i - seq_len + 1: i + 1])
            labels.append(labs[i])
            row_indices.append(idxs[i])

    assert len(sequences) > 0, (
        "No sequences built -- every node group in this partition had fewer than "
        "seq_len rows. Lower --seq-len, or if using --split-mode time, raise "
        "--time-frac so the test partition has enough rounds per node."
    )
    return np.array(sequences), np.array(labels), np.array(row_indices)


def train_lstm(X_seq_train, y_seq_train, n_features, n_classes, epochs=15, batch_size=256, lr=1e-3,
                X_val=None, y_val=None, torch_seed=42):
    """Class weights are computed from TRAIN sequences only -- never from
    validation or test -- so imbalance handling can't leak information about
    the held-out partitions. Validation (if provided) is used only to report
    recall per epoch for sanity-checking hyperparameters; it never touches
    the optimizer and is never mixed with the test partition.
    torch_seed controls weight init + minibatch shuffling ONLY -- the data
    split itself is fixed by RANDOM_STATE, so varying torch_seed across runs
    isolates training variance from data variance."""
    torch.manual_seed(torch_seed)
    np.random.seed(torch_seed)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[lstm] training on {device}, {len(X_seq_train)} sequences")

    classes, counts = np.unique(y_seq_train, return_counts=True)
    weights = np.ones(n_classes, dtype=np.float32)
    for c, cnt in zip(classes, counts):
        weights[c] = len(y_seq_train) / (n_classes * cnt)
    class_weights = torch.tensor(weights, dtype=torch.float32).to(device)

    model = LSTMDetector(n_features, n_classes).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    criterion = nn.CrossEntropyLoss(weight=class_weights)

    loader = DataLoader(SequenceDataset(X_seq_train, y_seq_train), batch_size=batch_size, shuffle=True)
    has_val = X_val is not None and len(X_val) > 0

    for epoch in range(epochs):
        model.train()
        total_loss = 0.0
        for xb, yb in loader:
            xb, yb = xb.to(device), yb.to(device)
            opt.zero_grad()
            out = model(xb)
            loss = criterion(out, yb)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
            opt.step()
            total_loss += loss.item() * len(xb)
        msg = f"  epoch {epoch+1}/{epochs}  train_loss={total_loss/len(X_seq_train):.4f}"

        if has_val:
            val_proba = lstm_predict_proba(model, X_val, device)
            val_pred = np.argmax(val_proba, axis=1)
            val_recall = recall_score(y_val, val_pred, average="macro", zero_division=0)
            msg += f"  val_recall_macro={val_recall:.4f}"
        print(msg)

    if not has_val:
        print("  [warn] no validation set provided -- epochs/hidden_size/dropout were not "
              "tuned against held-out data. Fine for a quick run, but tune against X_val "
              "before trusting the final numbers.")

    return model, device


def lstm_predict_proba(model, X_seq, device, batch_size=512):
    model.eval()
    loader = DataLoader(SequenceDataset(X_seq, np.zeros(len(X_seq))), batch_size=batch_size, shuffle=False)
    probs = []
    with torch.no_grad():
        for xb, _ in loader:
            xb = xb.to(device)
            out = torch.softmax(model(xb), dim=1)
            probs.append(out.cpu().numpy())
    return np.concatenate(probs, axis=0)


def compute_per_round_recall(df, rows, time_col, y_true, y_pred, attack_class_ids):
    """Pooled per-round recall, computed the same way the paper's DT-simulation
    recall is computed (line ~1099): recall = true_positives / all_actual_attacks,
    POOLED across all nodes within each round, not averaged per-node. This is
    NOT the same evaluation protocol as the paper's 92-93% figure (that number
    comes from inside the live Digital Twin simulation, not a static held-out
    classifier test set) -- provided for structural comparability only.
    'Attack' = true label is any class in attack_class_ids (i.e. not Normal)."""
    rounds = df.loc[rows, time_col].values
    is_attack_true = np.isin(y_true, attack_class_ids)
    is_attack_pred = np.isin(y_pred, attack_class_ids)
    correct_attack_catch = is_attack_true & is_attack_pred  # TP (any correct attack call, not necessarily right class)

    per_round = {}
    for rnd, ta, cc in zip(rounds, is_attack_true, correct_attack_catch):
        d = per_round.setdefault(rnd, {"tp": 0, "actual_attacks": 0})
        if ta:
            d["actual_attacks"] += 1
            if cc:
                d["tp"] += 1

    total_tp = sum(d["tp"] for d in per_round.values())
    total_actual = sum(d["actual_attacks"] for d in per_round.values())
    pooled_recall = total_tp / total_actual if total_actual > 0 else float("nan")

    per_round_recalls = {
        str(rnd): (d["tp"] / d["actual_attacks"] if d["actual_attacks"] > 0 else None)
        for rnd, d in sorted(per_round.items())
    }
    return {
        "pooled_recall": float(pooled_recall),
        "total_tp": int(total_tp),
        "total_actual_attacks": int(total_actual),
        "n_rounds": len(per_round),
        "per_round_recall": per_round_recalls,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True, help="Path to WSN-DS CSV")
    ap.add_argument("--node-col", default=None)
    ap.add_argument("--time-col", default=None)
    ap.add_argument("--seq-len", type=int, default=SEQ_LEN)
    ap.add_argument("--xgb-weight", type=float, default=XGB_WEIGHT)
    ap.add_argument("--lstm-weight", type=float, default=LSTM_WEIGHT)
    ap.add_argument("--epochs", type=int, default=15)
    ap.add_argument("--xgb-model-path", default=os.path.join(OUT_DIR, "xgb_model.pkl"))
    ap.add_argument("--split-mode", choices=["time", "node"], default="time",
                     help="'time' = global round threshold, all nodes in both partitions (default, "
                          "matches paper's per-round framing). 'node' = held-out nodes, tests "
                          "generalisation to unseen devices.")
    ap.add_argument("--time-frac", type=float, default=0.7,
                     help="Quantile of the time column used as the train/test boundary (--split-mode time).")
    ap.add_argument("--node-frac", type=float, default=0.8,
                     help="Fraction of nodes assigned to train (--split-mode node).")
    ap.add_argument("--val-frac", type=float, default=0.15,
                     help="Fraction of TRAIN sequences held out as a validation set for the LSTM "
                          "(split by node so no node's rounds appear in both train and val).")
    ap.add_argument("--torch-seed", type=int, default=42,
                     help="Seed for LSTM weight init and minibatch shuffling. Vary this across runs "
                          "to check whether a result is real or just training-variance noise -- the "
                          "data split itself stays fixed (RANDOM_STATE) so seeds are comparable.")
    ap.add_argument("--results-path", default=None,
                     help="Where to write the JSON results. Default: hybrid_xgb_lstm_outputs/hybrid_results.json")
    ap.add_argument("--ensemble-mode", choices=["fixed_weight", "stacking"], default="stacking",
                     help="'stacking' (default): a logistic-regression meta-learner learns per-class how "
                          "much to trust XGB vs LSTM, fit on genuinely held-out validation predictions. "
                          "'fixed_weight': the original --xgb-weight/--lstm-weight blend, kept for comparison.")
    args = ap.parse_args()
    return run_once(args)


def run_once(args):

    assert abs(args.xgb_weight + args.lstm_weight - 1.0) < 1e-6, "Ensemble weights must sum to 1.0"
    os.makedirs(OUT_DIR, exist_ok=True)

    df, node_col, time_col = load_dataset(args.csv, args.node_col, args.time_col)
    feat_cols = get_feature_columns(df, node_col, time_col)
    print(f"[features] using {len(feat_cols)} numeric feature columns: {feat_cols}")

    le = LabelEncoder()
    y_all = le.fit_transform(df["Attack_type"])
    n_classes = len(le.classes_)

    X_static_all = prep_static_features(df, feat_cols)

    # --- Leak-safe split: time-based (default) or node-held-out ---
    is_train = make_split(df, node_col, time_col, y_all, args.split_mode,
                           args.time_frac, args.node_frac, RANDOM_STATE)
    train_idx = df.index[is_train.values]
    test_idx = df.index[~is_train.values]

    # --- XGBoost (static features, row-level, using the SAME partition as the LSTM) ---
    xgb_model = train_or_load_xgb(X_static_all.loc[train_idx], y_all[is_train.values], args.xgb_model_path)
    xgb_test_proba = xgb_model.predict_proba(X_static_all.loc[test_idx])

    # --- LSTM (temporal sequences, per-node windows) ---
    # LSTM is gradient-based and needs normalised inputs (XGBoost above does
    # NOT -- it's tree-based and scale-invariant, so it keeps using raw
    # features to stay comparable with the paper's XGBoost numbers). Scaler
    # is fit on TRAIN ONLY and applied to test -- fitting on test would leak
    # its distribution into "unseen" data.
    scaler = StandardScaler()
    scaler.fit(X_static_all.loc[train_idx])
    df_train_scaled = df.loc[train_idx].copy()
    df_test_scaled = df.loc[test_idx].copy()
    df_train_scaled[feat_cols] = scaler.transform(X_static_all.loc[train_idx])
    df_test_scaled[feat_cols] = scaler.transform(X_static_all.loc[test_idx])

    df_train = df_train_scaled
    df_test = df_test_scaled
    y_train_all = y_all[is_train.values]
    y_test_all = y_all[~is_train.values]

    X_seq_train_full, y_seq_train_full, train_seq_rows = build_sequences(
        df_train, feat_cols, node_col, time_col, y_train_all, args.seq_len
    )
    X_seq_test, y_seq_test, lstm_test_rows = build_sequences(
        df_test, feat_cols, node_col, time_col, y_test_all, args.seq_len
    )
    drop_frac = 1 - (len(lstm_test_rows) / len(test_idx))
    if drop_frac > 0.3:
        print(f"[warn] {drop_frac:.0%} of test rows have no LSTM window (nodes with < seq_len "
              f"rounds in the test partition). Consider lowering --seq-len (currently "
              f"{args.seq_len}) or raising --time-frac so more rounds land in test per node.")

    # Validation split for the LSTM, carved out of TRAIN only, by node --
    # so no node's rounds appear in both the train and validation subsets.
    rng = np.random.RandomState(RANDOM_STATE)
    train_nodes = df_train[node_col].unique()
    rng.shuffle(train_nodes)
    n_val_nodes = max(1, int(len(train_nodes) * args.val_frac))
    val_node_set = set(train_nodes[:n_val_nodes])
    seq_node_of_row = df.loc[train_seq_rows, node_col].values
    is_val_seq = np.isin(seq_node_of_row, list(val_node_set))

    X_seq_train, y_seq_train = X_seq_train_full[~is_val_seq], y_seq_train_full[~is_val_seq]
    X_seq_val, y_seq_val = X_seq_train_full[is_val_seq], y_seq_train_full[is_val_seq]
    val_seq_rows = train_seq_rows[is_val_seq]
    print(f"[lstm split] train_seqs={len(X_seq_train)}, val_seqs={len(X_seq_val)}, test_seqs={len(X_seq_test)}")

    lstm_model, device = train_lstm(
        X_seq_train, y_seq_train, n_features=len(feat_cols),
        n_classes=n_classes, epochs=args.epochs,
        X_val=X_seq_val, y_val=y_seq_val, torch_seed=args.torch_seed,
    )
    lstm_test_proba_by_row = lstm_predict_proba(lstm_model, X_seq_test, device)

    # --- Stacking meta-learner (default ensemble mode) ---
    # The cached xgb_model above was trained on ALL of train_idx, including
    # rows belonging to validation nodes -- using it to generate "validation"
    # predictions for fitting a meta-learner would be in-sample/leaky (it has
    # already memorised those exact rows). So we train a SEPARATE xgb_val_model
    # excluding validation-node rows, purely to get honest out-of-sample XGB
    # predictions to pair with the (already out-of-sample) LSTM validation
    # predictions. The meta-learner is fit on this honest pairing. At test
    # time we go back to using the fully-trained xgb_model + lstm_model
    # (standard stacking practice: base learners are refit on all available
    # data for the deployed model; only the meta-learner's fit needs
    # held-out base predictions to avoid overfitting to base-learner leakage).
    meta_learner = None
    if args.ensemble_mode == "stacking":
        val_node_train_idx = df_train.index[~df_train[node_col].isin(val_node_set)]
        xgb_val_model = train_or_load_xgb(
            X_static_all.loc[val_node_train_idx], y_all[df.index.get_indexer(val_node_train_idx)],
            os.path.join(os.path.dirname(args.xgb_model_path) or OUT_DIR,
                          f"_xgb_val_model_tmp_{args.split_mode}_{args.time_frac}_{args.seq_len}.pkl"),
        )
        xgb_val_proba = xgb_val_model.predict_proba(X_static_all.loc[val_seq_rows])
        lstm_val_proba = lstm_predict_proba(lstm_model, X_seq_val, device)
        y_val_true = y_all[df.index.get_indexer(val_seq_rows)]

        meta_X = np.concatenate([xgb_val_proba, lstm_val_proba], axis=1)
        meta_learner = LogisticRegression(max_iter=2000)
        meta_learner.fit(meta_X, y_val_true)
        val_meta_pred = meta_learner.predict(meta_X)
        val_meta_recall = recall_score(y_val_true, val_meta_pred, average="macro", zero_division=0)
        print(f"[stacking] meta-learner fit on {len(y_val_true)} honest-validation rows, "
              f"val macro recall (in-fit, for sanity only)={val_meta_recall:.4f}")

    # --- Align: ensemble only possible where BOTH a row-level XGB prediction
    # and a windowed LSTM prediction exist (first seq_len-1 rows per node have no window) ---
    common_rows = np.intersect1d(test_idx, lstm_test_rows)
    assert len(common_rows) > 0, "No overlapping rows between XGB test set and LSTM windowed test set."
    print(f"[ensemble] {len(common_rows)} / {len(test_idx)} test rows have both predictions "
          f"({len(test_idx) - len(common_rows)} dropped -- start-of-sequence rows per node, expected)")

    xgb_row_lookup = {r: i for i, r in enumerate(test_idx)}
    lstm_row_lookup = {r: i for i, r in enumerate(lstm_test_rows)}

    y_true, final_pred, xgb_only_pred, lstm_only_pred = [], [], [], []
    for r in common_rows:
        p_xgb = xgb_test_proba[xgb_row_lookup[r]]
        p_lstm = lstm_test_proba_by_row[lstm_row_lookup[r]]
        if args.ensemble_mode == "stacking":
            meta_feat = np.concatenate([p_xgb, p_lstm]).reshape(1, -1)
            pred = meta_learner.predict(meta_feat)[0]
        else:
            p_final = args.xgb_weight * p_xgb + args.lstm_weight * p_lstm
            pred = np.argmax(p_final)
        final_pred.append(pred)
        xgb_only_pred.append(np.argmax(p_xgb))
        lstm_only_pred.append(np.argmax(p_lstm))
        y_true.append(y_all[df.index.get_loc(r)])

    y_true = np.array(y_true)
    final_pred = np.array(final_pred)
    xgb_only_pred = np.array(xgb_only_pred)
    lstm_only_pred = np.array(lstm_only_pred)

    def report(name, y_true, y_pred):
        per_class_recall = recall_score(y_true, y_pred, average=None, zero_division=0, labels=range(n_classes))
        return {
            "accuracy": float(accuracy_score(y_true, y_pred)),
            "recall_macro": float(recall_score(y_true, y_pred, average="macro", zero_division=0, labels=range(n_classes))),
            "recall_weighted": float(recall_score(y_true, y_pred, average="weighted", zero_division=0, labels=range(n_classes))),
            "precision_weighted": float(precision_score(y_true, y_pred, average="weighted", zero_division=0, labels=range(n_classes))),
            "f1_weighted": float(f1_score(y_true, y_pred, average="weighted", zero_division=0, labels=range(n_classes))),
            "recall_per_class": {cls: float(r) for cls, r in zip(le.classes_, per_class_recall)},
        }
    results = {
        "torch_seed": args.torch_seed,
        "time_frac": args.time_frac,
        "split_mode": args.split_mode,
        "n_test_rows_compared": int(len(common_rows)),
        "seq_len": args.seq_len,
        "ensemble_mode": args.ensemble_mode,
        "ensemble_weights": {"xgb": args.xgb_weight, "lstm": args.lstm_weight} if args.ensemble_mode == "fixed_weight" else None,
        "xgb_only": report("xgb", y_true, xgb_only_pred),
        "lstm_only": report("lstm", y_true, lstm_only_pred),
        "hybrid": report("hybrid", y_true, final_pred),
    }

    # Per-round pooled recall, computed the same way as the paper's DT figure --
    # provided alongside per-record for structural comparability, NOT as a
    # drop-in replacement for the 92-93% number (that's a different eval
    # protocol entirely -- see the module docstring / printed warning below).
    normal_ids = [i for i, c in enumerate(le.classes_) if c.lower() == "normal"]
    attack_class_ids = [i for i in range(n_classes) if i not in normal_ids]
    for name, pred in [("xgb_only", xgb_only_pred), ("lstm_only", lstm_only_pred), ("hybrid", final_pred)]:
        per_round = compute_per_round_recall(df, common_rows, time_col, y_true, pred, attack_class_ids)
        results[name]["per_round_pooled_recall"] = per_round["pooled_recall"]
        results[name]["per_round_detail"] = {
            "total_tp": per_round["total_tp"],
            "total_actual_attacks": per_round["total_actual_attacks"],
            "n_rounds": per_round["n_rounds"],
        }

    print("\n=== RESULTS (on the SAME held-out rows for all three models) ===")
    print(json.dumps({k: v for k, v in results.items() if k != "per_round_detail"}, indent=2,
                      default=lambda o: "..." if isinstance(o, dict) and len(o) > 20 else o))
    print("\nFull classification report (hybrid):")
    print(classification_report(y_true, final_pred, labels=range(n_classes),target_names=le.classes_, zero_division=0))
    print("\n" + "=" * 78)
    print("IMPORTANT: neither the per-record nor per-round-pooled recall above is\n"
          "the same evaluation protocol as your paper's 92-93% / 82-86% figures.\n"
          "Those come from INSIDE the live Digital Twin simulation (classifier\n"
          "output feeding trust/routing decisions across 23 rounds x 500 nodes),\n"
          "not from a static held-out test set. This script only evaluates the\n"
          "classifier in isolation. If you want a number directly comparable to\n"
          "the paper's DT-measured recall, the hybrid model needs to be wired\n"
          "into dt_uav_controller.py / the routing simulation itself, not just\n"
          "evaluated standalone. Use this script's numbers to decide whether the\n"
          "hybrid is worth that integration effort -- not as the final paper number.")
    print("=" * 78)

    out_path = args.results_path or os.path.join(OUT_DIR, "hybrid_results.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n[done] results written to {out_path}")
    print("Do NOT paste numbers into the paper until you've sanity-checked this against "
          "a second seed -- the paper's whole Limitations section exists because of "
          "single-seed results burning you once already.")
    return results


if __name__ == "__main__":
    main()