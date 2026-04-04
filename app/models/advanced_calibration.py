#!/usr/bin/env python3
"""Advanced Probability Calibration System v1.0
State-of-the-art calibration techniques for reliable confidence estimation:
- Platt Scaling (sigmoid calibration)
- Temperature Scaling (for neural networks)
- Beta Calibration (flexible 3-parameter calibration)
- Venn-ABERS Calibration (multi-class probabilistic)
- Histogram Binning (non-parametric)
- Conformal Prediction (distribution-free coverage guarantees)
- Ensemble Calibration (combines multiple methods)
"""

import json
import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy import optimize


@dataclass
class CalibrationResult:
    """Result of probability calibration"""

    calibrated_probs: np.ndarray
    confidence: float
    prediction_set: list[int]
    coverage_guarantee: float
    calibration_method: str
    uncertainty: float
    reliability_score: float


@dataclass
class CalibrationMetrics:
    """Calibration quality metrics"""

    expected_calibration_error: float
    maximum_calibration_error: float
    brier_score: float
    log_loss: float
    reliability_diagram: dict[str, list[float]]
    sharpness: float  # How confident predictions are (lower = more confident)


class PlattScaling:
    """Platt Scaling (sigmoid calibration) for binary/multi-class calibration.
    Learns sigmoid parameters A and B: P(y=1|f) = 1 / (1 + exp(A*f + B))
    """

    def __init__(self):
        self.A: float = 0.0
        self.B: float = 0.0
        self.is_fitted = False

    def fit(self, logits: np.ndarray, labels: np.ndarray):
        """Fit Platt scaling parameters.

        Args:
            logits: Raw model outputs (before sigmoid)
            labels: Binary labels (0 or 1)

        """
        # Target probabilities with label smoothing (Platt's approach)
        N_pos = np.sum(labels == 1)
        N_neg = np.sum(labels == 0)

        # Smoothed targets
        t_pos = (N_pos + 1) / (N_pos + 2)
        t_neg = 1 / (N_neg + 2)
        target = np.where(labels == 1, t_pos, t_neg)

        # Optimize A and B using maximum likelihood
        def negative_log_likelihood(params):
            a, b = params
            p = 1 / (1 + np.exp(a * logits + b))
            p = np.clip(p, 1e-10, 1 - 1e-10)
            return -np.sum(target * np.log(p) + (1 - target) * np.log(1 - p))

        result = optimize.minimize(
            negative_log_likelihood, x0=[0, 0], method="L-BFGS-B",
        )

        self.A, self.B = result.x
        self.is_fitted = True

    def calibrate(self, logits: np.ndarray) -> np.ndarray:
        """Apply Platt scaling to logits"""
        if not self.is_fitted:
            return 1 / (1 + np.exp(-logits))
        return 1 / (1 + np.exp(self.A * logits + self.B))


class TemperatureScaling:
    """Temperature Scaling for neural network calibration.
    Learns single temperature T: softmax(logits / T)
    Preserves accuracy while improving calibration.
    """

    def __init__(self):
        self.temperature: float = 1.0
        self.is_fitted = False

    def fit(self, logits: np.ndarray, labels: np.ndarray):
        """Fit temperature parameter using NLL minimization.

        Args:
            logits: Raw network outputs [n_samples, n_classes]
            labels: True class labels [n_samples]

        """

        def nll_loss(temperature):
            temperature = max(0.01, temperature[0])  # Prevent division by zero
            scaled_logits = logits / temperature
            # Softmax
            exp_logits = np.exp(
                scaled_logits - np.max(scaled_logits, axis=1, keepdims=True),
            )
            probs = exp_logits / np.sum(exp_logits, axis=1, keepdims=True)

            # Negative log likelihood
            log_probs = np.log(np.clip(probs, 1e-10, 1.0))
            nll = -np.mean(log_probs[np.arange(len(labels)), labels.astype(int)])
            return nll

        result = optimize.minimize(
            nll_loss, x0=[1.0], method="L-BFGS-B", bounds=[(0.01, 10.0)],
        )

        self.temperature = result.x[0]
        self.is_fitted = True

    def calibrate(self, logits: np.ndarray) -> np.ndarray:
        """Apply temperature scaling to logits"""
        scaled_logits = logits / self.temperature
        exp_logits = np.exp(
            scaled_logits - np.max(scaled_logits, axis=1, keepdims=True),
        )
        return exp_logits / np.sum(exp_logits, axis=1, keepdims=True)


