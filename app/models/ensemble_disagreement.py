"""Ensemble Disagreement Detection (TODO #12)
===========================================
Measures and classifies disagreement across constituent models in an
ensemble, using it to penalise confidence and optionally block bets when
models strongly disagree.

Why disagreement matters for live betting
------------------------------------------
High disagreement = high epistemic uncertainty = the edge may be an artefact
of one model's miscalibration rather than a genuine advantage.  Filtering or
penalising high-disagreement predictions is a crucial risk-control lever.

Disagreement metrics
--------------------
1. **Winner disagreement**     – do models disagree on WHO wins?
2. **Probability variance**    – variance of each outcome prob across models
3. **Jensen-Shannon divergence** (mean pairwise) – measure of distributional distance
4. **Prediction entropy**      – entropy of the *mean* distribution (captures overall uncertainty)
5. **Max pairwise distance**   – max L1 distance between any two model distributions

Usage
-----
    detector = EnsembleDisagreementDetector()

    predictions = [
        {"home_win_prob": 0.55, "draw_prob": 0.25, "away_win_prob": 0.20},  # model A
        {"home_win_prob": 0.40, "draw_prob": 0.30, "away_win_prob": 0.30},  # model B
        {"home_win_prob": 0.60, "draw_prob": 0.20, "away_win_prob": 0.20},  # model C
    ]
    result = detector.analyse(predictions)
    print(result.level)             # DisagreementLevel.MODERATE
    print(result.confidence_penalty) # e.g. 0.08

    # Modify a prediction dict
    adjusted = detector.apply_to_prediction(base_pred, predictions)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum

import numpy as np

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

#: Outcome keys used consistently throughout this module
OUTCOME_KEYS: tuple[str, str, str] = ("home_win_prob", "draw_prob", "away_win_prob")

#: DisagreementLevel thresholds for the composite score (0-1)
LEVEL_LOW_THRESHOLD      = 0.25
LEVEL_MODERATE_THRESHOLD = 0.45
LEVEL_HIGH_THRESHOLD     = 0.70

#: Confidence penalty per level
PENALTY_LOW      = 0.03
PENALTY_MODERATE = 0.08
PENALTY_HIGH     = 0.15
PENALTY_SEVERE   = 0.25

#: Minimum number of models required for disagreement analysis
MIN_MODELS = 2


# ---------------------------------------------------------------------------
# Enums / data structures
# ---------------------------------------------------------------------------

class DisagreementLevel(str, Enum):
    UNANIMOUS  = "UNANIMOUS"   # all models agree exactly (or near-exactly)
    LOW        = "LOW"         # small variation, acceptable
    MODERATE   = "MODERATE"    # notable variation, confidence penalty applied
    HIGH       = "HIGH"        # significant variation, large confidence penalty
    SEVERE     = "SEVERE"      # models strongly contradict each other

    @property
    def confidence_penalty(self) -> float:
        return {
            "UNANIMOUS":  0.00,
            "LOW":        PENALTY_LOW,
            "MODERATE":   PENALTY_MODERATE,
            "HIGH":       PENALTY_HIGH,
            "SEVERE":     PENALTY_SEVERE,
        }[self.value]

    @property
    def should_block(self) -> bool:
        """True if disagreement is so severe that bet should be blocked."""
        return self in (DisagreementLevel.SEVERE,)


@dataclass
class DisagreementReport:
    """Full disagreement analysis for a set of model predictions."""

    n_models:             int
    winner_agreement:     bool        # True = all models predict the same winner
    predicted_winners:    list[str]   # per-model predicted winner
    majority_winner:      str         # plurality winner
    winner_consensus_pct: float       # fraction of models agreeing on plurality winner

    # Quantitative metrics (0-1 scale)
    mean_variance:        float       # avg variance of probs across models
    mean_js_divergence:   float       # mean pairwise Jensen-Shannon divergence
    mean_entropy:         float       # entropy of mean distribution
    max_pairwise_l1:      float       # worst-case L1 distance between any two models

    # Composite
    composite_score:      float       # 0=perfect agreement, 1=complete chaos
    level:                DisagreementLevel
    confidence_penalty:   float

    # Per-outcome variances
    variances:            dict[str, float] = field(default_factory=dict)
    # Mean probabilities across models
    mean_probs:           dict[str, float] = field(default_factory=dict)

    def summary(self) -> str:
        winner_str = (
            f"all models → {self.majority_winner}"
            if self.winner_agreement
            else f"split ({self.winner_consensus_pct:.0%} → {self.majority_winner})"
        )
        return (
            f"[{self.level}] {self.n_models} models | {winner_str} | "
            f"composite={self.composite_score:.3f} | "
            f"JS={self.mean_js_divergence:.3f} | "
            f"penalty=-{self.confidence_penalty:.2f}"
        )


# ---------------------------------------------------------------------------
# Core detector
# ---------------------------------------------------------------------------

class EnsembleDisagreementDetector:
    """Analyses disagreement across an ensemble's constituent predictions.

    Parameters
    ----------
    level_thresholds : (low, moderate, high) composite-score thresholds
    custom_penalties : override default confidence penalties per level

    """

    def __init__(
        self,
        level_thresholds: tuple[float, float, float] = (
            LEVEL_LOW_THRESHOLD,
            LEVEL_MODERATE_THRESHOLD,
            LEVEL_HIGH_THRESHOLD,
        ),
        custom_penalties: dict[DisagreementLevel, float] | None = None,
    ) -> None:
        self._thresh_low, self._thresh_moderate, self._thresh_high = level_thresholds
        self._custom_penalties = custom_penalties or {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyse(
        self,
        predictions: list[dict[str, float]],
    ) -> DisagreementReport:
        """Analyse disagreement across a list of model-prediction dicts.

        Each prediction dict must contain the three outcome keys:
        ``home_win_prob``, ``draw_prob``, ``away_win_prob``.

        Parameters
        ----------
        predictions : list of dicts, each with home/draw/away probs
                      Probabilities are automatically renormalised if they
                      don't sum to 1.

        Returns
        -------
        DisagreementReport

        """
        if len(predictions) < MIN_MODELS:
            return self._trivial_report(predictions)

        # Extract and normalise probability arrays  [n_models × 3]
        prob_matrix = self._extract_prob_matrix(predictions)
        mean_probs  = prob_matrix.mean(axis=0)

        # --- winner disagreement ---
        winners = [OUTCOME_KEYS[int(np.argmax(row))] for row in prob_matrix]
        majority = max(set(winners), key=winners.count)
        consensus_pct = winners.count(majority) / len(winners)
        winner_agreement = len(set(winners)) == 1

        # --- quantitative metrics ---
        variances    = np.var(prob_matrix, axis=0)  # shape (3,)
        mean_var     = float(variances.mean())

        mean_js      = self._mean_pairwise_js(prob_matrix)
        entropy      = float(_entropy(mean_probs))
        max_l1       = self._max_pairwise_l1(prob_matrix)

        # --- composite score ---
        # Weight: JS divergence most informative, then winner disagreement
        winner_penalty = 0.0 if winner_agreement else (1.0 - consensus_pct)
        composite = float(
            0.40 * mean_js / math.log(2)        # normalised JSD → [0,1]
            + 0.25 * min(mean_var / 0.12, 1.0)  # variance term
            + 0.20 * winner_penalty               # winner split
            + 0.15 * entropy / math.log(3),       # entropy term
        )
        composite = max(0.0, min(1.0, composite))

        # --- level ---
        level = self._composite_to_level(composite)
        penalty = self._custom_penalties.get(level, level.confidence_penalty)

        var_dict  = {k: float(v) for k, v in zip(OUTCOME_KEYS, variances)}
        mean_dict = {k: float(v) for k, v in zip(OUTCOME_KEYS, mean_probs)}

        return DisagreementReport(
            n_models=len(predictions),
            winner_agreement=winner_agreement,
            predicted_winners=winners,
            majority_winner=majority,
            winner_consensus_pct=consensus_pct,
            mean_variance=mean_var,
            mean_js_divergence=mean_js,
            mean_entropy=entropy,
            max_pairwise_l1=max_l1,
            composite_score=composite,
            level=level,
            confidence_penalty=penalty,
            variances=var_dict,
            mean_probs=mean_dict,
        )

    def analyse_named(
        self,
        named_predictions: dict[str, dict[str, float]],
    ) -> DisagreementReport:
        """Convenience wrapper when predictions come as a dict keyed by model name.
        """
        return self.analyse(list(named_predictions.values()))

    def apply_to_prediction(
        self,
        base_prediction: dict,
        constituent_predictions: list[dict[str, float]],
    ) -> dict:
        """Compute disagreement and apply the confidence penalty to ``base_prediction``.

        Returns a new dict (shallow copy of ``base_prediction``) with:
        - ``confidence`` lowered by the disagreement penalty (if key exists)
        - ``ensemble_disagreement`` sub-dict added
        """
        report = self.analyse(constituent_predictions)
        out = dict(base_prediction)

        if "confidence" in out:
            out["confidence"] = max(0.0, float(out["confidence"]) - report.confidence_penalty)

        out["ensemble_disagreement"] = {
            "level":             report.level.value,
            "composite_score":   round(report.composite_score, 4),
            "confidence_penalty": round(report.confidence_penalty, 4),
            "winner_agreement":  report.winner_agreement,
            "majority_winner":   report.majority_winner,
            "winner_consensus":  round(report.winner_consensus_pct, 3),
            "mean_js":           round(report.mean_js_divergence, 4),
            "n_models":          report.n_models,
        }

        return out

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _extract_prob_matrix(
        self, predictions: list[dict[str, float]],
    ) -> np.ndarray:
        """Return [n_models × 3] normalised probability matrix."""
        rows = []
        for pred in predictions:
            row = np.array([float(pred.get(k, 0.0)) for k in OUTCOME_KEYS])
            total = row.sum()
            if total > 0:
                row = row / total
            else:
                row = np.array([1 / 3, 1 / 3, 1 / 3])
            rows.append(row)
        return np.array(rows, dtype=float)

    def _mean_pairwise_js(self, prob_matrix: np.ndarray) -> float:
        """Mean Jensen-Shannon divergence across all model pairs."""
        n = len(prob_matrix)
        if n < 2:
            return 0.0
        total = 0.0
        count = 0
        for i in range(n):
            for j in range(i + 1, n):
                total += _js_divergence(prob_matrix[i], prob_matrix[j])
                count += 1
        return total / count if count > 0 else 0.0

    def _max_pairwise_l1(self, prob_matrix: np.ndarray) -> float:
        """Maximum L1 distance between any two model prediction distributions."""
        n = len(prob_matrix)
        if n < 2:
            return 0.0
        worst = 0.0
        for i in range(n):
            for j in range(i + 1, n):
                d = float(np.sum(np.abs(prob_matrix[i] - prob_matrix[j])))
                worst = max(worst, d)
        return worst

    def _composite_to_level(self, composite: float) -> DisagreementLevel:
        if composite < 0.05:
            return DisagreementLevel.UNANIMOUS
        if composite < self._thresh_low:
            return DisagreementLevel.LOW
        if composite < self._thresh_moderate:
            return DisagreementLevel.MODERATE
        if composite < self._thresh_high:
            return DisagreementLevel.HIGH
        return DisagreementLevel.SEVERE

    def _trivial_report(
        self, predictions: list[dict[str, float]],
    ) -> DisagreementReport:
        """Return a report when there's only 0 or 1 model (no comparison possible)."""
        if predictions:
            probs = {k: float(predictions[0].get(k, 1 / 3)) for k in OUTCOME_KEYS}
            winner = max(probs, key=lambda k: probs[k])
        else:
            probs   = dict.fromkeys(OUTCOME_KEYS, 1 / 3)
            winner  = OUTCOME_KEYS[0]
        return DisagreementReport(
            n_models=len(predictions),
            winner_agreement=True,
            predicted_winners=[winner] if predictions else [],
            majority_winner=winner,
            winner_consensus_pct=1.0,
            mean_variance=0.0,
            mean_js_divergence=0.0,
            mean_entropy=float(_entropy(np.array(list(probs.values())))),
            max_pairwise_l1=0.0,
            composite_score=0.0,
            level=DisagreementLevel.UNANIMOUS,
            confidence_penalty=0.0,
            variances=dict.fromkeys(OUTCOME_KEYS, 0.0),
            mean_probs=probs,
        )


