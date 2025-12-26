"""A small AIMLPredictor shim used for tests and local development only.

This provides a deterministic, lightweight implementation of the minimal API
expected by tests: `AIMLPredictor.extract_advanced_features` and
`AIMLPredictor.predict_with_ml_ensemble`.
"""

from typing import Any


class AIMLPredictor:
    def __init__(self, *args, **kwargs):
        # Lightweight shim - no model loaded
        self.model_loaded = False

    def extract_advanced_features(
        self,
        match_data: dict,
        home_stats: dict,
        away_stats: dict,
        h2h_data: dict,
        weather_data: dict,
        referee_data: dict,
    ):
        # Defer numpy import to allow graceful test skip if numpy unavailable
        import numpy as np

        # Return a 1x48 array filled with zeros
        return np.zeros((1, 48), dtype=float)

    def predict_with_ml_ensemble(self, features: Any):
        # Return deterministic probabilities that sum to 1
        return {
            "home_win_probability": 0.5,
            "draw_probability": 0.3,
            "away_win_probability": 0.2,
            "accuracy_estimate": 0.6,
        }
