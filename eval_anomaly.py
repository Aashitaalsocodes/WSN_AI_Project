import pandas as pd
import joblib
from sklearn.metrics import classification_report

df = pd.read_csv("data/raw/WSN-DS_with_faults.csv")
y_true = (df['attack_type'] != 'Normal').astype(int)

model = joblib.load("savedmodels/isolation_forest.pkl")
X = df[['ADV_S','ADV_R','JOIN_S','JOIN_R','SCH_S','SCH_R','DATA_S','DATA_R','Data_Sent_To_BS','Expanded Energy']].fillna(0)
y_pred = model.predict(X)
y_pred_binary = (y_pred == -1).astype(int)

print(classification_report(y_true, y_pred_binary))