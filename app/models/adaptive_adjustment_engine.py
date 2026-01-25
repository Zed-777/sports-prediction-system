"""
Adaptive Adjustment Engine - Phase 4

Automatically adjusts model parameters based on performance monitoring
Implements learning feedback loops for continuous improvement
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import numpy as np


class AdaptiveAdjustmentEngine:
    """Automatically adjusts confidence levels and weights based on performance"""

    def __init__(self, cache_dir: str = "data/cache"):
        """
        Initialize adaptive adjustment engine

        Args:
            cache_dir: Directory for adjustment history
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.logger = logging.getLogger(__name__)

        # Adjustment history per league
        self.adjustment_history: Dict[str, List[Dict]] = {}

        # Current adjustments
        self.current_adjustments: Dict[str, Dict[str, float]] = {}

        # Learning rate controls how aggressively we adjust
        self.learning_rate = 0.1

        # Bounds to prevent runaway adjustments
        self.min_adjustment = 0.85  # Don't reduce confidence below 85%
        self.max_adjustment = 1.15  # Don't boost confidence above 115%

        self._load_adjustment_history()

    def suggest_confidence_adjustment(
        self,
        league: str,
        accuracy: float,
        target_accuracy: float = 0.65,
        recent_window_size: int = 10,
    ) -> float:
        """
        Suggest confidence adjustment based on accuracy drift

        Args:
            league: League name
            accuracy: Current accuracy (0.0 to 1.0)
            target_accuracy: Target accuracy to aim for
            recent_window_size: Window for recent accuracy

        Returns:
            Adjustment multiplier (0.85 to 1.15)
        """
        error = target_accuracy - accuracy

        if abs(error) < 0.02:
            # Within 2% of target, minimal adjustment
            adjustment = 1.0
        else:
            # Scale adjustment based on error magnitude
            # Negative error (accuracy too high) → reduce confidence
            # Positive error (accuracy too low) → boost confidence
            adjustment = 1.0 + (error * self.learning_rate)

        # Clamp adjustment
        adjustment = np.clip(adjustment, self.min_adjustment, self.max_adjustment)

        # Record adjustment
        self._record_adjustment(
            league,
            {
                "timestamp": datetime.now().isoformat(),
                "type": "confidence_adjustment",
                "accuracy": accuracy,
                "target": target_accuracy,
                "adjustment": adjustment,
                "error": error,
            },
        )

        return adjustment

    def suggest_weight_adjustments(
        self,
        league: str,
        model_accuracies: Dict[str, float],
        target_accuracy: float = 0.65,
    ) -> Dict[str, float]:
        """
        Suggest weight adjustments for ensemble models

        Args:
            league: League name
            model_accuracies: Dict of model_name -> accuracy
            target_accuracy: Target accuracy

        Returns:
            Dict of model_name -> weight_multiplier
        """
        adjustments = {}

        for model, accuracy in model_accuracies.items():
            error = target_accuracy - accuracy

            if abs(error) < 0.02:
                adjustment = 1.0
            else:
                # Models with higher accuracy get higher weight
                adjustment = 1.0 + (
                    error * self.learning_rate * 0.5
                )  # More conservative

            adjustment = np.clip(adjustment, self.min_adjustment, self.max_adjustment)
            adjustments[model] = adjustment

        # Normalize so they sum to number of models
        total = sum(adjustments.values())
        if total > 0:
            adjustments = {
                m: (w * len(adjustments) / total) for m, w in adjustments.items()
            }

        # Record adjustment
        self._record_adjustment(
            league,
            {
                "timestamp": datetime.now().isoformat(),
                "type": "weight_adjustment",
                "model_accuracies": model_accuracies,
                "adjustments": adjustments,
            },
        )

        return adjustments

    def suggest_calibration_adjustment(
        self, league: str, ece: float, target_ece: float = 0.03
    ) -> Dict[str, Any]:
        """
        Suggest calibration adjustments

        Args:
            league: League name
            ece: Expected Calibration Error
            target_ece: Target ECE

        Returns:
            Calibration adjustment recommendations
        """
        ece_error = ece - target_ece

        recommendations = {
            "league": league,
            "current_ece": ece,
            "target_ece": target_ece,
            "ece_error": ece_error,
            "actions": [],
        }

        if ece > target_ece * 1.5:
            recommendations["actions"].append(
                {
                    "severity": "high",
                    "action": "Run full isotonic regression recalibration",
                    "reason": "ECE significantly above target",
                }
            )
        elif ece > target_ece:
            recommendations["actions"].append(
                {
                    "severity": "medium",
                    "action": "Update calibration with recent predictions",
                    "reason": "ECE above target, incremental adjustment recommended",
                }
            )
        else:
            recommendations["actions"].append(
                {
                    "severity": "low",
                    "action": "Monitor calibration, maintain current state",
                    "reason": "ECE within acceptable range",
                }
            )

        # Record adjustment
        self._record_adjustment(
            league,
            {
                "timestamp": datetime.now().isoformat(),
                "type": "calibration_adjustment",
                "ece": ece,
                "recommendations": recommendations,
            },
        )

        return recommendations

    def suggest_threshold_adjustments(
        self,
        league: str,
        precision_recall: Dict[str, float],
        current_threshold: float = 0.5,
    ) -> Dict[str, Any]:
        """
        Suggest decision threshold adjustments

        Args:
            league: League name
            precision_recall: Dict with 'precision' and 'recall'
            current_threshold: Current classification threshold

        Returns:
            Threshold adjustment recommendations
        """
        precision = precision_recall.get("precision", 0.5)
        recall = precision_recall.get("recall", 0.5)

        f1_score = 2 * (precision * recall) / (precision + recall + 1e-10)

        recommendations = {
            "league": league,
            "current_threshold": current_threshold,
            "current_precision": precision,
            "current_recall": recall,
            "f1_score": f1_score,
            "suggested_threshold": current_threshold,
            "reasoning": "",
        }

        # Recommend threshold adjustment based on precision/recall balance
        if precision > recall + 0.1:
            # Too conservative (precision high, recall low)
            recommendations["suggested_threshold"] = current_threshold - 0.05
            recommendations["reasoning"] = "Lower threshold to improve recall"
        elif recall > precision + 0.1:
            # Too aggressive (recall high, precision low)
            recommendations["suggested_threshold"] = current_threshold + 0.05
            recommendations["reasoning"] = "Raise threshold to improve precision"
        else:
            recommendations["reasoning"] = "Threshold is well-balanced"

        recommendations["suggested_threshold"] = np.clip(
            recommendations["suggested_threshold"], 0.3, 0.7
        )

        # Record adjustment
        self._record_adjustment(
            league,
            {
                "timestamp": datetime.now().isoformat(),
                "type": "threshold_adjustment",
                "recommendations": recommendations,
            },
        )

        return recommendations

    def get_adjustment_status(self, league: str) -> Dict[str, Any]:
        """
        Get current adjustment status for a league

        Args:
            league: League name

        Returns:
            Current adjustment state
        """
        history = self.adjustment_history.get(league, [])

        if not history:
            return {
                "league": league,
                "status": "no_adjustments",
                "message": "No adjustments recorded for this league",
            }

        # Get most recent adjustment of each type
        latest_by_type = {}
        for adjustment in reversed(history):
            adj_type = adjustment.get("type")
            if adj_type not in latest_by_type:
                latest_by_type[adj_type] = adjustment

        return {
            "league": league,
            "total_adjustments": len(history),
            "latest_adjustments": latest_by_type,
            "timestamp": datetime.now().isoformat(),
        }

    def get_adjustment_recommendations_summary(self) -> str:
        """
        Get summary of all adjustment recommendations

        Returns:
            Formatted recommendation summary
        """
        summary = []
        summary.append("=" * 70)
        summary.append("ADAPTIVE ADJUSTMENT ENGINE - RECOMMENDATIONS SUMMARY")
        summary.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        summary.append("=" * 70)

        for league in sorted(self.adjustment_history.keys()):
            status = self.get_adjustment_status(league)
            summary.append(f"\n{league.upper()}")
            summary.append("-" * 50)
            summary.append(f"Total Adjustments Made: {status['total_adjustments']}")

            latest = status.get("latest_adjustments", {})
            if latest:
                for adj_type, adj_data in sorted(latest.items()):
                    summary.append(f"\n  Latest {adj_type.replace('_', ' ').title()}:")
                    summary.append(f"    Timestamp: {adj_data.get('timestamp', 'N/A')}")
                    if "adjustment" in adj_data:
                        summary.append(
                            f"    Adjustment Factor: {adj_data['adjustment']:.4f}"
                        )
                    if "reasoning" in adj_data:
                        summary.append(f"    Reasoning: {adj_data['reasoning']}")

        summary.append("\n" + "=" * 70)
        return "\n".join(summary)

    def _record_adjustment(self, league: str, adjustment: Dict) -> None:
        """Record an adjustment for history tracking"""
        if league not in self.adjustment_history:
            self.adjustment_history[league] = []

        self.adjustment_history[league].append(adjustment)
        self.logger.debug(f"Recorded {adjustment.get('type', 'unknown')} for {league}")

    def save_adjustment_history(self) -> None:
        """Save adjustment history to disk"""
        try:
            history_file = self.cache_dir / "adjustment_history.json"

            data = {
                "recorded_at": datetime.now().isoformat(),
                "adjustments": self.adjustment_history,
            }

            with open(history_file, "w") as f:
                json.dump(data, f, indent=2, default=str)

            self.logger.debug(f"Adjustment history saved to {history_file}")

        except Exception as e:
            self.logger.warning(f"Error saving adjustment history: {e}")

    def _load_adjustment_history(self) -> None:
        """Load adjustment history from disk"""
        try:
            history_file = self.cache_dir / "adjustment_history.json"

            if not history_file.exists():
                self.logger.debug("No adjustment history found, starting fresh")
                return

            with open(history_file, "r") as f:
                data = json.load(f)

            self.adjustment_history = data.get("adjustments", {})
            self.logger.debug(
                f"Loaded adjustment history for {len(self.adjustment_history)} leagues"
            )

        except Exception as e:
            self.logger.warning(f"Error loading adjustment history: {e}")


