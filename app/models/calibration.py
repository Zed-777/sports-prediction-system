"""Probability Calibration Suite (TODO #24, #27, #34)
====================================================
Isotonic-regression probability calibration, Brier-score tracking, Expected
Calibration Error (ECE), and per-league calibration registries.

Why calibration matters for profitable betting
-----------------------------------------------
Edge = model_prob - market_prob.
If our raw probabilities are systematically biased (e.g. we over-state confidence
on heavy favourites), the calculated edge is wrong, qualifying bets bleed EV, and
the live-trading validator is fooled.

Isotonic regression learns a monotone mapping  raw_prob → calibrated_prob  from
historical (prob, outcome) pairs, fixing over/under-confidence in a data-driven way.

Typical usage
-------------
    cal = ProbabilityCalibrator()
    cal.fit(probs_train, outcomes_train)          # list[float], list[int] (0/1)
    cal_prob = cal.calibrate_single(raw_prob)     # use before edge calc

    reg = LeagueCalibrationRegistry()
    reg.fit_league("premier-league", probs, outcomes)
    cal_prob = reg.calibrate("premier-league", raw_prob)
    reg.save_all()                                 # persists to models/calibration/
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from sklearn.isotonic import IsotonicRegression

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_CALIBRATION_DIR = os.path.join("models", "calibration")
MIN_SAMPLES_FOR_FIT = 20          # need at minimum N samples to fit a calibrator
DEFAULT_ECE_BINS = 10


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ReliabilityBin:
    """One bin of a reliability diagram."""

    bin_lower: float
    bin_upper: float
    mean_predicted_prob: float
    mean_actual_prob: float
    n_samples: int
    calibration_error: float      # |mean_predicted - mean_actual|


@dataclass
class CalibrationReport:
    """Full calibration quality report for a set of (prob, outcome) pairs."""

    n_samples: int
    brier_score: float            # lower is better; perfect = 0, baseline = 0.25
    brier_skill_score: float      # 1 - BS/BS_reference; > 0 = better than climatology
    ece: float                    # Expected Calibration Error (0-1, lower better)
    mce: float                    # Maximum Calibration Error
    log_loss: float               # cross-entropy loss
    reliability_bins: list[ReliabilityBin]
    is_calibrated: bool           # True if fitted calibrator was applied
    league: str | None = None

    def summary(self) -> str:
        status = "CALIBRATED" if self.is_calibrated else "RAW"
        return (
            f"[{status}] n={self.n_samples} | "
            f"Brier={self.brier_score:.4f} (skill={self.brier_skill_score:+.3f}) | "
            f"ECE={self.ece:.4f} | MCE={self.mce:.4f} | LogLoss={self.log_loss:.4f}"
        )


# ---------------------------------------------------------------------------
# Core calibrator
# ---------------------------------------------------------------------------

class ProbabilityCalibrator:
    """Wraps sklearn IsotonicRegression to provide probability calibration with
    built-in Brier score / ECE diagnostics.

    The calibrator is lazy: it returns raw probabilities until ``fit()`` is
    called with at least MIN_SAMPLES_FOR_FIT samples.
    """

    def __init__(self, n_ece_bins: int = DEFAULT_ECE_BINS) -> None:
        self.n_ece_bins = n_ece_bins
        self._iso: IsotonicRegression | None = None
        self._is_fitted: bool = False
        self._n_train: int = 0

    # ------------------------------------------------------------------
    # Fitting
    # ------------------------------------------------------------------

    def fit(self, probs: list[float], outcomes: list[int]) -> ProbabilityCalibrator:
        """Fit isotonic regression on (prob, outcome) pairs.

        Parameters
        ----------
        probs    : raw model probabilities for the selected outcome (0-1)
        outcomes : 1 if selected outcome occurred, 0 otherwise

        """
        if len(probs) < MIN_SAMPLES_FOR_FIT:
            # Not enough data — stay un-fitted; calibrate() will pass through
            self._is_fitted = False
            return self

        X = np.array(probs, dtype=float).clip(1e-7, 1 - 1e-7)
        y = np.array(outcomes, dtype=float)

        self._iso = IsotonicRegression(out_of_bounds="clip", increasing=True)
        self._iso.fit(X, y)
        self._is_fitted = True
        self._n_train = len(probs)
        return self

    # ------------------------------------------------------------------
    # Calibration
    # ------------------------------------------------------------------

    def calibrate(self, probs: list[float]) -> np.ndarray:
        """Apply calibration to a list of probabilities.
        Returns raw probs unchanged if not yet fitted.
        """
        arr = np.array(probs, dtype=float).clip(1e-7, 1 - 1e-7)
        if not self._is_fitted or self._iso is None:
            return arr
        return self._iso.predict(arr).clip(1e-7, 1 - 1e-7)

    def calibrate_single(self, prob: float) -> float:
        """Convenience wrapper for a single probability."""
        return float(self.calibrate([prob])[0])

    @property
    def is_fitted(self) -> bool:
        return self._is_fitted

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    @staticmethod
    def brier_score(probs: list[float], outcomes: list[int]) -> float:
        """Mean squared error between predicted probabilities and binary outcomes."""
        if not probs:
            return float("nan")
        ps = np.array(probs, dtype=float)
        ys = np.array(outcomes, dtype=float)
        return float(np.mean((ps - ys) ** 2))

    @staticmethod
    def brier_skill_score(probs: list[float], outcomes: list[int]) -> float:
        """Brier Skill Score = 1 - BS(model) / BS(climatology).
        Climatology (no-skill) uses the base rate as prediction for every sample.
        Positive = better than climatology.
        """
        if not probs:
            return float("nan")
        bs = ProbabilityCalibrator.brier_score(probs, outcomes)
        base_rate = float(np.mean(outcomes))
        bs_ref = float(np.mean((base_rate - np.array(outcomes, dtype=float)) ** 2))
        if bs_ref == 0.0:
            return 0.0
        return float(1.0 - bs / bs_ref)

    @staticmethod
    def log_loss(probs: list[float], outcomes: list[int]) -> float:
        """Binary cross-entropy."""
        if not probs:
            return float("nan")
        ps = np.clip(probs, 1e-15, 1 - 1e-15)
        ys = np.array(outcomes, dtype=float)
        return float(-np.mean(ys * np.log(ps) + (1 - ys) * np.log(1 - ps)))

    def ece(self, probs: list[float], outcomes: list[int]) -> float:
        """Expected Calibration Error (equal-width bins, weighted by frequency)."""
        bins = self._reliability_bins(probs, outcomes)
        total = sum(b.n_samples for b in bins)
        if total == 0:
            return float("nan")
        return float(sum(b.calibration_error * b.n_samples for b in bins) / total)

    def mce(self, probs: list[float], outcomes: list[int]) -> float:
        """Maximum Calibration Error across bins."""
        bins = self._reliability_bins(probs, outcomes)
        if not bins:
            return float("nan")
        return float(max(b.calibration_error for b in bins))

    def _reliability_bins(
        self, probs: list[float], outcomes: list[int],
    ) -> list[ReliabilityBin]:
        ps = np.array(probs, dtype=float)
        ys = np.array(outcomes, dtype=float)
        bins: list[ReliabilityBin] = []
        edges = np.linspace(0.0, 1.0, self.n_ece_bins + 1)
        for lo, hi in zip(edges[:-1], edges[1:]):
            mask = (ps >= lo) & (ps < hi if hi < 1.0 else ps <= hi)
            n = int(mask.sum())
            if n == 0:
                continue
            mean_p = float(ps[mask].mean())
            mean_y = float(ys[mask].mean())
            bins.append(
                ReliabilityBin(
                    bin_lower=float(lo),
                    bin_upper=float(hi),
                    mean_predicted_prob=mean_p,
                    mean_actual_prob=mean_y,
                    n_samples=n,
                    calibration_error=abs(mean_p - mean_y),
                ),
            )
        return bins

    def report(
        self,
        probs: list[float],
        outcomes: list[int],
        league: str | None = None,
        already_calibrated: bool = False,
    ) -> CalibrationReport:
        """Produce a full CalibrationReport for the given (prob, outcome) pairs."""
        bins = self._reliability_bins(probs, outcomes)
        total_n = sum(b.n_samples for b in bins)
        ece_val = (
            float(sum(b.calibration_error * b.n_samples for b in bins) / total_n)
            if total_n > 0
            else float("nan")
        )
        mce_val = float(max(b.calibration_error for b in bins)) if bins else float("nan")
        return CalibrationReport(
            n_samples=len(probs),
            brier_score=self.brier_score(probs, outcomes),
            brier_skill_score=self.brier_skill_score(probs, outcomes),
            ece=ece_val,
            mce=mce_val,
            log_loss=self.log_loss(probs, outcomes),
            reliability_bins=bins,
            is_calibrated=already_calibrated,
            league=league,
        )

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Serialise to a plain dict (json-safe)."""
        if not self._is_fitted or self._iso is None:
            return {"fitted": False}
        return {
            "fitted": True,
            "n_train": self._n_train,
            "x_thresholds": self._iso.X_thresholds_.tolist(),
            "y_thresholds": self._iso.y_thresholds_.tolist(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> ProbabilityCalibrator:
        cal = cls()
        if not data.get("fitted"):
            return cal
        iso = IsotonicRegression(out_of_bounds="clip", increasing=True)
        x = np.array(data["x_thresholds"])
        y = np.array(data["y_thresholds"])
        # Reconstruct by fitting on the threshold pairs (lossless round-trip)
        iso.fit(x, y)
        cal._iso = iso
        cal._is_fitted = True
        cal._n_train = data.get("n_train", 0)
        return cal


# ---------------------------------------------------------------------------
# League calibration registry
# ---------------------------------------------------------------------------

class LeagueCalibrationRegistry:
    """Maintains one ``ProbabilityCalibrator`` per league, with persistence to
    ``models/calibration/<league>.json``.

    Usage
    -----
        reg = LeagueCalibrationRegistry()
        reg.fit_league("premier-league", probs, outcomes)
        cal_p = reg.calibrate("premier-league", 0.62)
        reg.save_all()

        reg2 = LeagueCalibrationRegistry()
        reg2.load_all()          # restores from disk
    """

    def __init__(self, registry_dir: str = DEFAULT_CALIBRATION_DIR) -> None:
        self.registry_dir = registry_dir
        self._calibrators: dict[str, ProbabilityCalibrator] = {}

    # ------------------------------------------------------------------
    # Fitting
    # ------------------------------------------------------------------

    def fit_league(
        self, league: str, probs: list[float], outcomes: list[int],
    ) -> bool:
        """Fit (or refit) the calibrator for a league.
        Returns True if calibrator was successfully fitted.
        """
        cal = ProbabilityCalibrator()
        cal.fit(probs, outcomes)
        self._calibrators[league] = cal
        return cal.is_fitted

    def fit_all(self, data: dict[str, tuple[list[float], list[int]]]) -> None:
        """Fit all leagues at once.
        data = {"premier-league": ([probs], [outcomes]), ...}
        """
        for league, (probs, outcomes) in data.items():
            self.fit_league(league, probs, outcomes)

    # ------------------------------------------------------------------
    # Calibration
    # ------------------------------------------------------------------

    def calibrate(self, league: str, raw_prob: float) -> float:
        """Return calibrated probability for the given league.
        Falls back to raw_prob if no fitted calibrator exists for the league
        (graceful degradation: no exception thrown).
        """
        cal = self._calibrators.get(league)
        if cal is None or not cal.is_fitted:
            return float(np.clip(raw_prob, 1e-7, 1 - 1e-7))
        return cal.calibrate_single(raw_prob)

    def calibrate_batch(self, league: str, probs: list[float]) -> list[float]:
        """Batch calibration for a list of probabilities."""
        cal = self._calibrators.get(league)
        if cal is None or not cal.is_fitted:
            return list(np.clip(probs, 1e-7, 1 - 1e-7))
        return list(cal.calibrate(probs))

    def has_calibrator(self, league: str) -> bool:
        cal = self._calibrators.get(league)
        return cal is not None and cal.is_fitted

    def leagues(self) -> list[str]:
        return list(self._calibrators.keys())

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def report_all(
        self,
        data: dict[str, tuple[list[float], list[int]]],
    ) -> dict[str, CalibrationReport]:
        """Produce calibration reports for all leagues.
        ``data`` = {"league": ([probs], [outcomes])}
        Reports are produced for *calibrated* probs where a calibrator exists.
        """
        reports = {}
        for league, (probs, outcomes) in data.items():
            cal = self._calibrators.get(league)
            if cal is not None and cal.is_fitted:
                cal_probs = list(cal.calibrate(probs))
                report = cal.report(cal_probs, outcomes, league=league, already_calibrated=True)
            else:
                dummy = ProbabilityCalibrator()
                report = dummy.report(probs, outcomes, league=league, already_calibrated=False)
            reports[league] = report
        return reports

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save_all(self) -> None:
        """Persist all calibrators to ``registry_dir``."""
        Path(self.registry_dir).mkdir(parents=True, exist_ok=True)
        for league, cal in self._calibrators.items():
            path = os.path.join(self.registry_dir, f"{league}.json")
            with open(path, "w") as fh:
                json.dump(cal.to_dict(), fh, indent=2)

    def load_all(self) -> int:
        """Load all calibrators from ``registry_dir``.
        Returns the number of fitted calibrators loaded.
        """
        if not os.path.isdir(self.registry_dir):
            return 0
        loaded = 0
        for fname in os.listdir(self.registry_dir):
            if not fname.endswith(".json"):
                continue
            league = fname[:-5]
            path = os.path.join(self.registry_dir, fname)
            try:
                with open(path) as fh:
                    data = json.load(fh)
                cal = ProbabilityCalibrator.from_dict(data)
                self._calibrators[league] = cal
                if cal.is_fitted:
                    loaded += 1
            except Exception:  # noqa: BLE001
                pass  # corrupt file — skip gracefully
        return loaded


# ---------------------------------------------------------------------------
# Brier score tracker (lightweight ring-buffer for monitoring)
# ---------------------------------------------------------------------------

class BrierScoreTracker:
    """Lightweight rolling Brier score tracker.
    Designed to be integrated with PerformanceMonitor for real-time monitoring.

    Usage
    -----
        tracker = BrierScoreTracker(window=200)
        tracker.record(predicted_prob=0.65, outcome=1)
        print(tracker.current_brier())
        print(tracker.current_bss())   # Brier Skill Score vs climatology
    """

    def __init__(self, window: int = 200) -> None:
        self.window = window
        self._buffer: list = []  # list of (pred_prob, outcome)

    def record(self, predicted_prob: float, outcome: int) -> None:
        self._buffer.append((float(predicted_prob), int(outcome)))
        if len(self._buffer) > self.window:
            self._buffer.pop(0)

    def current_brier(self) -> float | None:
        if not self._buffer:
            return None
        ps = [x[0] for x in self._buffer]
        ys = [x[1] for x in self._buffer]
        return ProbabilityCalibrator.brier_score(ps, ys)

    def current_bss(self) -> float | None:
        if not self._buffer:
            return None
        ps = [x[0] for x in self._buffer]
        ys = [x[1] for x in self._buffer]
        return ProbabilityCalibrator.brier_skill_score(ps, ys)

    def current_log_loss(self) -> float | None:
        if not self._buffer:
            return None
        ps = [x[0] for x in self._buffer]
        ys = [x[1] for x in self._buffer]
        return ProbabilityCalibrator.log_loss(ps, ys)

    def n_samples(self) -> int:
        return len(self._buffer)

    def to_dict(self) -> dict:
        return {
            "n_samples": self.n_samples(),
            "brier_score": self.current_brier(),
            "brier_skill_score": self.current_bss(),
            "log_loss": self.current_log_loss(),
        }


# ---------------------------------------------------------------------------
# Integration helper: calibrate a single prediction dict
# ---------------------------------------------------------------------------

def calibrate_prediction(
    prediction: dict,
    registry: LeagueCalibrationRegistry | None,
    league: str | None = None,
) -> dict:
    """Take a prediction dict (containing keys ``home_win_prob``, ``draw_prob``,
    ``away_win_prob``) and return a new dict with calibrated probabilities.

    If no registry or no fitted calibrator for the league, returns prediction
    unchanged (graceful degradation — #36).

    The three calibrated probs are re-normalised to sum to 1.
    """
    if registry is None or not league:
        return prediction

    out = dict(prediction)
    raw_h = float(prediction.get("home_win_prob", 0.0))
    raw_d = float(prediction.get("draw_prob", 0.0))
    raw_a = float(prediction.get("away_win_prob", 0.0))

    if not registry.has_calibrator(league):
        return out

    cal_h = registry.calibrate(league, raw_h)
    cal_d = registry.calibrate(league, raw_d)
    cal_a = registry.calibrate(league, raw_a)

    total = cal_h + cal_d + cal_a
    if total <= 0:
        return out   # safety

    out["home_win_prob"] = cal_h / total
    out["draw_prob"] = cal_d / total
    out["away_win_prob"] = cal_a / total
    out["calibration_applied"] = True
    out["calibration_league"] = league
    return out
