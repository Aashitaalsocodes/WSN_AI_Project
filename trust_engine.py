# trust_engine.py
import pandas as pd
import numpy as np
from config import TRUST_WEIGHTS, TRUST_THRESHOLD

class TrustEngine:
    """
    Calculates trust scores for each node per round based on:
    - historical accuracy (40%)
    - protocol compliance (30%)
    - neighbor recommendation (20%)
    - anomaly score (10%)
    """
    def __init__(self):
        self.weights = TRUST_WEIGHTS
        self.threshold = TRUST_THRESHOLD
        self.history = {}  # store past accuracy per node

    def update_trust(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        df must have columns (per round, per node):
        - historical_accuracy (0-1)
        - protocol_compliance (0-1)
        - neighbor_recommendation (0-1)
        - anomaly_score (0-1), where 0=normal, 1=highly anomalous

        Returns df with added columns: trust_score, suspicious_flag
        """
        inverted_anomaly = 1 - df['anomaly_score'].clip(0, 1)

        df['trust_score'] = (
            self.weights['historical_accuracy'] * df['historical_accuracy'] +
            self.weights['protocol_compliance'] * df['protocol_compliance'] +
            self.weights['neighbor_recommendation'] * df['neighbor_recommendation'] +
            self.weights['anomaly_score'] * inverted_anomaly
        )
        df['trust_score'] = df['trust_score'].clip(0, 1)
        df['suspicious_flag'] = (df['trust_score'] < self.threshold).astype(int)
        return df

    def initialize_trust(self, num_nodes: int) -> pd.DataFrame:
        """Create initial trust scores for new nodes (no history)."""
        df = pd.DataFrame({
            'node_id': range(num_nodes),
            'historical_accuracy': 0.8,
            'protocol_compliance': 0.8,
            'neighbor_recommendation': 0.5,
            'anomaly_score': 0.2
        })
        return self.update_trust(df)


# Quick test when run directly
if __name__ == "__main__":
    sample = pd.DataFrame({
        'historical_accuracy': [0.98, 0.60, 0.80, 0.95, 0.45],
        'protocol_compliance': [0.95, 0.40, 0.85, 0.90, 0.55],
        'neighbor_recommendation': [0.90, 0.50, 0.70, 0.88, 0.60],
        'anomaly_score': [0.02, 0.80, 0.10, 0.05, 0.70]
    })
    engine = TrustEngine()
    result = engine.update_trust(sample)
    print(result[['trust_score', 'suspicious_flag']])