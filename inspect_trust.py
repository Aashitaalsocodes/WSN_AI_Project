import pandas as pd
from trust_engine import TrustEngine

te = TrustEngine()
df = pd.read_csv('processed_data.csv', nrows=20)
result = te.update_trust(df)
print(result.columns.tolist())
print(result.head(10))