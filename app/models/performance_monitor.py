"""
Performance Monitoring System - Phase 4

Real-time tracking of prediction performance with automatic adjustment suggestions
Monitors confidence accuracy, recalibration triggers, and performance trends
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import numpy as np
from collections import defaultdict, deque


class PerformanceMonitor:
    """Monitors prediction performance and triggers recalibration when needed"""

    def __init__(
        self, cache_dir: str = "data/cache", lookback_windows: List[int] = None
    ):
        """
        Initialize performance monitor

        Args:
            cache_dir: Directory for performance data persistence
            lookback_windows: Windows (in matches) to track: [10, 50, 100]
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.lookback_windows = lookback_windows or [10, 50, 100]
        self.logger = logging.getLogger(__name__)

        # Performance tracking
        self.predictions: deque = deque(maxlen=500)  # Keep last 500 predictions
        self.league_performance: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                "total_predictions": 0,
                "correct_predictions": 0,
                "confidence_scores": deque(maxlen=100),
                "accuracies_by_window": {},
                "calibration_error": 0.0,
                "drift_detected": False,
                "last_recalibration": None,
            }
        )

        # ECE (Expected Calibration Error) tracking
        self.ece_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=50))

        # Drift detection thresholds
        self.drift_threshold = 0.05  # 5% drift triggers alert
        self.recalibration_threshold = 10  # Recalibrate after 10% ECE increase

        self._load_performance_history()

    def record_prediction(self, league: str, prediction: Dict[str, Any]) -> None:
        """
        Record a prediction for performance tracking

        Args:
            league: League name
            prediction: Prediction dict with 'confidence', 'outcome', 'timestamp'
        """
        try:
            timestamp = datetime.now()

            record = {
                "league": league,
                "confidence": prediction.get("confidence", 0.0),
                "outcome": prediction.get(
                    "outcome"
                ),  # 0.0 (away win) to 1.0 (home win)
                "timestamp": timestamp.isoformat(),
                "match_id": prediction.get("match_id", ""),
            }

            self.predictions.append(record)

            # Update league statistics
            league_stats = self.league_performance[league]
            league_stats["total_predictions"] += 1

            # Check if outcome matches prediction
            if record["outcome"] is not None:
                is_correct = self._check_prediction_correctness(
                    record["confidence"], record["outcome"]
                )
                if is_correct:
                    league_stats["correct_predictions"] += 1

                # Track confidence for ECE calculation
                league_stats["confidence_scores"].append(
                    {
                        "confidence": record["confidence"],
                        "outcome": record["outcome"],
                        "timestamp": timestamp.isoformat(),
                    }
                )

        except Exception as e:
            self.logger.warning(f"Error recording prediction: {e}")

    def get_performance_summary(self, league: Optional[str] = None) -> Dict[str, Any]:
        """
        Get performance summary for league or all leagues

        Args:
            league: Specific league or None for all

        Returns:
            Performance metrics
        """
        if league:
            return self._get_league_performance(league)
        else:
            return self._get_all_leagues_performance()

    def _get_league_performance(self, league: str) -> Dict[str, Any]:
        """Get performance metrics for a specific league"""
        stats = self.league_performance.get(league, {})

        if stats.get("total_predictions", 0) == 0:
            return {
                "league": league,
                "status": "no_data",
                "message": "No predictions recorded yet",
            }

        accuracy = (
            stats["correct_predictions"] / stats["total_predictions"]
            if stats["total_predictions"] > 0
            else 0.0
        )

        # Calculate ECE
        ece = self._calculate_ece(league)

        # Window-based accuracies
        window_accuracies = {}
        for window in self.lookback_windows:
            recent = self._get_recent_predictions(league, window)
            if recent:
                correct = sum(
                    1
                    for p in recent
                    if self._check_prediction_correctness(p["confidence"], p["outcome"])
                )
                window_accuracies[f"last_{window}"] = correct / len(recent)

        return {
            "league": league,
            "total_predictions": stats["total_predictions"],
            "overall_accuracy": accuracy,
            "expected_calibration_error": ece,
            "window_accuracies": window_accuracies,
            "recalibration_needed": ece > self.recalibration_threshold,
            "drift_detected": stats["drift_detected"],
            "last_recalibration": stats.get("last_recalibration"),
        }

    def _get_all_leagues_performance(self) -> Dict[str, Any]:
        """Get performance summary for all leagues"""
        return {
            "leagues": {
                league: self._get_league_performance(league)
                for league in self.league_performance.keys()
            },
            "timestamp": datetime.now().isoformat(),
        }

    def _calculate_ece(self, league: str) -> float:
        """
        Calculate Expected Calibration Error (ECE)

        Expected Calibration Error measures how well predicted probabilities
        match actual outcomes
        """
        try:
            scores = list(self.league_performance[league]["confidence_scores"])
            if len(scores) < 10:
                return 0.0

            # Bin predictions into confidence buckets
            bins = defaultdict(list)
            for score in scores:
                confidence = score["confidence"]
                outcome = score["outcome"]

                # Determine bin (0-10%, 10-20%, etc.)
                bin_idx = min(int(confidence * 10), 9)
                bins[bin_idx].append(outcome)

            # Calculate ECE as weighted average of bin errors
            ece = 0.0
            total = len(scores)

            for bin_idx, outcomes in bins.items():
                if len(outcomes) == 0:
                    continue

                bin_confidence = (bin_idx + 0.5) / 10.0  # Center of bin
                bin_accuracy = np.mean(outcomes)
                bin_error = abs(bin_confidence - bin_accuracy)
                bin_weight = len(outcomes) / total

                ece += bin_weight * bin_error

            return ece

        except Exception as e:
            self.logger.warning(f"Error calculating ECE: {e}")
            return 0.0

    def detect_performance_drift(self, league: str, window: int = 50) -> Dict[str, Any]:
        """
        Detect if prediction performance is drifting

        Drift suggests the model may need recalibration

        Args:
            league: League name
            window: Number of recent predictions to check

        Returns:
            Drift analysis with alert if needed
        """
        recent = self._get_recent_predictions(league, window)

        if len(recent) < 20:
            return {"status": "insufficient_data", "samples": len(recent)}

        # Calculate accuracy trends
        first_half = recent[: len(recent) // 2]
        second_half = recent[len(recent) // 2 :]

        first_accuracy = self._calculate_accuracy(first_half)
        second_accuracy = self._calculate_accuracy(second_half)

        drift_magnitude = abs(second_accuracy - first_accuracy)

        result = {
            "league": league,
            "window": window,
            "first_half_accuracy": first_accuracy,
            "second_half_accuracy": second_accuracy,
            "drift_magnitude": drift_magnitude,
            "drift_detected": drift_magnitude > self.drift_threshold,
            "recommendation": self._get_drift_recommendation(
                drift_magnitude, second_accuracy
            ),
        }

        # Update league stats
        self.league_performance[league]["drift_detected"] = result["drift_detected"]

        return result

    def suggest_recalibration_actions(self, league: str) -> List[str]:
        """
        Suggest actions for recalibration

        Args:
            league: League name

        Returns:
            List of recommended actions
        """
        stats = self._get_league_performance(league)

        if stats.get("status") == "no_data":
            return ["Insufficient data: Continue collecting predictions"]

        actions = []

        # Check ECE (convert to proper threshold)
        if stats.get("expected_calibration_error", 0.0) > 0.10:
            actions.append(
                "High calibration error: Run isotonic regression recalibration"
            )

        # Check accuracy by window
        window_accs = stats.get("window_accuracies", {})
        if window_accs:
            recent_acc = window_accs.get("last_10", 0.0)
            if recent_acc < 0.45:
                actions.append(
                    "Recent accuracy dropping: Review model weights and thresholds"
                )

        # Check drift
        drift = self.detect_performance_drift(league)
        if drift.get("drift_detected"):
            actions.append(f"Performance drift detected: {drift['recommendation']}")

        # Check data freshness
        if stats.get("total_predictions", 0) < 20:
            actions.append(
                "Insufficient historical data: Continue collecting predictions"
            )

        return actions if actions else ["System performing well, no action needed"]

    def _get_recent_predictions(self, league: str, count: int) -> List[Dict]:
        """Get recent predictions for a league"""
        league_preds = [p for p in self.predictions if p.get("league") == league]
        return league_preds[-count:] if league_preds else []

    def _check_prediction_correctness(self, confidence: float, outcome: float) -> bool:
        """
        Check if prediction was correct

        confidence: 0.0 to 1.0 (0=away win, 0.5=draw, 1.0=home win)
        outcome: 0.0 to 1.0 (actual result)
        """
        if outcome is None:
            return False

        # Prediction is correct if confidence matches outcome
        # (simplified: if confidence > 0.5, predict home win, etc.)
        prediction = confidence > 0.5
        actual = outcome > 0.5

        return prediction == actual

    def _calculate_accuracy(self, predictions: List[Dict]) -> float:
        """Calculate accuracy from prediction list"""
        if not predictions:
            return 0.0

        correct = sum(
            1
            for p in predictions
            if self._check_prediction_correctness(p["confidence"], p["outcome"])
        )
        return correct / len(predictions)

    def _get_drift_recommendation(self, drift_magnitude: float, accuracy: float) -> str:
        """Get recommendation based on drift and accuracy"""
        if drift_magnitude > 0.15:
            return "Significant drift detected - consider full model retraining"
        elif drift_magnitude > 0.10:
            return "Moderate drift - update calibration and weights"
        elif accuracy < 0.45:
            return "Low accuracy period - check data quality and feature freshness"
        else:
            return "Minor drift - monitor closely, recalibrate if continues"

    def save_performance_history(self) -> None:
        """Save performance history to disk"""
        try:
            history_file = self.cache_dir / "performance_history.json"

            data = {"recorded_at": datetime.now().isoformat(), "league_performance": {}}

            # Convert deques to lists for JSON serialization
            for league, stats in self.league_performance.items():
                data["league_performance"][league] = {
                    "total_predictions": stats["total_predictions"],
                    "correct_predictions": stats["correct_predictions"],
                    "confidence_scores": list(stats["confidence_scores"]),
                    "drift_detected": stats["drift_detected"],
                    "last_recalibration": stats.get("last_recalibration"),
                }

            with open(history_file, "w") as f:
                json.dump(data, f, indent=2)

            self.logger.debug(f"Performance history saved to {history_file}")

        except Exception as e:
            self.logger.warning(f"Error saving performance history: {e}")

    def _load_performance_history(self) -> None:
        """Load performance history from disk"""
        try:
            history_file = self.cache_dir / "performance_history.json"

            if not history_file.exists():
                self.logger.debug("No performance history found, starting fresh")
                return

            with open(history_file, "r") as f:
                data = json.load(f)

            # Restore league performance
            for league, stats in data.get("league_performance", {}).items():
                self.league_performance[league] = {
                    "total_predictions": stats["total_predictions"],
                    "correct_predictions": stats["correct_predictions"],
                    "confidence_scores": deque(
                        stats.get("confidence_scores", []), maxlen=100
                    ),
                    "drift_detected": stats.get("drift_detected", False),
                    "last_recalibration": stats.get("last_recalibration"),
                }

            self.logger.debug(
                f"Loaded performance history for {len(self.league_performance)} leagues"
            )

        except Exception as e:
            self.logger.warning(f"Error loading performance history: {e}")

    def generate_performance_report(self, league: Optional[str] = None) -> str:
        """
        Generate human-readable performance report

        Args:
            league: Specific league or None for all

        Returns:
            Formatted report string
        """
        report = []
        report.append("=" * 60)
        report.append("PERFORMANCE MONITORING REPORT")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("=" * 60)

        if league:
            performance = self._get_league_performance(league)
            report.extend(self._format_league_report(league, performance))

            actions = self.suggest_recalibration_actions(league)
            report.append("\nRECOMMENDED ACTIONS:")
            for action in actions:
                report.append(f"  • {action}")

        else:
            for league_name in sorted(self.league_performance.keys()):
                perf = self._get_league_performance(league_name)
                report.extend(self._format_league_report(league_name, perf))
                report.append("")

        report.append("=" * 60)
        return "\n".join(report)

    def _format_league_report(self, league: str, performance: Dict) -> List[str]:
        """Format league report lines"""
        lines = []
        league_display = league.replace("-", " ").upper()
        lines.append(f"\n{league_display}")
        lines.append("-" * 40)
        lines.append(f"  Total Predictions: {performance.get('total_predictions', 0)}")
        lines.append(
            f"  Overall Accuracy: {performance.get('overall_accuracy', 0):.1%}"
        )
        lines.append(
            f"  Calibration Error: {performance.get('expected_calibration_error', 0):.4f}"
        )

        windows = performance.get("window_accuracies", {})
        if windows:
            lines.append("  Accuracy by Window:")
            for window, accuracy in sorted(windows.items()):
                lines.append(f"    {window}: {accuracy:.1%}")

        if performance.get("drift_detected"):
            lines.append("  ⚠️  DRIFT DETECTED - Recalibration recommended")

        return lines