class LearningFeedbackLoop:
    """Manages feedback loops for continuous learning"""

    def __init__(
        self, performance_monitor, adjustment_engine, cache_dir: str = "data/cache"
    ):
        """
        Initialize feedback loop

        Args:
            performance_monitor: PerformanceMonitor instance
            adjustment_engine: AdaptiveAdjustmentEngine instance
            cache_dir: Cache directory
        """
        self.performance_monitor = performance_monitor
        self.adjustment_engine = adjustment_engine
        self.cache_dir = Path(cache_dir)
        self.logger = logging.getLogger(__name__)

        self.feedback_history: Dict[str, List[Dict]] = {}

    def run_feedback_cycle(
        self, league: str, model_accuracies: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Run a complete feedback cycle for a league

        Args:
            league: League name
            model_accuracies: Dict of model accuracies (optional)

        Returns:
            Feedback cycle results
        """
        results = {
            "league": league,
            "timestamp": datetime.now().isoformat(),
            "recommendations": [],
        }

        # Get performance summary
        perf = self.performance_monitor.get_performance_summary(league)

        if perf.get("status") == "no_data":
            results["status"] = "insufficient_data"
            return results

        accuracy = perf.get("overall_accuracy", 0.5)
        ece = perf.get("expected_calibration_error", 0.0)

        # Suggest confidence adjustment
        conf_adj = self.adjustment_engine.suggest_confidence_adjustment(
            league, accuracy
        )
        results["confidence_adjustment"] = conf_adj

        if conf_adj != 1.0:
            results["recommendations"].append(
                f"Adjust confidence by {(conf_adj - 1) * 100:+.1f}% based on accuracy"
            )

        # Suggest weight adjustments if model accuracies provided
        if model_accuracies:
            weight_adj = self.adjustment_engine.suggest_weight_adjustments(
                league, model_accuracies
            )
            results["weight_adjustments"] = weight_adj
            results["recommendations"].append("Update ensemble model weights")

        # Suggest calibration adjustment
        cal_adj = self.adjustment_engine.suggest_calibration_adjustment(league, ece)
        if cal_adj["actions"]:
            action = cal_adj["actions"][0]
            if action["severity"] != "low":
                results["recommendations"].append(action["action"])

        # Detect drift
        drift = self.performance_monitor.detect_performance_drift(league)
        if drift.get("drift_detected"):
            results["recommendations"].append(
                drift.get("recommendation", "Monitor drift")
            )

        # Record feedback cycle
        if league not in self.feedback_history:
            self.feedback_history[league] = []

        self.feedback_history[league].append(results)

        return results

    def get_feedback_report(self, league: Optional[str] = None) -> str:
        """
        Get feedback loop report

        Args:
            league: Specific league or None for all

        Returns:
            Formatted report
        """
        report = []
        report.append("=" * 70)
        report.append("LEARNING FEEDBACK LOOP REPORT")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("=" * 70)

        if league:
            cycles = self.feedback_history.get(league, [])
            if cycles:
                latest = cycles[-1]
                league_display = league.replace("-", " ").upper()
                report.append(f"\n{league_display}")
                report.append("-" * 50)
                report.append(f"Latest Cycle: {latest.get('timestamp', 'N/A')}")
                report.append(f"Status: {latest.get('status', 'complete')}")

                if latest.get("confidence_adjustment"):
                    adj = latest["confidence_adjustment"]
                    report.append(f"Confidence Adjustment: {(adj - 1) * 100:+.1f}%")

                if latest.get("recommendations"):
                    report.append("Recommendations:")
                    for rec in latest["recommendations"]:
                        report.append(f"  • {rec}")
        else:
            for league_name in sorted(self.feedback_history.keys()):
                cycles = self.feedback_history[league_name]
                if cycles:
                    latest = cycles[-1]
                    league_display = league_name.replace("-", " ").upper()
                    report.append(f"\n{league_display}")
                    report.append("-" * 40)
                    report.append(f"Cycles Completed: {len(cycles)}")
                    report.append(f"Latest: {latest.get('timestamp', 'N/A')}")

        report.append("\n" + "=" * 70)
        return "\n".join(report)

    def save_feedback_history(self) -> None:
        """Save feedback history to disk"""
        try:
            history_file = self.cache_dir / "feedback_history.json"

            data = {
                "recorded_at": datetime.now().isoformat(),
                "feedback": self.feedback_history,
            }

            with open(history_file, "w") as f:
                json.dump(data, f, indent=2, default=str)

            self.logger.debug(f"Feedback history saved to {history_file}")

        except Exception as e:
            self.logger.warning(f"Error saving feedback history: {e}")
