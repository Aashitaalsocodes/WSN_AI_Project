import pandas as pd
df = pd.read_csv("data/processed/processed_data.csv")
print("shape:", df.shape)
print("columns:", list(df.columns))
print(df.head(3).to_string())