class BetaCalibration:
    """Beta Calibration - flexible 3-parameter calibration.
    Maps probabilities to beta distribution: beta(a, b, c) where
    calibrated = 1 / (1 + 1/(c * (p^a / (1-p)^b)))
    """

    def __init__(self):
        self.a: float = 1.0
        self.b: float = 1.0
        self.c: float = 1.0
        self.is_fitted = False

    def fit(self, probs: np.ndarray, labels: np.ndarray):
        """Fit beta calibration parameters.

        Args:
            probs: Predicted probabilities
            labels: Binary labels

        """
        probs = np.clip(probs, 1e-10, 1 - 1e-10)

        def negative_log_likelihood(params):
            a, b, c = params
            a = max(0.01, a)
            b = max(0.01, b)
            c = max(0.01, c)

            # Beta calibration formula
            lr = c * (probs**a) / ((1 - probs) ** b)
            calibrated = lr / (1 + lr)
            calibrated = np.clip(calibrated, 1e-10, 1 - 1e-10)

            # Binary cross-entropy
            nll = -np.mean(
                labels * np.log(calibrated) + (1 - labels) * np.log(1 - calibrated),
            )
            return nll

        result = optimize.minimize(
            negative_log_likelihood,
            x0=[1.0, 1.0, 1.0],
            method="L-BFGS-B",
            bounds=[(0.01, 10.0), (0.01, 10.0), (0.01, 100.0)],
        )

        self.a, self.b, self.c = result.x
        self.is_fitted = True

    def calibrate(self, probs: np.ndarray) -> np.ndarray:
        """Apply beta calibration to probabilities"""
        if not self.is_fitted:
            return probs

        probs = np.clip(probs, 1e-10, 1 - 1e-10)
        lr = self.c * (probs**self.a) / ((1 - probs) ** self.b)
        return lr / (1 + lr)


class HistogramBinning:
    """Histogram Binning - non-parametric calibration.
    Divides probability range into bins and maps each to empirical accuracy.
    """

    def __init__(self, n_bins: int = 15):
        self.n_bins = n_bins
        self.bin_edges: np.ndarray = np.linspace(0, 1, n_bins + 1)
        self.bin_calibrated: np.ndarray = np.linspace(
            0.5 / n_bins, 1 - 0.5 / n_bins, n_bins,
        )
        self.is_fitted = False

    def fit(self, probs: np.ndarray, labels: np.ndarray):
        """Fit histogram binning.

        Args:
            probs: Predicted probabilities
            labels: Binary labels

        """
        self.bin_calibrated = np.zeros(self.n_bins)

        for i in range(self.n_bins):
            mask = (probs >= self.bin_edges[i]) & (probs < self.bin_edges[i + 1])
            if np.sum(mask) > 0:
                self.bin_calibrated[i] = np.mean(labels[mask])
            else:
                # Use midpoint if no samples in bin
                self.bin_calibrated[i] = (self.bin_edges[i] + self.bin_edges[i + 1]) / 2

        self.is_fitted = True

    def calibrate(self, probs: np.ndarray) -> np.ndarray:
        """Apply histogram binning calibration"""
        if not self.is_fitted:
            return probs

        calibrated = np.zeros_like(probs)
        for i in range(self.n_bins):
            mask = (probs >= self.bin_edges[i]) & (probs < self.bin_edges[i + 1])
            calibrated[mask] = self.bin_calibrated[i]

        return calibrated


