import json

files = [
    "outputs/digital_twin_results_packetmodel_seed42.json",
    "outputs/node_energy_history.json",
]

for path in files:
    print("="*60)
    print(path)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        keys = list(data.keys())
        print(f"dict with {len(keys)} keys, first 10: {keys[:10]}")
        first_key = keys[0]
        v = data[first_key]
        print(f"  data[{first_key!r}] type={type(v).__name__}", end="")
        if isinstance(v, list):
            print(f" len={len(v)}")
            print(f"  item[0] type={type(v[0]).__name__}: {str(v[0])[:200]}")
        elif isinstance(v, dict):
            print(f" subkeys(first10)={list(v.keys())[:10]}")
    elif isinstance(data, list):
        print(f"list, len={len(data)}")
        print(f"  item[0]: {str(data[0])[:300]}")
