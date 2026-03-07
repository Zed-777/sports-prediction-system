"""
Model Staleness Detection (TODO #38)
=====================================
Detects when a trained model or data artifact is too old / degraded to be
trusted for live predictions, preventing stale-model bets.

Three stale-detection axes
--------------------------
1. FILE AGE     – model artifact (pickle / json) older than ``max_age_days``
2. ACCURACY     – rolling accuracy in the live monitor has dropped below a floor
3. DISTRIBUTIONAL DRIFT – moving average of probabilities has shifted vs baseline

Severity levels
---------------
``OK``      – all checks pass
``WARNING`` – at least one soft boundary crossed (warn but keep predicting)
``STALE``   – hard boundary crossed (block live predictions)

Typical usage
-------------
    detector = ModelStalenessDetector()
    report   = detector.check_model("models/enhanced_model.pkl")
    if report.severity == Severity.STALE:
        raise PredictionBlockedError("Model too stale for live bets")
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Enums / constants
# ---------------------------------------------------------------------------

class Severity(str, Enum):
    OK      = "OK"
    WARNING = "WARNING"
    STALE   = "STALE"


# Default thresholds (overridable per instance)
DEFAULT_MAX_AGE_DAYS        = 7      # model file older than 7 days → WARNING
DEFAULT_HARD_MAX_AGE_DAYS   = 30     # older than 30 days → STALE
DEFAULT_ACCURACY_FLOOR_WARN = 0.55   # rolling accuracy below 55 % → WARNING
DEFAULT_ACCURACY_FLOOR_HARD = 0.45   # rolling accuracy below 45 % → STALE
DEFAULT_DRIFT_WARN          = 0.10   # mean-prob shift > 10 pp → WARNING
DEFAULT_DRIFT_HARD          = 0.20   # mean-prob shift > 20 pp → STALE
DEFAULT_PROB_WINDOW         = 100    # number of recent predictions for drift check


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class FileAgeCheck:
    path: str
    exists: bool
    age_days: Optional[float]         # None if file does not exist
    severity: Severity
    message: str


@dataclass
class AccuracyCheck:
    rolling_accuracy: Optional[float]  # None if not enough data
    baseline_accuracy: float
    n_samples: int
    severity: Severity
    message: str


@dataclass
class DriftCheck:
    current_mean_prob: Optional[float]
    baseline_mean_prob: float
    shift: Optional[float]             # |current - baseline|, None if insufficient
    n_samples: int
    severity: Severity
    message: str


@dataclass
class StalenessReport:
    """Aggregated staleness report for one model / artifact."""
    model_name: str
    checked_at: str                    # ISO-8601 UTC
    file_check:     Optional[FileAgeCheck]
    accuracy_check: Optional[AccuracyCheck]
    drift_check:    Optional[DriftCheck]
    overall_severity: Severity
    blocking: bool                     # True → live predictions should be halted
    reasons: List[str] = field(default_factory=list)

    def summary(self) -> str:
        icon = {"OK": "✓", "WARNING": "⚠", "STALE": "✗"}.get(self.overall_severity, "?")
        sep  = " | ".join(self.reasons) if self.reasons else "all checks passed"
        return f"[{icon} {self.overall_severity}] {self.model_name}: {sep}"


# ---------------------------------------------------------------------------
# Core detector
# ---------------------------------------------------------------------------

class ModelStalenessDetector:
    """
    Checks model artifacts and live performance metrics for staleness.

    Parameters
    ----------
    max_age_days_warn  : file age threshold for WARNING (default 7)
    max_age_days_hard  : file age threshold for STALE   (default 30)
    accuracy_floor_warn: rolling accuracy WARNING floor  (default 0.55)
    accuracy_floor_hard: rolling accuracy STALE floor   (default 0.45)
    drift_warn         : probability drift WARNING threshold (default 0.10)
    drift_hard         : probability drift STALE threshold   (default 0.20)
    prob_window        : rolling window size for drift detection (default 100)
    """

    def __init__(
        self,
        max_age_days_warn:   float = DEFAULT_MAX_AGE_DAYS,
        max_age_days_hard:   float = DEFAULT_HARD_MAX_AGE_DAYS,
        accuracy_floor_warn: float = DEFAULT_ACCURACY_FLOOR_WARN,
        accuracy_floor_hard: float = DEFAULT_ACCURACY_FLOOR_HARD,
        drift_warn:          float = DEFAULT_DRIFT_WARN,
        drift_hard:          float = DEFAULT_DRIFT_HARD,
        prob_window:         int   = DEFAULT_PROB_WINDOW,
    ) -> None:
        self.max_age_days_warn   = max_age_days_warn
        self.max_age_days_hard   = max_age_days_hard
        self.accuracy_floor_warn = accuracy_floor_warn
        self.accuracy_floor_hard = accuracy_floor_hard
        self.drift_warn          = drift_warn
        self.drift_hard          = drift_hard
        self.prob_window         = prob_window

        # Rolling buffers for live accuracy / drift tracking
        # Populated externally by calling ``record_prediction``
        self._recent_correct:  List[int]   = []  # 1 = correct, 0 = incorrect
        self._recent_probs:    List[float] = []  # predicted probability values

    # ------------------------------------------------------------------
    # External update interface
    # ------------------------------------------------------------------

    def record_prediction(self, predicted_prob: float, is_correct: bool) -> None:
        """
        Feed a new live prediction result into the rolling buffers.
        Call this every time the model makes a verifiable prediction.
        """
        self._recent_correct.append(1 if is_correct else 0)
        self._recent_probs.append(float(predicted_prob))
        # Keep rolling window
        if len(self._recent_correct) > self.prob_window:
            self._recent_correct.pop(0)
        if len(self._recent_probs) > self.prob_window:
            self._recent_probs.pop(0)

    def reset_buffers(self) -> None:
        """Clear rolling history (e.g. after a model retrain)."""
        self._recent_correct = []
        self._recent_probs   = []

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    def check_file_age(self, model_path: str) -> FileAgeCheck:
        """Check whether a model file is too old."""
        p = Path(model_path)
        if not p.exists():
            return FileAgeCheck(
                path=model_path, exists=False, age_days=None,
                severity=Severity.WARNING,
                message=f"File not found: {model_path}",
            )
        mtime   = p.stat().st_mtime
        age_sec = time.time() - mtime
        age_d   = age_sec / 86_400

        if age_d >= self.max_age_days_hard:
            sev = Severity.STALE
            msg = f"Model file {p.name} is {age_d:.1f} days old (hard limit {self.max_age_days_hard}d)"
        elif age_d >= self.max_age_days_warn:
            sev = Severity.WARNING
            msg = f"Model file {p.name} is {age_d:.1f} days old (warn limit {self.max_age_days_warn}d)"
        else:
            sev = Severity.OK
            msg = f"Model file {p.name} is {age_d:.1f} days old — OK"

        return FileAgeCheck(path=model_path, exists=True, age_days=age_d, severity=sev, message=msg)

    def check_accuracy(
        self,
        recent_correct: Optional[List[int]] = None,
        baseline: float = 0.60,
    ) -> AccuracyCheck:
        """
        Check rolling accuracy vs baseline.
        Uses internal buffer if ``recent_correct`` is not supplied.
        """
        buf = recent_correct if recent_correct is not None else self._recent_correct
        n   = len(buf)
        if n == 0:
            return AccuracyCheck(
                rolling_accuracy=None, baseline_accuracy=baseline,
                n_samples=0, severity=Severity.OK,
                message="Insufficient samples for accuracy check",
            )
        acc = sum(buf) / n
        if acc < self.accuracy_floor_hard:
            sev = Severity.STALE
            msg = f"Rolling accuracy {acc:.1%} below hard floor {self.accuracy_floor_hard:.1%} (n={n})"
        elif acc < self.accuracy_floor_warn:
            sev = Severity.WARNING
            msg = f"Rolling accuracy {acc:.1%} below warning floor {self.accuracy_floor_warn:.1%} (n={n})"
        else:
            sev = Severity.OK
            msg = f"Rolling accuracy {acc:.1%} OK (n={n}, baseline {baseline:.1%})"
        return AccuracyCheck(rolling_accuracy=acc, baseline_accuracy=baseline,
                             n_samples=n, severity=sev, message=msg)

    def check_drift(
        self,
        recent_probs: Optional[List[float]] = None,
        baseline_mean_prob: float = 0.60,
    ) -> DriftCheck:
        """
        Check whether the distribution of predicted probabilities has shifted.
        Uses internal buffer if ``recent_probs`` is not supplied.
        """
        buf = recent_probs if recent_probs is not None else self._recent_probs
        n   = len(buf)
        if n < 10:
            return DriftCheck(
                current_mean_prob=None, baseline_mean_prob=baseline_mean_prob,
                shift=None, n_samples=n, severity=Severity.OK,
                message="Insufficient samples for drift check",
            )
        mean_p = sum(buf) / n
        shift  = abs(mean_p - baseline_mean_prob)
        if shift >= self.drift_hard:
            sev = Severity.STALE
            msg = f"Prob distribution shifted {shift:.2f} (hard limit {self.drift_hard}) vs baseline {baseline_mean_prob:.2f}"
        elif shift >= self.drift_warn:
            sev = Severity.WARNING
            msg = f"Prob distribution shifted {shift:.2f} (warn limit {self.drift_warn}) vs baseline {baseline_mean_prob:.2f}"
        else:
            sev = Severity.OK
            msg = f"Prob distribution shift {shift:.2f} — OK"
        return DriftCheck(current_mean_prob=mean_p, baseline_mean_prob=baseline_mean_prob,
                          shift=shift, n_samples=n, severity=sev, message=msg)

    # ------------------------------------------------------------------
    # Aggregate report
    # ------------------------------------------------------------------

    def check_model(
        self,
        model_path: Optional[str] = None,
        model_name: str = "model",
        baseline_accuracy: float = 0.60,
        baseline_mean_prob: float = 0.60,
        recent_correct: Optional[List[int]] = None,
        recent_probs:   Optional[List[float]] = None,
    ) -> StalenessReport:
        """
        Run all configured checks and return an aggregated StalenessReport.

        Parameters
        ----------
        model_path       : path to the model artifact file (optional)
        model_name       : human-readable name for the model
        baseline_accuracy: expected accuracy from training/validation
        baseline_mean_prob: expected mean predicted probability
        recent_correct   : override for accuracy buffer
        recent_probs     : override for drift buffer
        """
        file_check     = self.check_file_age(model_path) if model_path else None
        accuracy_check = self.check_accuracy(recent_correct, baseline=baseline_accuracy)
        drift_check    = self.check_drift(recent_probs, baseline_mean_prob=baseline_mean_prob)

        # Determine overall severity (worst of all checks)
        severities: List[Severity] = []
        if file_check:     severities.append(file_check.severity)
        if accuracy_check: severities.append(accuracy_check.severity)
        if drift_check:    severities.append(drift_check.severity)

        order = {Severity.OK: 0, Severity.WARNING: 1, Severity.STALE: 2}
        overall = max(severities, key=lambda s: order.get(s, 0)) if severities else Severity.OK
        blocking = (overall == Severity.STALE)

        reasons = []
        if file_check and file_check.severity != Severity.OK:
            reasons.append(file_check.message)
        if accuracy_check and accuracy_check.severity != Severity.OK:
            reasons.append(accuracy_check.message)
        if drift_check and drift_check.severity != Severity.OK:
            reasons.append(drift_check.message)

        return StalenessReport(
            model_name=model_name,
            checked_at=datetime.now(timezone.utc).isoformat(),
            file_check=file_check,
            accuracy_check=accuracy_check,
            drift_check=drift_check,
            overall_severity=overall,
            blocking=blocking,
            reasons=reasons,
        )

    # ------------------------------------------------------------------
    # Bulk check
    # ------------------------------------------------------------------

    def check_many(
        self, model_paths: Dict[str, str], **kwargs
    ) -> Dict[str, StalenessReport]:
        """
        Check multiple model artifacts at once.
        ``model_paths`` = {"model_name": "/path/to/artifact", ...}
        ``kwargs`` are passed to each ``check_model`` call.
        """
        return {
            name: self.check_model(path, model_name=name, **kwargs)
            for name, path in model_paths.items()
        }

    def any_blocking(self, reports: Dict[str, StalenessReport]) -> bool:
        """Return True if any report in the dict requires blocking."""
        return any(r.blocking for r in reports.values())


# ---------------------------------------------------------------------------
# Convenience function: fast is-stale check
# ---------------------------------------------------------------------------

def is_model_stale(
    model_path: str,
    max_age_days: float = DEFAULT_MAX_AGE_DAYS,
    recent_accuracy: Optional[float] = None,
    accuracy_floor: float = DEFAULT_ACCURACY_FLOOR_WARN,
) -> bool:
    """
    Quick yes/no check: is the model stale?

    Parameters
    ----------
    model_path      : path to model artifact
    max_age_days    : age threshold in days
    recent_accuracy : if provided, checked against ``accuracy_floor``
    accuracy_floor  : minimum acceptable accuracy

    Returns
    -------
    True if model should be considered stale.
    """
    detector = ModelStalenessDetector(
        max_age_days_warn=max_age_days,
        max_age_days_hard=max_age_days * 2,
        accuracy_floor_warn=accuracy_floor,
        accuracy_floor_hard=accuracy_floor - 0.10,
    )
    report = detector.check_model(model_path=model_path)
    if recent_accuracy is not None and recent_accuracy < accuracy_floor:
        return True
    return report.overall_severity == Severity.STALE