class VennABERS:
    """Venn-ABERS Calibration - provides valid probability intervals.
    Produces both lower and upper probability bounds with coverage guarantee.
    """

    def __init__(self):
        self.calibration_scores: list[tuple[float, int]] = []
        self.is_fitted = False

    def fit(self, probs: np.ndarray, labels: np.ndarray):
        """Store calibration data for Venn-ABERS.

        Args:
            probs: Predicted probabilities
            labels: Binary labels

        """
        self.calibration_scores = list(zip(probs.tolist(), labels.astype(int).tolist()))
        self.calibration_scores.sort(key=lambda x: x[0])
        self.is_fitted = True

    def calibrate(self, prob: float) -> tuple[float, float]:
        """Get Venn-ABERS probability interval.

        Returns:
            (lower_bound, upper_bound) probability interval

        """
        if not self.is_fitted or len(self.calibration_scores) == 0:
            return (prob, prob)

        # Find position in sorted calibration scores
        n = len(self.calibration_scores)

        # Calculate p0 (assume label is 0)
        scores_with_0 = self.calibration_scores + [(prob, 0)]
        scores_with_0.sort(key=lambda x: x[0])

        pos_0 = next(
            i for i, (s, l) in enumerate(scores_with_0) if s == prob and l == 0
        )
        n_below_0 = sum(1 for i, (s, l) in enumerate(scores_with_0[:pos_0]) if l == 1)
        n_above_0 = sum(1 for i, (s, l) in enumerate(scores_with_0[pos_0:]) if l == 1)

        p0 = n_below_0 / (pos_0 + 1) if pos_0 >= 0 else 0

        # Calculate p1 (assume label is 1)
        scores_with_1 = self.calibration_scores + [(prob, 1)]
        scores_with_1.sort(key=lambda x: x[0])

        pos_1 = next(
            i for i, (s, l) in enumerate(scores_with_1) if s == prob and l == 1
        )
        n_below_1 = sum(1 for i, (s, l) in enumerate(scores_with_1[:pos_1]) if l == 1)

        p1 = (n_below_1 + 1) / (pos_1 + 1) if pos_1 >= 0 else 1

        return (min(p0, p1), max(p0, p1))


class ConformalCalibrator:
    """Conformal Prediction for distribution-free coverage guarantees.
    Produces prediction sets with guaranteed coverage probability.
    """

    def __init__(self, alpha: float = 0.1):
        """Args:
        alpha: Significance level (1 - alpha = coverage probability)

        """
        self.alpha = alpha
        self.quantile: float = 0.0
        self.calibration_scores: list[float] = []
        self.is_fitted = False

    def fit(self, probs: np.ndarray, labels: np.ndarray):
        """Fit conformal predictor on calibration data.

        Args:
            probs: Predicted probabilities [n_samples, n_classes]
            labels: True class labels [n_samples]

        """
        # Nonconformity score: 1 - probability of true class
        self.calibration_scores = []

        for i, label in enumerate(labels):
            if len(probs.shape) == 1:
                score = 1 - probs[i]
            else:
                score = 1 - probs[i, int(label)]
            self.calibration_scores.append(score)

        self.calibration_scores.sort()

        # Quantile for coverage
        n = len(self.calibration_scores)
        k = int(np.ceil((n + 1) * (1 - self.alpha)))
        self.quantile = self.calibration_scores[min(k - 1, n - 1)]

        self.is_fitted = True

    def get_prediction_set(self, probs: np.ndarray) -> tuple[list[int], float]:
        """Get prediction set with coverage guarantee.

        Args:
            probs: Predicted probabilities [n_classes]

        Returns:
            (prediction_set, coverage_probability)

        """
        if not self.is_fitted:
            return [int(np.argmax(probs))], float(np.max(probs))

        # Include all classes with nonconformity <= quantile
        prediction_set = []
        for class_idx, prob in enumerate(probs):
            if 1 - prob <= self.quantile:
                prediction_set.append(class_idx)

        if not prediction_set:
            prediction_set = [int(np.argmax(probs))]

        coverage = 1 - self.alpha
        return prediction_set, coverage


