"""Calibration Manager - Non-Linear Probability Calibration
Implements isotonic regression and other calibration techniques to improve prediction reliability.
Phase 2 Optimization: +2-4% confidence improvement expected.
"""

import json
from datetime import datetime

import numpy as np
from sklearn.isotonic import IsotonicRegression


class CalibrationManager:
    """Manages probability calibration using isotonic regression.
    Improves reliability of model confidence predictions.
    """

    def __init__(self, model_name: str = "default"):
        """Initialize calibration manager.

        Args:
            model_name: Name of the model being calibrated

        """
        self.model_name = model_name
        self.isotonic_regressor: IsotonicRegression | None = None
        self.calibration_data: dict = {
            "predictions": [],
            "outcomes": [],
            "timestamps": [],
        }
        self.is_trained = False
        self.training_size = 0

    def add_calibration_sample(
        self,
        predicted_prob: float,
        actual_outcome: float,
        timestamp: float | None = None,
    ):
        """Add a prediction-outcome pair for calibration.

        Args:
            predicted_prob: Model's predicted probability (0-1)
            actual_outcome: Actual outcome (0 or 1, or 0-1 for soft labels)
            timestamp: Optional timestamp of prediction

        """
        # Clip to valid range
        predicted_prob = max(0.0, min(1.0, predicted_prob))
        actual_outcome = max(0.0, min(1.0, actual_outcome))

        self.calibration_data["predictions"].append(predicted_prob)
        self.calibration_data["outcomes"].append(actual_outcome)
        self.calibration_data["timestamps"].append(
            timestamp or datetime.now().timestamp(),
        )

    def add_batch_calibration_samples(
        self,
        predictions: list[float],
        outcomes: list[float],
        timestamps: list[float] | None = None,
    ):
        """Add multiple prediction-outcome pairs.

        Args:
            predictions: List of predicted probabilities
            outcomes: List of actual outcomes
            timestamps: Optional list of timestamps

        """
        if len(predictions) != len(outcomes):
            raise ValueError("Predictions and outcomes must have same length")

        if timestamps is None:
            timestamps = [datetime.now().timestamp()] * len(predictions)
        elif len(timestamps) != len(predictions):
            raise ValueError("Timestamps must match predictions length")

        for pred, outcome, ts in zip(predictions, outcomes, timestamps):
            self.add_calibration_sample(pred, outcome, ts)

    def train_calibration(self, min_samples: int = 30):
        """Train isotonic regression calibrator on accumulated data.

        Args:
            min_samples: Minimum samples required to train

        Returns:
            bool: True if training successful, False otherwise

        """
        if len(self.calibration_data["predictions"]) < min_samples:
            return False

        try:
            # Prepare data
            X = np.array(self.calibration_data["predictions"]).reshape(-1, 1)
            y = np.array(self.calibration_data["outcomes"])

            # Train isotonic regressor
            self.isotonic_regressor = IsotonicRegression(out_of_bounds="clip")
            self.isotonic_regressor.fit(X.flatten(), y)

            self.is_trained = True
            self.training_size = len(self.calibration_data["predictions"])
            return True

        except Exception as e:
            print(f"Calibration training failed: {e!s}")
            return False

    def calibrate_probability(self, predicted_prob: float) -> float:
        """Apply calibration to a predicted probability.

        Args:
            predicted_prob: Raw model probability (0-1)

        Returns:
            Calibrated probability (0-1)

        """
        # Clip to valid range
        predicted_prob = max(0.0, min(1.0, predicted_prob))

        if not self.is_trained or self.isotonic_regressor is None:
            # Return uncalibrated if not trained
            return predicted_prob

        try:
            # Apply isotonic regression
            calibrated = float(self.isotonic_regressor.predict([predicted_prob])[0])
            return max(0.0, min(1.0, calibrated))
        except Exception:
            return predicted_prob

    def calibrate_batch(self, probabilities: list[float]) -> list[float]:
        """Apply calibration to multiple probabilities.

        Args:
            probabilities: List of raw probabilities

        Returns:
            List of calibrated probabilities

        """
        return [self.calibrate_probability(p) for p in probabilities]

    def get_calibration_stats(self) -> dict:
        """Get statistics about calibration.

        Returns:
            Dict with calibration statistics

        """
        if len(self.calibration_data["predictions"]) == 0:
            return {
                "total_samples": 0,
                "is_trained": False,
                "training_size": 0,
                "expected_calibration_error": None,
            }

        predictions = np.array(self.calibration_data["predictions"])
        outcomes = np.array(self.calibration_data["outcomes"])

        # Calculate expected calibration error (ECE)
        ece = self._calculate_ece(predictions, outcomes)

        return {
            "total_samples": len(predictions),
            "is_trained": self.is_trained,
            "training_size": self.training_size,
            "mean_prediction": float(np.mean(predictions)),
            "mean_outcome": float(np.mean(outcomes)),
            "expected_calibration_error": ece,
            "prediction_range": (
                float(np.min(predictions)),
                float(np.max(predictions)),
            ),
            "outcome_range": (float(np.min(outcomes)), float(np.max(outcomes))),
        }

    def _calculate_ece(
        self, predictions: np.ndarray, outcomes: np.ndarray, num_bins: int = 10,
    ) -> float:
        """Calculate expected calibration error.

        Args:
            predictions: Array of predicted probabilities
            outcomes: Array of actual outcomes
            num_bins: Number of bins for ECE calculation

        Returns:
            ECE value (0-1, lower is better)

        """
        bin_edges = np.linspace(0, 1, num_bins + 1)
        ece = 0.0
        bin_count = 0

        for i in range(num_bins):
            mask = (predictions >= bin_edges[i]) & (predictions < bin_edges[i + 1])
            if np.sum(mask) > 0:
                bin_acc = np.mean(outcomes[mask])
                bin_conf = np.mean(predictions[mask])
                ece += np.abs(bin_acc - bin_conf) * np.sum(mask)
                bin_count += np.sum(mask)

        return ece / bin_count if bin_count > 0 else 0.0

    def save_calibration(self, filepath: str):
        """Save calibration data and model to file.

        Args:
            filepath: Path to save calibration

        """
        try:
            calibration_dict = {
                "model_name": self.model_name,
                "is_trained": self.is_trained,
                "training_size": self.training_size,
                "total_samples": len(self.calibration_data["predictions"]),
                "predictions": self.calibration_data["predictions"],
                "outcomes": self.calibration_data["outcomes"],
                "timestamps": self.calibration_data["timestamps"],
                "calibration_stats": self.get_calibration_stats(),
            }

            with open(filepath, "w") as f:
                json.dump(calibration_dict, f, indent=2, default=str)

        except Exception as e:
            print(f"Failed to save calibration: {e!s}")

    def load_calibration(self, filepath: str) -> bool:
        """Load calibration data from file.

        Args:
            filepath: Path to load calibration from

        Returns:
            bool: True if loading successful

        """
        try:
            with open(filepath) as f:
                calibration_dict = json.load(f)

            self.model_name = calibration_dict.get("model_name", "default")
            self.is_trained = calibration_dict.get("is_trained", False)
            self.training_size = calibration_dict.get("training_size", 0)

            self.calibration_data = {
                "predictions": calibration_dict.get("predictions", []),
                "outcomes": calibration_dict.get("outcomes", []),
                "timestamps": calibration_dict.get("timestamps", []),
            }

            # Retrain if we have historical data
            if len(self.calibration_data["predictions"]) >= 30:
                self.train_calibration()
            elif self.is_trained and len(self.calibration_data["predictions"]) > 0:
                # If marked as trained but below retrain threshold, still mark as trained
                # (it was previously trained on this data)
                self.is_trained = True

            return True

        except Exception as e:
            print(f"Failed to load calibration: {e!s}")
            return False


