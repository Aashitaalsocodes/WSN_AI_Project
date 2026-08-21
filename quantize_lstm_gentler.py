"""
quantize_lstm_gentler.py

Follow-up to quantize_edge_models.py's LSTM section.

PURPOSE:
Full int8 post-training quantization (int8 in, int8 weights/activations,
float32 out) on the LSTM 16/1/8 model gave a real but fairly large accuracy
hit: MSE 0.000065 -> 0.000353 (~5.4x worse), for 2.62x smaller size and
~15x faster desktop inference. Before accepting that tradeoff for the
paper, this script tries two gentler, standard alternatives on the SAME
trained model:

  1. DYNAMIC-RANGE quantization: only weights are quantized to int8,
     activations stay float32, computed at inference time. Keeps
     float32 input/output (no int8 in/out plumbing needed), typically
     preserves accuracy much better than full int8, less aggressive
     size/speed win.

  2. FLOAT16 quantization: weights stored as float16 instead of float32.
     Usually near-zero accuracy loss, ~2x size reduction (not 4x like
     int8), speed gain depends on whether the target hardware has
     float16 support (desktop CPU here likely doesn't get a big speedup,
     but real edge accelerators often do).

REAL, MEASURED numbers only -- no simulated/fabricated results.

Uses the SAME trained model (same architecture, same seed=42, same
training data/split) as quantize_edge_models.py's quantize_lstm(), so
these numbers are directly comparable to the full-int8 result already
measured. Retrains once (fast, single small model) rather than trying to
reuse a serialized model across scripts, to keep this self-contained.

Output: outputs/quantize_lstm_gentler_results.csv
"""

import time
import tempfile
from pathlib import Path

import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping
import pandas as pd

DATA_DIR = Path(".")
OUTPUT_PATH = Path("outputs/quantize_lstm_gentler_results.csv")

LSTM_UNITS, LSTM_LAYERS, LSTM_DENSE = 16, 1, 8
SEED = 42  # same seed used in quantize_edge_models.py's quantize_lstm()


def load_data():
    X_train_full = np.load(DATA_DIR / "X_train.npy")
    y_train_full = np.load(DATA_DIR / "y_train.npy")
    X_test = np.load(DATA_DIR / "X_test.npy")
    y_test = np.load(DATA_DIR / "y_test.npy")

    n_val = int(0.15 * len(X_train_full))
    X_train, y_train = X_train_full[:-n_val], y_train_full[:-n_val]
    X_val, y_val = X_train_full[-n_val:], y_train_full[-n_val:]

    X_train_r = X_train.reshape(-1, X_train.shape[1], 1).astype(np.float32)
    X_val_r = X_val.reshape(-1, X_val.shape[1], 1).astype(np.float32)
    X_test_r = X_test.reshape(-1, X_test.shape[1], 1).astype(np.float32)

    return (X_train_r, y_train), (X_val_r, y_val), (X_test_r, y_test)


def build_and_train():
    (X_train_r, y_train), (X_val_r, y_val), (X_test_r, y_test) = load_data()

    tf.random.set_seed(SEED)
    np.random.seed(SEED)

    model = Sequential([
        LSTM(LSTM_UNITS, input_shape=(X_train_r.shape[1], 1)),
        Dense(LSTM_DENSE, activation="relu"),
        Dense(1, activation="linear"),
    ])
    model.compile(optimizer=Adam(), loss="mse", metrics=["mae"])
    early_stop = EarlyStopping(monitor="val_loss", patience=8, restore_best_weights=True)
    model.fit(
        X_train_r, y_train, epochs=50, batch_size=128,
        validation_data=(X_val_r, y_val), callbacks=[early_stop], verbose=0,
    )
    return model, (X_train_r, y_train), (X_test_r, y_test)


def make_unrolled_copy(model, input_len):
    """Same trick as quantize_edge_models.py: TFLite converter can't lower
    Keras' default dynamic-loop LSTM, so rebuild with unroll=True and copy
    the trained weights over (same weights, static-unrolled graph)."""
    convert_model = Sequential([
        LSTM(LSTM_UNITS, input_shape=(input_len, 1), unroll=True),
        Dense(LSTM_DENSE, activation="relu"),
        Dense(1, activation="linear"),
    ])
    convert_model.build(input_shape=(None, input_len, 1))
    convert_model.set_weights(model.get_weights())
    return convert_model


def measure_inference_ms(interpreter, input_details, output_details, X_sample, is_float_input,
                          n_repeats=500):
    def predict_one(x_row):
        x_in = x_row.astype(np.float32) if is_float_input else x_row
        interpreter.set_tensor(input_details["index"], x_in.reshape(input_details["shape"]))
        interpreter.invoke()
        return interpreter.get_tensor(output_details["index"])[0][0]

    _ = predict_one(X_sample[0])  # warm-up
    start = time.perf_counter()
    for i in range(n_repeats):
        _ = predict_one(X_sample[i % len(X_sample)])
    return (time.perf_counter() - start) * 1000.0 / n_repeats