class AdaptiveCalibrator:
    """Adaptive Calibrator that learns which calibration method works best
    for different prediction contexts (confidence level, match type, etc.)
    """

    def __init__(self):
        self.method_performances: dict[str, list[float]] = {
            "platt": [],
            "temperature": [],
            "beta": [],
            "histogram": [],
            "venn_abers": [],
        }
        self.context_weights: dict[str, dict[str, float]] = {}

    def record_performance(self, method: str, error: float, context: str = "default"):
        """Record calibration error for a method in a context"""
        if method in self.method_performances:
            self.method_performances[method].append(error)

        if context not in self.context_weights:
            self.context_weights[context] = dict.fromkeys(self.method_performances, 1.0)

        # Update weights with exponential moving average
        alpha = 0.1
        for m in self.method_performances:
            if m == method:
                self.context_weights[context][m] = (1 - alpha) * self.context_weights[
                    context
                ][m] + alpha * (1 - error)  # Higher weight for lower error

    def get_best_method(self, context: str = "default") -> str:
        """Get the best calibration method for a context"""
        if context not in self.context_weights:
            return "temperature"  # Default

        weights = self.context_weights[context]
        return max(weights, key=lambda m: weights[m])


class AdvancedCalibrationManager:
    """Comprehensive calibration manager combining multiple calibration techniques
    with automatic method selection and ensemble calibration.
    """

    def __init__(self, models_dir: str = "models/calibration"):
        self.logger = logging.getLogger(__name__)
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)

        # Initialize calibrators
        self.platt = PlattScaling()
        self.temperature = TemperatureScaling()
        self.beta = BetaCalibration()
        self.histogram = HistogramBinning(n_bins=15)
        self.venn_abers = VennABERS()
        self.conformal = ConformalCalibrator(alpha=0.1)
        self.adaptive = AdaptiveCalibrator()

        # Calibration data
        self.calibration_data: dict[str, list] = {
            "probs": [],
            "labels": [],
            "contexts": [],
        }

        # Load existing calibration
        self._load_calibration()

        self.logger.info("Advanced Calibration Manager initialized")

    def add_sample(
        self, predicted_probs: np.ndarray, true_label: int, context: str = "default",
    ):
        """Add a calibration sample.

        Args:
            predicted_probs: Model's predicted probabilities [n_classes]
            true_label: True class label
            context: Prediction context (e.g., 'high_confidence', 'derby')

        """
        self.calibration_data["probs"].append(predicted_probs.tolist())
        self.calibration_data["labels"].append(true_label)
        self.calibration_data["contexts"].append(context)

    def fit_all(self, min_samples: int = 50) -> bool:
        """Fit all calibration methods on accumulated data.

        Args:
            min_samples: Minimum samples required

        Returns:
            True if fitting successful

        """
        n_samples = len(self.calibration_data["probs"])

        if n_samples < min_samples:
            self.logger.warning(f"Insufficient samples: {n_samples} < {min_samples}")
            return False

        probs = np.array(self.calibration_data["probs"])
        labels = np.array(self.calibration_data["labels"])

        self.logger.info(f"Fitting calibrators on {n_samples} samples...")

        try:
            # For binary calibrators, use max probability
            max_probs = np.max(probs, axis=1)
            binary_labels = (labels == np.argmax(probs, axis=1)).astype(int)

            # Fit each calibrator
            self.platt.fit(max_probs, binary_labels)
            self.logger.info("  ✓ Platt Scaling fitted")

            # Temperature scaling needs logits
            logits = np.log(probs + 1e-10) - np.log(1 - probs + 1e-10)
            self.temperature.fit(logits, labels)
            self.logger.info(
                f"  ✓ Temperature Scaling fitted (T={self.temperature.temperature:.3f})",
            )

            self.beta.fit(max_probs, binary_labels)
            self.logger.info("  ✓ Beta Calibration fitted")

            self.histogram.fit(max_probs, binary_labels)
            self.logger.info("  ✓ Histogram Binning fitted")

            self.venn_abers.fit(max_probs, binary_labels)
            self.logger.info("  ✓ Venn-ABERS fitted")

            self.conformal.fit(probs, labels)
            self.logger.info(
                f"  ✓ Conformal Predictor fitted (quantile={self.conformal.quantile:.3f})",
            )

            # Save calibration
            self._save_calibration()

            return True

        except Exception as e:
            self.logger.error(f"Calibration fitting failed: {e}")
            return False

    def calibrate(
        self, probs: np.ndarray, method: str = "ensemble", context: str = "default",
    ) -> CalibrationResult:
        """Calibrate predicted probabilities.

        Args:
            probs: Raw predicted probabilities [n_classes]
            method: Calibration method ('platt', 'temperature', 'beta',
                    'histogram', 'venn_abers', 'ensemble', 'adaptive')
            context: Prediction context for adaptive selection

        Returns:
            CalibrationResult with calibrated probabilities and metadata

        """
        max_prob = np.max(probs)

        if method == "adaptive":
            method = self.adaptive.get_best_method(context)

        if method == "ensemble":
            calibrated = self._ensemble_calibrate(probs)
            calibration_method = "ensemble"
        elif method == "platt":
            calibrated_max = self.platt.calibrate(np.array([max_prob]))[0]
            calibrated = self._rescale_probs(probs, calibrated_max)
            calibration_method = "platt"
        elif method == "temperature":
            logits = np.log(probs + 1e-10) - np.log(1 - probs + 1e-10)
            calibrated = self.temperature.calibrate(logits.reshape(1, -1))[0]
            calibration_method = "temperature"
        elif method == "beta":
            calibrated_max = self.beta.calibrate(np.array([max_prob]))[0]
            calibrated = self._rescale_probs(probs, calibrated_max)
            calibration_method = "beta"
        elif method == "histogram":
            calibrated_max = self.histogram.calibrate(np.array([max_prob]))[0]
            calibrated = self._rescale_probs(probs, calibrated_max)
            calibration_method = "histogram"
        else:
            calibrated = probs
            calibration_method = "none"

        # Get conformal prediction set
        pred_set, coverage = self.conformal.get_prediction_set(calibrated)

        # Get Venn-ABERS interval for uncertainty
        lower, upper = self.venn_abers.calibrate(np.max(calibrated))
        uncertainty = (upper - lower) / 2

        # Calculate reliability score
        reliability = self._calculate_reliability(calibrated, pred_set, uncertainty)

        return CalibrationResult(
            calibrated_probs=calibrated,
            confidence=float(np.max(calibrated)),
            prediction_set=pred_set,
            coverage_guarantee=coverage,
            calibration_method=calibration_method,
            uncertainty=uncertainty,
            reliability_score=reliability,
        )

    def _ensemble_calibrate(self, probs: np.ndarray) -> np.ndarray:
        """Ensemble calibration combining multiple methods"""
        max_prob = np.max(probs)

        calibrated_values = []

        # Get calibrated values from each method
        if self.platt.is_fitted:
            calibrated_values.append(self.platt.calibrate(np.array([max_prob]))[0])

        if self.beta.is_fitted:
            calibrated_values.append(self.beta.calibrate(np.array([max_prob]))[0])

        if self.histogram.is_fitted:
            calibrated_values.append(self.histogram.calibrate(np.array([max_prob]))[0])

        if not calibrated_values:
            return probs

        # Average calibrated max probability
        ensemble_max = np.mean(calibrated_values)

        return self._rescale_probs(probs, ensemble_max)

    def _rescale_probs(self, probs: np.ndarray, new_max: float) -> np.ndarray:
        """Rescale probabilities to have a new maximum while preserving relative ratios"""
        old_max = np.max(probs)
        if old_max == 0:
            return probs

        # Scale factor for max probability
        scale = new_max / old_max

        # Apply scaling
        scaled = probs * scale

        # Renormalize to sum to 1
        return scaled / np.sum(scaled)

    def _calculate_reliability(
        self, probs: np.ndarray, pred_set: list[int], uncertainty: float,
    ) -> float:
        """Calculate reliability score based on calibration quality"""
        # Higher confidence = higher reliability (up to a point)
        confidence_factor = min(np.max(probs), 0.9)

        # Smaller prediction set = higher reliability
        set_factor = 1.0 / len(pred_set)

        # Lower uncertainty = higher reliability
        uncertainty_factor = 1.0 - min(uncertainty, 0.5)

        # Combine factors
        reliability = (confidence_factor + set_factor + uncertainty_factor) / 3

        return float(reliability)

    def get_calibration_metrics(
        self, probs: np.ndarray = None, labels: np.ndarray = None,
    ) -> CalibrationMetrics:
        """Calculate calibration quality metrics.

        Args:
            probs: Predicted probabilities (optional, uses stored data if None)
            labels: True labels (optional)

        Returns:
            CalibrationMetrics with ECE, MCE, Brier score, etc.

        """
        if probs is None:
            if not self.calibration_data["probs"]:
                return CalibrationMetrics(
                    expected_calibration_error=0.0,
                    maximum_calibration_error=0.0,
                    brier_score=0.0,
                    log_loss=0.0,
                    reliability_diagram={
                        "bins": [],
                        "accuracies": [],
                        "confidences": [],
                    },
                    sharpness=0.0,
                )
            probs = np.array(self.calibration_data["probs"])
            labels = np.array(self.calibration_data["labels"])

        n_bins = 10

        # Get max probabilities and predicted classes
        max_probs = np.max(probs, axis=1)
        predicted = np.argmax(probs, axis=1)
        correct = (predicted == labels).astype(float)

        # Calculate ECE and MCE
        bin_edges = np.linspace(0, 1, n_bins + 1)
        ece = 0.0
        mce = 0.0

        bin_accuracies = []
        bin_confidences = []
        bin_counts = []

        for i in range(n_bins):
            mask = (max_probs >= bin_edges[i]) & (max_probs < bin_edges[i + 1])
            count = np.sum(mask)

            if count > 0:
                bin_acc = np.mean(correct[mask])
                bin_conf = np.mean(max_probs[mask])

                bin_accuracies.append(bin_acc)
                bin_confidences.append(bin_conf)
                bin_counts.append(count)

                calibration_error = np.abs(bin_acc - bin_conf)
                ece += calibration_error * count
                mce = max(mce, calibration_error)
            else:
                bin_accuracies.append(0.0)
                bin_confidences.append(0.0)
                bin_counts.append(0)

        n_samples = len(labels)
        ece = ece / n_samples if n_samples > 0 else 0.0

        # Brier score
        one_hot = np.zeros_like(probs)
        one_hot[np.arange(len(labels)), labels.astype(int)] = 1
        brier_score = np.mean(np.sum((probs - one_hot) ** 2, axis=1))

        # Log loss
        clipped_probs = np.clip(probs, 1e-10, 1.0)
        log_loss = -np.mean(
            np.log(clipped_probs[np.arange(len(labels)), labels.astype(int)]),
        )

        # Sharpness (average max probability)
        sharpness = 1.0 - np.mean(max_probs)

        return CalibrationMetrics(
            expected_calibration_error=float(ece),
            maximum_calibration_error=float(mce),
            brier_score=float(brier_score),
            log_loss=float(log_loss),
            reliability_diagram={
                "bins": [(bin_edges[i] + bin_edges[i + 1]) / 2 for i in range(n_bins)],
                "accuracies": bin_accuracies,
                "confidences": bin_confidences,
                "counts": bin_counts,
            },
            sharpness=float(sharpness),
        )

    def _save_calibration(self):
        """Save calibration state to disk"""

        # Convert numpy types to Python native types for JSON serialization
        def convert_to_native(obj):
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            if isinstance(obj, (np.integer, np.int64, np.int32)):
                return int(obj)
            if isinstance(obj, (np.floating, np.float64, np.float32)):
                return float(obj)
            if isinstance(obj, list):
                return [convert_to_native(item) for item in obj]
            if isinstance(obj, dict):
                return {k: convert_to_native(v) for k, v in obj.items()}
            return obj

        state = {
            "platt": {
                "A": float(self.platt.A),
                "B": float(self.platt.B),
                "fitted": self.platt.is_fitted,
            },
            "temperature": {
                "T": float(self.temperature.temperature),
                "fitted": self.temperature.is_fitted,
            },
            "beta": {
                "a": float(self.beta.a),
                "b": float(self.beta.b),
                "c": float(self.beta.c),
                "fitted": self.beta.is_fitted,
            },
            "histogram": {
                "bin_edges": self.histogram.bin_edges.tolist(),
                "bin_calibrated": self.histogram.bin_calibrated.tolist(),
                "fitted": self.histogram.is_fitted,
            },
            "conformal": {
                "quantile": float(self.conformal.quantile),
                "fitted": self.conformal.is_fitted,
            },
            "calibration_data": convert_to_native(self.calibration_data),
            "adaptive_weights": self.adaptive.context_weights,
        }

        path = self.models_dir / "calibration_state.json"
        with open(path, "w") as f:
            json.dump(state, f, indent=2)

        self.logger.info(f"Saved calibration state to {path}")

    def _load_calibration(self):
        """Load calibration state from disk"""
        path = self.models_dir / "calibration_state.json"

        if not path.exists():
            return

        try:
            with open(path) as f:
                state = json.load(f)

            platt = state.get("platt", {})
            self.platt.A = platt.get("A", 0.0)
            self.platt.B = platt.get("B", 0.0)
            self.platt.is_fitted = platt.get("fitted", False)

            temp = state.get("temperature", {})
            self.temperature.temperature = temp.get("T", 1.0)
            self.temperature.is_fitted = temp.get("fitted", False)

            beta = state.get("beta", {})
            self.beta.a = beta.get("a", 1.0)
            self.beta.b = beta.get("b", 1.0)
            self.beta.c = beta.get("c", 1.0)
            self.beta.is_fitted = beta.get("fitted", False)

            hist = state.get("histogram", {})
            self.histogram.bin_edges = np.array(
                hist.get("bin_edges", np.linspace(0, 1, 16)),
            )
            self.histogram.bin_calibrated = np.array(
                hist.get("bin_calibrated", np.zeros(15)),
            )
            self.histogram.is_fitted = hist.get("fitted", False)

            conf = state.get("conformal", {})
            self.conformal.quantile = conf.get("quantile", 0.0)
            self.conformal.is_fitted = conf.get("fitted", False)

            self.calibration_data = state.get(
                "calibration_data", {"probs": [], "labels": [], "contexts": []},
            )
            self.adaptive.context_weights = state.get("adaptive_weights", {})

            self.logger.info("Loaded calibration state")

        except Exception as e:
            self.logger.warning(f"Failed to load calibration: {e}")