# ---------------------------------------------------------------------------
# Math helpers
# ---------------------------------------------------------------------------

def _entropy(probs: np.ndarray) -> float:
    """Shannon entropy (nats) of a probability distribution."""
    probs = np.clip(probs, 1e-15, 1.0)
    probs = probs / probs.sum()
    return float(-np.sum(probs * np.log(probs)))


def _js_divergence(p: np.ndarray, q: np.ndarray) -> float:
    """Jensen-Shannon divergence between two distributions (nats).
    Bounded [0, ln 2].
    """
    p = np.clip(p, 1e-15, 1.0)
    q = np.clip(q, 1e-15, 1.0)
    p = p / p.sum()
    q = q / q.sum()
    m = 0.5 * (p + q)
    return float(0.5 * np.sum(p * np.log(p / m)) + 0.5 * np.sum(q * np.log(q / m)))


# ---------------------------------------------------------------------------
# Convenience: build predictions from a dict of named model outputs
# ---------------------------------------------------------------------------

def disagreement_from_named(
    named_predictions: dict[str, dict[str, float]],
    detector: EnsembleDisagreementDetector | None = None,
) -> DisagreementReport:
    """Quick helper: run disagreement analysis on named model predictions.

    Example::
        report = disagreement_from_named({
            "poisson":   {"home_win_prob": 0.55, "draw_prob": 0.25, "away_win_prob": 0.20},
            "elo":        {"home_win_prob": 0.50, "draw_prob": 0.28, "away_win_prob": 0.22},
            "xg_model":  {"home_win_prob": 0.48, "draw_prob": 0.30, "away_win_prob": 0.22},
        })
    """
    det = detector or EnsembleDisagreementDetector()
    return det.analyse(list(named_predictions.values()))
