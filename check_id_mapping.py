import pandas as pd
import json

df = pd.read_csv("data/processed/processed_data.csv")
print("unique node_id count:", df["node_id"].nunique())
print("node_id sample:", df["node_id"].unique()[:5])
print("timestamp min/max:", df["timestamp"].min(), df["timestamp"].max())
print("timestamp nunique:", df["timestamp"].nunique())
print("rows per node_id (should be constant if timestamp=round):")
print(df.groupby("node_id").size().describe())

with open("outputs/digital_twin_results_packetmodel_seed42.json", encoding="utf-8") as f:
    sim = json.load(f)
sim_node_ids = list(sim["rounds"][0]["node_energy_snapshot"].keys())
print("\nseed42 node_id sample:", sim_node_ids[:5])
print("seed42 num nodes:", len(sim_node_ids))

csv_ids = set(df["node_id"].unique())
overlap = csv_ids.intersection(set(sim_node_ids))
print("\ndirect string overlap betweencsv node_id and seed42 node_id:", len(overlap))