def create_calibration_manager() -> AdvancedCalibrationManager:
    """Factory function to create calibration manager"""
    return AdvancedCalibrationManager()


# Test the calibration system
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    manager = AdvancedCalibrationManager()

    # Generate synthetic calibration data
    np.random.seed(42)
    n_samples = 200

    # Simulate overconfident predictions
    true_probs = np.random.beta(2, 2, n_samples)
    predicted_probs = np.clip(true_probs * 1.3, 0, 0.99)  # Overconfident
    labels = (np.random.random(n_samples) < true_probs).astype(int)

    # Convert to 3-class format
    probs_3class = np.zeros((n_samples, 3))
    for i in range(n_samples):
        p = predicted_probs[i]
        probs_3class[i, 2] = p  # Home win
        probs_3class[i, 1] = (1 - p) * 0.4  # Draw
        probs_3class[i, 0] = (1 - p) * 0.6  # Away win

    # Add samples
    for i in range(n_samples):
        manager.add_sample(probs_3class[i], labels[i] * 2, "test")  # 0 or 2

    # Fit calibrators
    manager.fit_all(min_samples=50)

    # Test calibration
    test_probs = np.array([0.65, 0.20, 0.15])  # Overconfident home win

    result = manager.calibrate(test_probs, method="ensemble")

    print("\n📊 Advanced Calibration Result:")
    print(f"   Original probs:    {test_probs}")
    print(f"   Calibrated probs:  {result.calibrated_probs}")
    print(f"   Confidence:        {result.confidence:.1%}")
    print(f"   Prediction Set:    {result.prediction_set}")
    print(f"   Coverage:          {result.coverage_guarantee:.1%}")
    print(f"   Uncertainty:       {result.uncertainty:.4f}")
    print(f"   Reliability:       {result.reliability_score:.4f}")
    print(f"   Method:            {result.calibration_method}")

    # Get calibration metrics
    metrics = manager.get_calibration_metrics()
    print("\n📈 Calibration Metrics:")
    print(f"   ECE: {metrics.expected_calibration_error:.4f}")
    print(f"   MCE: {metrics.maximum_calibration_error:.4f}")
    print(f"   Brier Score: {metrics.brier_score:.4f}")
    print(f"   Log Loss: {metrics.log_loss:.4f}")
    print(f"   Sharpness: {metrics.sharpness:.4f}")
