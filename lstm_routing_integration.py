"""
lstm_routing_integration.py
Integrate LSTM energy forecasts into routing decisions.
"""

import numpy as np
import tensorflow as tf
from tensorflow.keras.models import load_model
from pathlib import Path

# Load the trained model
MODEL_PATH = Path("outputs/lstm_models/lstm_dt_energy_model.h5")

class LSTMEnergyRouter:
    """
    Router that uses LSTM energy forecasts for proactive routing decisions.
    """
    
    def __init__(self, model_path=MODEL_PATH):
        # Load with custom objects to handle the metric
        self.model = load_model(
            model_path,
            custom_objects={'mse': 'mse', 'mae': 'mae'}
        )
        self.history = {}  # Store energy history per node
        self.forecasts = {}  # Store energy forecasts per node
    
    def update_energy_history(self, node_id, current_energy):
        """Update energy history for a node."""
        if node_id not in self.history:
            self.history[node_id] = []
        self.history[node_id].append(current_energy)
        
        # Keep only last 3 values for forecasting
        if len(self.history[node_id]) > 3:
            self.history[node_id] = self.history[node_id][-3:]
    
    def forecast_energy(self, node_id):
        """Forecast next energy value for a node."""
        if node_id not in self.history or len(self.history[node_id]) < 3:
            return None
        
        # Prepare input: last 3 energy values
        X = np.array(self.history[node_id]).reshape(1, 3, 1)
        forecast = self.model.predict(X, verbose=0)[0][0]
        
        self.forecasts[node_id] = forecast
        return forecast
    
    def get_routing_cost_penalty(self, node_id):
        """
        Get energy-based routing cost penalty.
        Higher penalty for nodes with predicted low energy.
        """
        forecast = self.forecast_energy(node_id)
        if forecast is None:
            return 1.0  # No penalty if no forecast available
        
        # If predicted energy is low, heavily penalize
        if forecast < 0.1:
            return 10.0
        elif forecast < 0.2:
            return 5.0
        elif forecast < 0.3:
            return 2.0
        else:
            return 1.0

# Test the router
if __name__ == "__main__":
    router = LSTMEnergyRouter()
    print("LSTMEnergyRouter initialized successfully!")
    
    # Test with sample data
    test_node = "node_0"
    test_energies = [0.8, 0.7, 0.65]
    
    for e in test_energies:
        router.update_energy_history(test_node, e)
        forecast = router.forecast_energy(test_node)
        penalty = router.get_routing_cost_penalty(test_node)
        print(f"Node {test_node}: energy={e:.3f}, forecast={forecast if forecast else 'None'}, penalty={penalty:.2f}")