def evaluate_tflite(tflite_bytes, X_test_r, y_test, is_float_input=True):
    interpreter = tf.lite.Interpreter(model_content=tflite_bytes)
    interpreter.allocate_tensors()
    input_details = interpreter.get_input_details()[0]
    output_details = interpreter.get_output_details()[0]

    def predict_one(x_row):
        x_in = x_row.astype(np.float32) if is_float_input else x_row
        interpreter.set_tensor(input_details["index"], x_in.reshape(input_details["shape"]))
        interpreter.invoke()
        return interpreter.get_tensor(output_details["index"])[0][0]

    preds = np.array([predict_one(X_test_r[i]) for i in range(len(X_test_r))])
    mse = float(np.mean((preds - y_test) ** 2))
    mae = float(np.mean(np.abs(preds - y_test)))
    median_ms = measure_inference_ms(interpreter, input_details, output_details, X_test_r, is_float_input)
    return mse, mae, median_ms


def main():
    print("Training LSTM 16/1/8 (seed=42, same as quantize_edge_models.py)...")
    model, (X_train_r, y_train), (X_test_r, y_test) = build_and_train()
    convert_model = make_unrolled_copy(model, X_train_r.shape[1])

    results = []

    # --- Reference: plain float32 (already measured in quantize_edge_models.py,
    # re-measured here for a self-contained, directly comparable table) ---
    f32_loss = model.evaluate(X_test_r, y_test, verbose=0)
    with tempfile.NamedTemporaryFile(suffix=".h5", delete=False) as tmp:
        tmp_path = tmp.name
    model.save(tmp_path)
    f32_size_kb = Path(tmp_path).stat().st_size / 1024.0
    Path(tmp_path).unlink()
    results.append({
        "precision": "float32_keras", "mse": float(f32_loss[0]), "mae": float(f32_loss[1]),
        "size_kb": f32_size_kb, "desktop_inference_ms_median": None,  # measured via Keras .predict elsewhere
    })
    print(f"float32 (Keras)      : MSE={f32_loss[0]:.6f}  MAE={f32_loss[1]:.6f}  size={f32_size_kb:.2f}KB")

    # --- Variant 1: dynamic-range quantization (weights only, float32 in/out) ---
    converter = tf.lite.TFLiteConverter.from_keras_model(convert_model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    # No representative_dataset, no target_spec restriction -> dynamic-range
    # quantization: weights become int8, activations computed in float32.
    tflite_dynamic = converter.convert()
    dyn_size_kb = len(tflite_dynamic) / 1024.0
    dyn_mse, dyn_mae, dyn_ms = evaluate_tflite(tflite_dynamic, X_test_r, y_test, is_float_input=True)
    results.append({
        "precision": "dynamic_range_int8_weights", "mse": dyn_mse, "mae": dyn_mae,
        "size_kb": dyn_size_kb, "desktop_inference_ms_median": dyn_ms,
    })
    print(f"dynamic-range (int8 weights only) : MSE={dyn_mse:.6f}  MAE={dyn_mae:.6f}  "
          f"size={dyn_size_kb:.2f}KB  inference_median={dyn_ms:.5f}ms")

    # --- Variant 2: float16 quantization ---
    converter = tf.lite.TFLiteConverter.from_keras_model(convert_model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    converter.target_spec.supported_types = [tf.float16]
    tflite_fp16 = converter.convert()
    fp16_size_kb = len(tflite_fp16) / 1024.0
    fp16_mse, fp16_mae, fp16_ms = evaluate_tflite(tflite_fp16, X_test_r, y_test, is_float_input=True)
    results.append({
        "precision": "float16", "mse": fp16_mse, "mae": fp16_mae,
        "size_kb": fp16_size_kb, "desktop_inference_ms_median": fp16_ms,
    })
    print(f"float16                            : MSE={fp16_mse:.6f}  MAE={fp16_mae:.6f}  "
          f"size={fp16_size_kb:.2f}KB  inference_median={fp16_ms:.5f}ms")

    print()
    print("Reference (from quantize_edge_models.py, same trained config):")
    print("  float32 (measured there) : MSE=0.000065  size=48.30KB  inference=0.18880ms")
    print("  full int8 (measured there): MSE=0.000353  size=18.46KB  inference=0.01240ms")

    df = pd.DataFrame(results)
    OUTPUT_PATH.parent.mkdir(exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)
    print()
    print(f"Saved: {OUTPUT_PATH}")
    print()
    print("REMINDER: desktop_inference_ms_median is DESKTOP CPU timing, not edge hardware.")


if __name__ == "__main__":
    main()