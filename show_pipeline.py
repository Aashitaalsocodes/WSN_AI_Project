import json

with open('outputs/final_pipeline_result.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print("Top-level keys:", list(data.keys()))
print()

ml = data.get('ml_predictions')
if isinstance(ml, dict):
    keys = list(ml.keys())
    print(f"ml_predictions: dict, {len(keys)} keys")
    print("First 5 keys:", keys[:5])
    first_key = keys[0]
    print(f"Sample value for key '{first_key}':", ml[first_key])
elif isinstance(ml, list):
    print(f"ml_predictions: list, {len(ml)} items")
    print("First item:", ml[0])
else:
    print("ml_predictions type:", type(ml), ml)