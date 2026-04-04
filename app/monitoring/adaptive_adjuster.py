"""Phase 4: Adaptive Confidence Adjustment Engine

Dynamically adjusts confidence factors based on recent performance metrics,
enabling the system to self-correct when drift is detected.
"""

import json
import os
from datetime import datetime


class AdaptiveAdjuster:
    """Dynamically adjusts confidence factors based on recent performance.

    Adapts:
    - League adjustment factors based on per-league accuracy
    - Bayesian prior parameters based on recent calibration
    - Context adjustment weights based on recent effectiveness
    - Overall confidence scaling based on drift detection
    """

    def __init__(self, cache_dir: str = "data/cache", adaptation_rate: float = 0.1):
        """Initialize adaptive adjuster.

        Args:
            cache_dir: Directory for persistence
            adaptation_rate: Rate of adaptation (0.0-1.0, higher = more aggressive)

        """
        self.cache_dir = cache_dir
        self.adaptation_rate = adaptation_rate

        # Base adjustment factors (defaults from Phase 3)
        self.league_factors = {
            "la-liga": 1.00,
            "premier-league": 1.02,
            "bundesliga": 0.98,
            "serie-a": 0.99,
            "ligue-1": 0.97,
        }

        # Context adjustment weights (confidence factors)
        self.context_weights = {
            "home_away": 1.0,
            "season_phase": 1.0,
            "competition_level": 1.0,
            "venue_performance": 1.0,
        }

        # Bayesian parameters adaptation
        self.bayesian_adaptation = {
            "learning_rate_adjustment": 1.0,  # Multiplier for learning rate
            "prior_alpha_adjustment": 1.0,  # Adjustment to prior strength
            "prior_beta_adjustment": 1.0,
        }

        # Confidence scaling
        self.confidence_scale = 1.0  # Multiplier for all predictions

        # Adaptation history for tracking changes
        self.adaptation_history = []

        self._load_adjuster_state()

    def adapt_league_factors(self, league_performance: dict[str, dict]) -> None:
        """Adapt league adjustment factors based on per-league accuracy.

        Args:
            league_performance: {league: {'accuracy': float, 'samples': int, ...}}

        """
        for league, stats in league_performance.items():
            if league not in self.league_factors:
                continue

            if stats["samples"] < 5:
                continue  # Need minimum samples for reliable adaptation

            accuracy = stats["accuracy"]
            baseline_accuracy = 0.65  # From Phase 3 target

            # Calculate adjustment: if accuracy is below baseline, boost the factor
            accuracy_delta = accuracy - baseline_accuracy

            # Adaptive scaling: positive delta = good performance, boost slightly
            # Negative delta = poor performance, reduce slightly
            adjustment = 1.0 + (accuracy_delta * self.adaptation_rate * 0.5)
            adjustment = max(0.85, min(1.15, adjustment))  # Clamp to ±15%

            # Apply adaptation with smoothing
            self.league_factors[league] = (
                self.league_factors[league] * (1.0 - self.adaptation_rate)
                + adjustment * self.adaptation_rate
            )

    def adapt_context_weights(self, context_effectiveness: dict[str, float]) -> None:
        """Adapt context adjustment weights based on recent effectiveness.

        Args:
            context_effectiveness: {context_type: accuracy_contribution}

        """
        for context_type, effectiveness in context_effectiveness.items():
            if context_type not in self.context_weights:
                continue

            # Effectiveness > 0.5 means the adjustment helped
            # Effectiveness < 0.5 means the adjustment hurt
            direction = effectiveness - 0.5

            # Scale weight based on effectiveness
            adjustment = 1.0 + (direction * self.adaptation_rate)
            adjustment = max(0.7, min(1.3, adjustment))  # Clamp to 70%-130%

            self.context_weights[context_type] = (
                self.context_weights[context_type] * (1.0 - self.adaptation_rate)
                + adjustment * self.adaptation_rate
            )

    def adapt_bayesian_parameters(self, calibration_error: float, samples: int) -> None:
        """Adapt Bayesian update parameters based on calibration performance.

        Args:
            calibration_error: Mean absolute calibration error (ECE)
            samples: Number of samples used

        """
        if samples < 10:
            return  # Need minimum samples

        baseline_error = 0.08  # From Phase 3 target
        error_ratio = calibration_error / baseline_error

        # If calibration is poor (high error), reduce learning rate
        # If calibration is good (low error), increase learning rate slightly
        if error_ratio > 1.2:  # Error is 20%+ above baseline
            self.bayesian_adaptation["learning_rate_adjustment"] *= (
                1.0 - self.adaptation_rate * 0.2
            )
        elif error_ratio < 0.8:  # Error is 20%+ below baseline
            self.bayesian_adaptation["learning_rate_adjustment"] *= (
                1.0 + self.adaptation_rate * 0.1
            )

        # Clamp adjustment
        self.bayesian_adaptation["learning_rate_adjustment"] = max(
            0.5, min(1.5, self.bayesian_adaptation["learning_rate_adjustment"]),
        )

    def adapt_confidence_scale(self, drift_severity: float, accuracy: float) -> None:
        """Adapt overall confidence scaling based on drift and accuracy.

        Args:
            drift_severity: Drift detection severity (0.0-1.0)
            accuracy: Current overall accuracy

        """
        baseline_accuracy = 0.65  # From Phase 3 target
        accuracy_ratio = accuracy / baseline_accuracy if baseline_accuracy > 0 else 1.0

        # Calculate target scale
        target_scale = 1.0

        # Adjust based on accuracy
        if accuracy_ratio < 0.95:  # Below baseline
            target_scale *= accuracy_ratio  # Reduce confidence proportionally
        elif accuracy_ratio > 1.05:  # Above baseline
            target_scale *= min(1.05, accuracy_ratio)  # Slight boost

        # Adjust based on drift
        target_scale *= 1.0 - drift_severity * 0.15  # Reduce by up to 15% on drift

        # Apply smoothing
        self.confidence_scale = (
            self.confidence_scale * (1.0 - self.adaptation_rate)
            + target_scale * self.adaptation_rate
        )

        # Clamp to reasonable range
        self.confidence_scale = max(0.80, min(1.20, self.confidence_scale))

    def get_adapted_league_factor(self, league: str) -> float:
        """Get the current adapted factor for a league."""
        return self.league_factors.get(league, 1.0)

    def get_adapted_context_weights(self) -> dict[str, float]:
        """Get the current adapted context weights."""
        return self.context_weights.copy()

    def get_adapted_bayesian_adjustment(self) -> float:
        """Get the adjusted learning rate for Bayesian updates."""
        return self.bayesian_adaptation["learning_rate_adjustment"]

    def get_confidence_scale(self) -> float:
        """Get the current overall confidence scaling factor."""
        return self.confidence_scale

    def apply_adaptations(self, raw_confidence: float, league: str) -> float:
        """Apply all active adaptations to a raw confidence value.

        Args:
            raw_confidence: Raw model confidence (0.0-1.0)
            league: League identifier

        Returns:
            Adapted confidence (0.0-1.0)

        """
        adapted = raw_confidence

        # Apply league factor
        league_factor = self.get_adapted_league_factor(league)
        adapted *= league_factor

        # Apply overall confidence scale
        adapted *= self.confidence_scale

        # Clamp to valid range
        return max(0.0, min(1.0, adapted))

    def reset_to_baseline(self) -> None:
        """Reset all adaptation factors to baseline values."""
        self.league_factors = {
            "la-liga": 1.00,
            "premier-league": 1.02,
            "bundesliga": 0.98,
            "serie-a": 0.99,
            "ligue-1": 0.97,
        }
        self.context_weights = {
            "home_away": 1.0,
            "season_phase": 1.0,
            "competition_level": 1.0,
            "venue_performance": 1.0,
        }
        self.bayesian_adaptation = {
            "learning_rate_adjustment": 1.0,
            "prior_alpha_adjustment": 1.0,
            "prior_beta_adjustment": 1.0,
        }
        self.confidence_scale = 1.0

    def record_adaptation(self, change_type: str, details: dict) -> None:
        """Record an adaptation event for audit trail."""
        self.adaptation_history.append(
            {
                "timestamp": datetime.now().isoformat(),
                "type": change_type,
                "details": details,
            },
        )

    def save_adjuster_state(self) -> None:
        """Persist adjuster state to disk."""
        os.makedirs(self.cache_dir, exist_ok=True)

        state = {
            "league_factors": self.league_factors,
            "context_weights": self.context_weights,
            "bayesian_adaptation": self.bayesian_adaptation,
            "confidence_scale": self.confidence_scale,
            "adaptation_history": self.adaptation_history[
                -100:
            ],  # Keep last 100 events
            "timestamp": datetime.now().isoformat(),
        }

        filepath = os.path.join(self.cache_dir, "phase4_adjuster_state.json")
        with open(filepath, "w") as f:
            json.dump(state, f, indent=2)

    def _load_adjuster_state(self) -> None:
        """Load adjuster state from disk if available."""
        filepath = os.path.join(self.cache_dir, "phase4_adjuster_state.json")
        if os.path.exists(filepath):
            try:
                with open(filepath) as f:
                    state = json.load(f)
                    self.league_factors = state.get(
                        "league_factors", self.league_factors,
                    )
                    self.context_weights = state.get(
                        "context_weights", self.context_weights,
                    )
                    self.bayesian_adaptation = state.get(
                        "bayesian_adaptation", self.bayesian_adaptation,
                    )
                    self.confidence_scale = state.get(
                        "confidence_scale", self.confidence_scale,
                    )
                    self.adaptation_history = state.get("adaptation_history", [])
            except Exception:
                pass  # Graceful fallback to defaults
