# isolation_forest.py
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from config import ISOLATION_FOREST_CONTAMINATION, ISOLATION_FOREST_N_ESTIMATORS
import joblib  # optional, for saving model

class AnomalyDetector:
    """
    Uses Isolation Forest to detect anomalous node behavior per round.
    Features: packet rate, energy trend, data consistency, behavior history.
    """
    def __init__(self, contamination=None, n_estimators=None):
        self.contamination = contamination or ISOLATION_FOREST_CONTAMINATION
        self.n_estimators = n_estimators or ISOLATION_FOREST_N_ESTIMATORS
        self.model = None
        self.is_fitted = False

    def _prepare_features(self, df: pd.DataFrame) -> np.ndarray:
        """
        Extract behavioral features from raw data.
        Expected columns in df (per round per node):
        - packets_sent
        - packets_received
        - energy_percent (current energy / max energy)
        - data_consistency (0-1, how much matches neighbors)
        - protocol_compliance (0-1)
        """
        # Feature engineering
        packet_rate = (df['packets_sent'] + df['packets_received']) / (df['packets_sent'].max() + 1e-6)
        # Energy trend (difference from previous round) – if not available, use 0
        energy_trend = df.get('energy_trend', 0)
        # Use provided columns or defaults
        data_consistency = df.get('data_consistency', 0.9)
        protocol_compliance = df.get('protocol_compliance', 0.8)
        
        features = np.column_stack([
            packet_rate,
            energy_trend,
            data_consistency,
            protocol_compliance,
            df['energy_percent']  # current energy percentage
        ])
        return features

    def fit(self, df_normal: pd.DataFrame):
        """
        Train Isolation Forest on normal (attack‑free) rounds.
        df_normal should contain only data from trusted, normal operation.
        """
        X = self._prepare_features(df_normal)
        self.model = IsolationForest(
            contamination=self.contamination,
            n_estimators=self.n_estimators,
            random_state=42,
            verbose=0
        )
        self.model.fit(X)
        self.is_fitted = True
        return self

    def predict(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Predict anomaly scores for each row.
        Returns original df with added columns:
        - anomaly_score (0 = normal, 1 = anomalous)
        - is_anomaly (bool)
        """
        if not self.is_fitted:
            raise ValueError("Model not fitted. Call fit() first with normal data.")
        X = self._prepare_features(df)
        # IsolationForest returns -1 for anomalies, 1 for normal
        predictions = self.model.predict(X)
        # anomaly_score: 1 = most anomalous, 0 = normal (approximate from decision_function)
        scores = self.model.decision_function(X)
        # Normalize scores to [0,1] where higher = more anomalous
        anomaly_score = 1 - (scores - scores.min()) / (scores.max() - scores.min() + 1e-6)
        
        df = df.copy()
        df['anomaly_score'] = anomaly_score
        df['is_anomaly'] = (predictions == -1).astype(int)
        return df

    def save_model(self, path: str):
        """Save trained model to disk."""
        import joblib
        joblib.dump(self.model, path)
        print(f"Model saved to {path}")

    def load_model(self, path: str):
        """Load a previously trained model."""
        import joblib
        self.model = joblib.load(path)
        self.is_fitted = True
        print(f"Model loaded from {path}")


# Quick test when run directly
if __name__ == "__main__":
    # Simulate normal behavior (100 normal rounds)
    np.random.seed(42)
    n_samples = 100
    normal_data = pd.DataFrame({
        'packets_sent': np.random.poisson(5, n_samples),
        'packets_received': np.random.poisson(5, n_samples),
        'energy_percent': np.random.uniform(0.7, 1.0, n_samples),
        'data_consistency': np.random.uniform(0.85, 1.0, n_samples),
        'protocol_compliance': np.random.uniform(0.9, 1.0, n_samples),
        'energy_trend': np.random.normal(0, 0.01, n_samples)
    })
    
    # Fit detector
    detector = AnomalyDetector(contamination=0.05)
    detector.fit(normal_data)
    
    # Test on a mix of normal and anomalous
    test_data = pd.DataFrame({
        'packets_sent': [5, 50, 4, 200],
        'packets_received': [5, 45, 4, 180],
        'energy_percent': [0.9, 0.3, 0.88, 0.05],
        'data_consistency': [0.95, 0.40, 0.92, 0.10],
        'protocol_compliance': [0.95, 0.50, 0.94, 0.20],
        'energy_trend': [0.0, -0.3, 0.0, -0.8]
    })
    result = detector.predict(test_data)
    print(result[['anomaly_score', 'is_anomaly']])