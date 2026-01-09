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

    def calculate_advanced_accuracy(
        self,
        prediction_strength: float,
        data_quality: float,
        h2h_quality: float,
        form_consistency: float,
    ) -> float:
        """Estimate a normalized accuracy score [0.0, 1.0].

        This method is deliberately simple for the shim: it
        accepts inputs in mixed ranges and normalizes them as needed.
        It must be robust to None/missing values for testing environments.
        """
        try:
            # Normalize inputs to [0,1]
            ps = float(prediction_strength) if prediction_strength is not None else 0.5
        except Exception:
            ps = 0.5

        try:
            dq = float(data_quality) / 100.0 if data_quality is not None else 0.75
        except Exception:
            dq = 0.75

        try:
            h2h = float(h2h_quality) if h2h_quality is not None else 0.5
        except Exception:
            h2h = 0.5

        try:
            fc = float(form_consistency) / 100.0 if form_consistency is not None else 0.5
        except Exception:
            fc = 0.5

        # Weighted linear combination (safe, interpretable)
        score = (0.5 * ps) + (0.25 * dq) + (0.15 * h2h) + (0.10 * fc)

        # Clamp to [0.0, 1.0]
        return max(0.0, min(1.0, float(score)))