class ModelPerformanceTracker:
    """Tracks per-model performance for dynamic weighting.
    Used in Phase 2 Model-Specific Weighting optimization.
    """

    def __init__(self, model_names: list[str]):
        """Initialize performance tracker.

        Args:
            model_names: List of model names to track

        """
        self.model_names = model_names
        self.performance_history: dict[str, list[dict]] = {
            name: [] for name in model_names
        }
        self.current_weights: dict[str, float] = {
            name: 1.0 / len(model_names) for name in model_names
        }

    def record_prediction(
        self,
        model_name: str,
        prediction: float,
        actual_outcome: float,
        context: dict | None = None,
    ):
        """Record a model prediction and outcome.

        Args:
            model_name: Name of the model
            prediction: Predicted value
            actual_outcome: Actual outcome
            context: Optional context dict (league, confidence level, etc.)

        """
        if model_name not in self.model_names:
            return

        error = abs(prediction - actual_outcome)
        record = {
            "timestamp": datetime.now().timestamp(),
            "prediction": prediction,
            "actual": actual_outcome,
            "error": error,
            "context": context or {},
        }

        self.performance_history[model_name].append(record)

    def get_model_metrics(self, model_name: str, window: int = 50) -> dict:
        """Get performance metrics for a model.

        Args:
            model_name: Name of the model
            window: Number of recent samples to consider

        Returns:
            Dict with metrics (MAE, RMSE, accuracy)

        """
        if model_name not in self.performance_history:
            return {}

        history = self.performance_history[model_name][-window:]

        if len(history) == 0:
            return {"mae": None, "rmse": None, "sample_count": 0}

        errors = np.array([h["error"] for h in history])

        return {
            "model_name": model_name,
            "sample_count": len(history),
            "mae": float(np.mean(errors)),
            "rmse": float(np.sqrt(np.mean(errors**2))),
            "min_error": float(np.min(errors)),
            "max_error": float(np.max(errors)),
        }

    def calculate_dynamic_weights(
        self, window: int = 50, power: float = 2.0,
    ) -> dict[str, float]:
        """Calculate dynamic weights based on recent performance.

        Args:
            window: Number of recent samples to consider
            power: Power factor for weighting (higher = more extreme weighting)

        Returns:
            Dict of model weights normalized to sum to 1.0

        """
        weights = {}

        for model_name in self.model_names:
            metrics = self.get_model_metrics(model_name, window)

            if metrics.get("mae") is None or metrics["sample_count"] < 5:
                weights[model_name] = 1.0 / len(self.model_names)
            else:
                # Lower MAE = higher weight (inverse relationship)
                # Power increases spread between good and bad performers
                mae = metrics["mae"] + 0.0001  # Avoid division by zero
                weights[model_name] = (1.0 / mae) ** power

        # Normalize to sum to 1.0
        total_weight = sum(weights.values())
        weights = {k: v / total_weight for k, v in weights.items()}

        self.current_weights = weights
        return weights

    def get_all_metrics(self) -> dict[str, dict]:
        """Get metrics for all models."""
        return {name: self.get_model_metrics(name) for name in self.model_names}

    def save_performance_history(self, filepath: str):
        """Save performance history to file."""
        try:
            history_dict = {
                "timestamp": datetime.now().isoformat(),
                "model_names": self.model_names,
                "current_weights": self.current_weights,
                "performance_history": self.performance_history,
            }

            with open(filepath, "w") as f:
                json.dump(history_dict, f, indent=2, default=str)

        except Exception as e:
            print(f"Failed to save performance history: {e!s}")

    def load_performance_history(self, filepath: str) -> bool:
        """Load performance history from file."""
        try:
            with open(filepath) as f:
                history_dict = json.load(f)

            self.model_names = history_dict.get("model_names", self.model_names)
            self.current_weights = history_dict.get(
                "current_weights", self.current_weights,
            )
            self.performance_history = history_dict.get("performance_history", {})

            return True

        except Exception as e:
            print(f"Failed to load performance history: {e!s}")
            return False
