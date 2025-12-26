"""
Phase 4: Real-Time Performance Monitoring & Drift Detection

Tracks live prediction performance, detects statistical drift, and maintains
per-league and per-model performance baselines for continuous system optimization.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from collections import deque
import statistics


class PerformanceMonitor:
    """
    Real-time performance tracking with drift detection and performance alerting.

    Monitors:
    - Per-league accuracy and calibration
    - Per-model accuracy and reliability
    - Overall system drift detection
    - Confidence distribution changes
    """

    def __init__(self, cache_dir: str = "data/cache", window_size: int = 50):
        """
        Initialize performance monitor.

        Args:
            cache_dir: Directory for persistence
            window_size: Number of recent matches to track (for drift detection)
        """
        self.cache_dir = cache_dir
        self.window_size = window_size

        # Per-league performance tracking
        self.league_performance = {}  # {league: {'accuracy': float, 'calibration_error': float, 'samples': int}}
        self.league_windows = {}  # {league: deque of (prediction, outcome) tuples}

        # Per-model performance tracking
        self.model_performance = {}  # {model: {'accuracy': float, 'samples': int}}
        self.model_windows = {}  # {model: deque of (prediction, outcome) tuples}

        # Overall system metrics
        self.system_metrics = {
            "total_predictions": 0,
            "overall_accuracy": 0.0,
            "overall_calibration_error": 0.0,
            "average_confidence": 0.0,
            "confidence_std": 0.0,
            "drift_detected": False,
            "drift_severity": 0.0,  # 0.0 = no drift, 1.0 = severe drift
        }

        # Historical baselines for drift comparison
        self.baselines = {
            "accuracy": 0.65,  # Baseline accuracy (from Phase 3 target)
            "calibration": 0.08,  # Baseline calibration error (ECE)
            "confidence": 0.68,  # Baseline average confidence
        }

        # Drift detection thresholds
        self.drift_thresholds = {
            "accuracy_drop": 0.05,  # Alert if accuracy drops > 5%
            "calibration_increase": 0.03,  # Alert if calibration error increases > 3%
            "confidence_shift": 0.08,  # Alert if avg confidence shifts > 8%
        }

        self._load_monitor_state()

    def record_prediction(
        self,
        league: str,
        model: str,
        confidence: float,
        outcome: float,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """
        Record a single prediction outcome for monitoring.

        Args:
            league: League identifier (e.g., 'la-liga')
            model: Model name (e.g., 'xg', 'poisson')
            confidence: Predicted confidence (0.0-1.0)
            outcome: Actual outcome (0.0 = loss, 0.5 = draw, 1.0 = win)
            timestamp: Optional timestamp (defaults to now)
        """
        timestamp = timestamp or datetime.now()

        # Initialize league tracking if needed
        if league not in self.league_performance:
            self.league_performance[league] = {
                "accuracy": 0.0,
                "calibration_error": 0.0,
                "samples": 0,
                "last_updated": timestamp.isoformat(),
            }
            self.league_windows[league] = deque(maxlen=self.window_size)

        # Initialize model tracking if needed
        if model not in self.model_performance:
            self.model_performance[model] = {
                "accuracy": 0.0,
                "samples": 0,
                "last_updated": timestamp.isoformat(),
            }
            self.model_windows[model] = deque(maxlen=self.window_size)

        # Record prediction
        is_correct = (
            1.0
            if (confidence > 0.5 and outcome > 0.5)
            or (confidence <= 0.5 and outcome <= 0.5)
            else 0.0
        )
        calibration_error = abs(confidence - outcome)

        # Update league metrics
        league_stats = self.league_performance[league]
        league_stats["accuracy"] = (
            league_stats["accuracy"] * league_stats["samples"] + is_correct
        ) / (league_stats["samples"] + 1)
        league_stats["calibration_error"] = (
            league_stats["calibration_error"] * league_stats["samples"]
            + calibration_error
        ) / (league_stats["samples"] + 1)
        league_stats["samples"] += 1
        league_stats["last_updated"] = timestamp.isoformat()
        self.league_windows[league].append((confidence, outcome))

        # Update model metrics
        model_stats = self.model_performance[model]
        model_stats["accuracy"] = (
            model_stats["accuracy"] * model_stats["samples"] + is_correct
        ) / (model_stats["samples"] + 1)
        model_stats["samples"] += 1
        model_stats["last_updated"] = timestamp.isoformat()
        self.model_windows[model].append((confidence, outcome))

        # Update system metrics
        self._update_system_metrics(confidence, is_correct, calibration_error)
        self._detect_drift()

    def _update_system_metrics(
        self, confidence: float, is_correct: float, calibration_error: float
    ) -> None:
        """Update overall system performance metrics."""
        n = self.system_metrics["total_predictions"]

        # Update overall accuracy
        self.system_metrics["overall_accuracy"] = (
            self.system_metrics["overall_accuracy"] * n + is_correct
        ) / (n + 1)

        # Update overall calibration error
        self.system_metrics["overall_calibration_error"] = (
            self.system_metrics["overall_calibration_error"] * n + calibration_error
        ) / (n + 1)

        self.system_metrics["total_predictions"] += 1

    def _detect_drift(self) -> None:
        """Detect statistical drift in system performance."""
        if self.system_metrics["total_predictions"] < 10:
            return  # Need minimum samples for drift detection

        current_accuracy = self.system_metrics["overall_accuracy"]
        current_calibration = self.system_metrics["overall_calibration_error"]

        accuracy_drop = self.baselines["accuracy"] - current_accuracy
        calibration_increase = current_calibration - self.baselines["calibration"]

        drift_score = 0.0

        # Accuracy drift component
        if accuracy_drop > self.drift_thresholds["accuracy_drop"]:
            drift_score += min(1.0, accuracy_drop / 0.1)  # Scale by severity

        # Calibration drift component
        if calibration_increase > self.drift_thresholds["calibration_increase"]:
            drift_score += min(1.0, calibration_increase / 0.06)

        # Average drift score (0.0-1.0)
        self.system_metrics["drift_severity"] = min(1.0, drift_score / 2.0)
        self.system_metrics["drift_detected"] = drift_score > 0.5

    def get_league_performance(self, league: str) -> Dict:
        """Get performance metrics for a specific league."""
        return self.league_performance.get(
            league, {"accuracy": 0.0, "calibration_error": 0.0, "samples": 0}
        )

    def get_model_performance(self, model: str) -> Dict:
        """Get performance metrics for a specific model."""
        return self.model_performance.get(model, {"accuracy": 0.0, "samples": 0})

    def get_system_metrics(self) -> Dict:
        """Get overall system performance metrics."""
        return self.system_metrics.copy()

    def get_drift_status(self) -> Tuple[bool, float]:
        """
        Get current drift detection status.

        Returns:
            (is_drifting, severity_0_to_1)
        """
        return (
            self.system_metrics["drift_detected"],
            self.system_metrics["drift_severity"],
        )

    def get_recommendations(self) -> List[str]:
        """Generate performance optimization recommendations based on current metrics."""
        recommendations = []

        # Check for accuracy drift
        accuracy_drop = (
            self.baselines["accuracy"] - self.system_metrics["overall_accuracy"]
        )
        if accuracy_drop > 0.03:
            recommendations.append(
                f"⚠️ Accuracy dropped {accuracy_drop * 100:.1f}% below baseline - recalibrate models"
            )

        # Check for calibration drift
        calibration_increase = (
            self.system_metrics["overall_calibration_error"]
            - self.baselines["calibration"]
        )
        if calibration_increase > 0.02:
            recommendations.append(
                f"⚠️ Calibration error increased {calibration_increase * 100:.1f}% - rerun isotonic regression"
            )

        # Check per-league performance
        for league, stats in self.league_performance.items():
            if stats["samples"] >= 5 and stats["accuracy"] < 0.55:
                recommendations.append(
                    f"⚠️ {league}: Low accuracy ({stats['accuracy'] * 100:.1f}%) - review league tuning"
                )

        # Check per-model performance
        for model, stats in self.model_performance.items():
            if stats["samples"] >= 5 and stats["accuracy"] < 0.50:
                recommendations.append(
                    f"⚠️ {model}: Poor performance ({stats['accuracy'] * 100:.1f}%) - consider model retraining"
                )

        if not recommendations:
            recommendations.append("✓ System performing within normal parameters")

        return recommendations

    def get_recent_window(
        self, league: str, window_size: Optional[int] = None
    ) -> List[Tuple[float, float]]:
        """
        Get recent predictions for drift analysis.

        Returns:
            List of (confidence, outcome) tuples
        """
        if league not in self.league_windows:
            return []

        window = list(self.league_windows[league])
        if window_size:
            window = window[-window_size:]

        return window

    def save_monitor_state(self) -> None:
        """Persist monitoring state to disk."""
        os.makedirs(self.cache_dir, exist_ok=True)

        state = {
            "league_performance": self.league_performance,
            "model_performance": self.model_performance,
            "system_metrics": self.system_metrics,
            "baselines": self.baselines,
            "timestamp": datetime.now().isoformat(),
        }

        filepath = os.path.join(self.cache_dir, "phase4_monitor_state.json")
        with open(filepath, "w") as f:
            json.dump(state, f, indent=2)

    def _load_monitor_state(self) -> None:
        """Load monitoring state from disk if available."""
        filepath = os.path.join(self.cache_dir, "phase4_monitor_state.json")
        if os.path.exists(filepath):
            try:
                with open(filepath, "r") as f:
                    state = json.load(f)
                    self.league_performance = state.get("league_performance", {})
                    self.model_performance = state.get("model_performance", {})
                    self.system_metrics = state.get(
                        "system_metrics", self.system_metrics
                    )
                    self.baselines = state.get("baselines", self.baselines)
            except Exception:
                pass  # Graceful fallback to defaults


class DriftAnalyzer:
    """
    Advanced drift analysis using statistical tests.
    Detects concept drift, performance degradation, and data distribution changes.
    """

    def __init__(self, reference_window_size: int = 30, test_window_size: int = 10):
        """
        Initialize drift analyzer.

        Args:
            reference_window_size: Size of reference window for comparison
            test_window_size: Size of test window for current performance
        """
        self.reference_window_size = reference_window_size
        self.test_window_size = test_window_size

    def analyze_drift(self, predictions: List[Tuple[float, float]]) -> Dict:
        """
        Analyze predictions for drift using statistical methods.

        Args:
            predictions: List of (confidence, outcome) tuples

        Returns:
            Drift analysis results
        """
        if len(predictions) < self.reference_window_size + self.test_window_size:
            return {"drift_detected": False, "test_statistic": 0.0}

        reference = predictions[
            -self.reference_window_size - self.test_window_size : -self.test_window_size
        ]
        current = predictions[-self.test_window_size :]

        # Calculate mean accuracy for each window
        ref_accuracy = sum(
            1 if (pred > 0.5) == (outcome > 0.5) else 0 for pred, outcome in reference
        ) / len(reference)
        curr_accuracy = sum(
            1 if (pred > 0.5) == (outcome > 0.5) else 0 for pred, outcome in current
        ) / len(current)

        # Simple test statistic: relative change in accuracy
        test_stat = abs(curr_accuracy - ref_accuracy) / max(ref_accuracy, 0.01)

        return {
            "drift_detected": test_stat > 0.15,  # 15% change threshold
            "test_statistic": test_stat,
            "reference_accuracy": ref_accuracy,
            "current_accuracy": curr_accuracy,
        }
