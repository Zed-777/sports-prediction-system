"""Bayesian Update System Module for Phase 3

Maintains Bayesian posterior distributions for confidence prediction,
enabling continuous learning from match outcomes.
"""

import json
import os
from datetime import datetime

import numpy as np
from scipy import stats as scipy_stats


class BayesianUpdater:
    """Maintains Bayesian posterior for confidence prediction accuracy.

    Uses Beta-Binomial conjugate model:
    - Prior: Beta(alpha, beta) - initial belief about prediction quality
    - Updates: Add 1 to alpha on correct predictions, to beta on incorrect
    - Posterior Mean: alpha / (alpha + beta) - expected accuracy
    - Posterior Variance: alpha*beta / ((alpha+beta)^2 * (alpha+beta+1))

    This enables self-correcting confidence calibration through continuous learning.
    """

    def __init__(
        self,
        prior_alpha: float = 2.0,
        prior_beta: float = 2.0,
        learning_rate: float = 0.8,
        cache_dir: str | None = None,
    ):
        """Initialize Bayesian updater with prior parameters.

        Args:
            prior_alpha: Prior alpha parameter (shapes confidence belief)
            prior_beta: Prior beta parameter (shapes confidence belief)
            learning_rate: How aggressively to shift toward posterior (0-1)
            cache_dir: Directory for persistence

        """
        # Prior parameters (Beta distribution)
        self.prior_alpha = prior_alpha
        self.prior_beta = prior_beta

        # Posterior parameters (updated with outcomes)
        self.posterior_alpha = prior_alpha
        self.posterior_beta = prior_beta

        # Learning parameters
        self.learning_rate = learning_rate
        self.min_samples_for_adjustment = 10

        # Match history for tracking
        self.match_history: list[dict] = []
        self.successful_predictions = 0
        self.total_predictions = 0

        # Cache directory
        self.cache_dir = cache_dir or "data/cache"

        # Load persisted data
        self._load_bayesian_state()

    def record_match(
        self,
        confidence: float,
        home_won: bool,
        match_id: str | None = None,
        additional_data: dict | None = None,
    ) -> dict:
        """Update posterior with match outcome.

        Records whether the prediction (based on confidence) was correct
        and updates the posterior distribution accordingly.

        Args:
            confidence: Predicted probability of home win (0.0-1.0)
            home_won: Whether home team actually won
            match_id: Optional match identifier for tracking
            additional_data: Optional additional match data

        Returns:
            Update metadata including new posterior mean and confidence adjustment

        """
        # Determine if prediction was correct
        # Confidence > 0.5 = predict home win, otherwise predict away
        predicted_home_win = confidence > 0.5
        prediction_correct = (predicted_home_win and home_won) or (
            not predicted_home_win and not home_won
        )

        # Update posterior
        if prediction_correct:
            self.posterior_alpha += 1.0
            self.successful_predictions += 1
        else:
            self.posterior_beta += 1.0

        self.total_predictions += 1

        # Calculate new metrics
        new_mean = self.get_posterior_mean()
        new_std = self.get_posterior_std()
        confidence_adjustment = self._calculate_confidence_adjustment(confidence)

        # Record in history
        record = {
            "timestamp": datetime.now().isoformat(),
            "match_id": match_id,
            "confidence": confidence,
            "outcome": home_won,
            "prediction_correct": prediction_correct,
            "posterior_mean": new_mean,
            "posterior_std": new_std,
            "posterior_alpha": self.posterior_alpha,
            "posterior_beta": self.posterior_beta,
            "confidence_adjustment": confidence_adjustment,
            "additional_data": additional_data or {},
        }

        self.match_history.append(record)

        return record

    def get_posterior_mean(self) -> float:
        """Get current posterior mean (expected prediction accuracy).

        Returns:
            Mean of Beta distribution: alpha / (alpha + beta)

        """
        total = self.posterior_alpha + self.posterior_beta
        return self.posterior_alpha / total if total > 0 else 0.5

    def get_posterior_std(self) -> float:
        """Get posterior standard deviation (uncertainty).

        Lower std = more confident in posterior estimate.
        Higher std = more uncertain.

        Returns:
            Standard deviation of Beta distribution

        """
        alpha = self.posterior_alpha
        beta = self.posterior_beta
        total = alpha + beta

        if total <= 1:
            return 0.5  # Maximum uncertainty with default prior

        variance = (alpha * beta) / (total**2 * (total + 1))
        return np.sqrt(variance)

    def get_posterior_credible_interval(
        self, credibility: float = 0.95,
    ) -> tuple[float, float]:
        """Get credible interval for posterior accuracy.

        Args:
            credibility: Confidence level (default 95%)

        Returns:
            Tuple of (lower_bound, upper_bound)

        """
        alpha = self.posterior_alpha
        beta = self.posterior_beta

        # Use Beta distribution quantiles
        lower = scipy_stats.beta.ppf((1 - credibility) / 2, alpha, beta)
        upper = scipy_stats.beta.ppf(1 - (1 - credibility) / 2, alpha, beta)

        return (lower, upper)

    def adjust_confidence(self, raw_confidence: float) -> tuple[float, dict]:
        """Adjust confidence toward posterior mean using learning rate.

        If system has learned it's overconfident, shift confidence closer to 0.5.
        If system has learned it's underconfident, shift closer to extremes.

        Args:
            raw_confidence: Unadjusted confidence (0.0-1.0)

        Returns:
            Tuple of (adjusted_confidence, adjustment_metadata)

        """
        if self.total_predictions < self.min_samples_for_adjustment:
            # Not enough data for adjustment
            return raw_confidence, {
                "reason": "insufficient_samples",
                "samples": self.total_predictions,
                "min_required": self.min_samples_for_adjustment,
            }

        posterior_mean = self.get_posterior_mean()
        posterior_std = self.get_posterior_std()

        # Calculate uncertainty multiplier
        # Higher uncertainty = less aggressive adjustment
        uncertainty_factor = 1.0 + posterior_std
        effective_learning_rate = self.learning_rate / uncertainty_factor

        # Blend raw confidence with posterior mean
        # If posterior_mean > 0.5, system is accurate, trust it more
        # If posterior_mean < 0.5, system is poor, trust it less
        adjusted = (
            raw_confidence * (1.0 - effective_learning_rate)
            + posterior_mean * effective_learning_rate
        )

        metadata = {
            "raw_confidence": raw_confidence,
            "posterior_mean": posterior_mean,
            "posterior_std": posterior_std,
            "learning_rate": effective_learning_rate,
            "adjustment_factor": (
                adjusted / raw_confidence if raw_confidence > 0 else 1.0
            ),
            "direction": "increased" if adjusted > raw_confidence else "decreased",
            "change": adjusted - raw_confidence,
            "samples_used": self.total_predictions,
            "accuracy_rate": self.successful_predictions / self.total_predictions,
        }

        return adjusted, metadata

    def _calculate_confidence_adjustment(self, confidence: float) -> float:
        """Calculate confidence adjustment factor for this match."""
        if self.total_predictions < self.min_samples_for_adjustment:
            return 1.0

        adjusted, _ = self.adjust_confidence(confidence)
        return adjusted

    def get_bayesian_statistics(self) -> dict:
        """Get comprehensive Bayesian statistics.

        Returns:
            Dict with posterior, accuracy, history summary

        """
        credible_lower, credible_upper = self.get_posterior_credible_interval(0.95)

        recent_history = self.match_history[-20:] if self.match_history else []
        recent_accuracy = (
            sum(1 for m in recent_history if m["prediction_correct"])
            / len(recent_history)
            if recent_history
            else 0.0
        )

        return {
            "total_predictions": self.total_predictions,
            "successful_predictions": self.successful_predictions,
            "overall_accuracy": (
                self.successful_predictions / self.total_predictions
                if self.total_predictions > 0
                else 0.0
            ),
            "recent_accuracy_20": recent_accuracy,
            "posterior_mean": self.get_posterior_mean(),
            "posterior_std": self.get_posterior_std(),
            "credible_interval_95": {"lower": credible_lower, "upper": credible_upper},
            "posterior_alpha": self.posterior_alpha,
            "posterior_beta": self.posterior_beta,
            "learning_rate": self.learning_rate,
            "samples_for_adjustment": self.min_samples_for_adjustment,
            "ready_for_adjustment": self.total_predictions
            >= self.min_samples_for_adjustment,
            "recent_matches": recent_history,
        }

    def reset_posterior(self, keep_history: bool = True) -> None:
        """Reset posterior to prior (for new league, new season, etc).

        Args:
            keep_history: If True, keep match history; if False, clear it

        """
        self.posterior_alpha = self.prior_alpha
        self.posterior_beta = self.prior_beta
        self.successful_predictions = 0
        self.total_predictions = 0

        if not keep_history:
            self.match_history = []

    def _load_bayesian_state(self) -> None:
        """Load persisted Bayesian state."""
        if not self.cache_dir or not os.path.exists(self.cache_dir):
            return

        state_file = os.path.join(self.cache_dir, "bayesian_updater_state.json")
        if os.path.exists(state_file):
            try:
                with open(state_file) as f:
                    data = json.load(f)
                    self.posterior_alpha = data.get("posterior_alpha", self.prior_alpha)
                    self.posterior_beta = data.get("posterior_beta", self.prior_beta)
                    self.successful_predictions = data.get("successful_predictions", 0)
                    self.total_predictions = data.get("total_predictions", 0)
                    self.match_history = data.get("match_history", [])
            except Exception:
                pass  # Silently fail if load is corrupted

    def save_bayesian_state(self) -> None:
        """Save Bayesian state to cache."""
        if not self.cache_dir:
            return

        os.makedirs(self.cache_dir, exist_ok=True)

        state_data = {
            "posterior_alpha": self.posterior_alpha,
            "posterior_beta": self.posterior_beta,
            "prior_alpha": self.prior_alpha,
            "prior_beta": self.prior_beta,
            "successful_predictions": self.successful_predictions,
            "total_predictions": self.total_predictions,
            "learning_rate": self.learning_rate,
            "match_history": self.match_history[-100:],  # Keep last 100 matches
            "saved_at": datetime.now().isoformat(),
        }

        try:
            with open(
                os.path.join(self.cache_dir, "bayesian_updater_state.json"), "w",
            ) as f:
                json.dump(state_data, f, indent=2)
        except Exception:
            pass  # Silently fail if save fails
