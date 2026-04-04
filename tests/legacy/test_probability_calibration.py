"""Tests for app/models/calibration.py  (TODO #24, #27, #34)
Isotonic regression, Brier score, ECE, league registry, BrierScoreTracker.
"""

from __future__ import annotations

import json
import math

import numpy as np
import pytest

from app.models.calibration import (
    BrierScoreTracker,
    CalibrationReport,
    LeagueCalibrationRegistry,
    ProbabilityCalibrator,
    calibrate_prediction,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _perfect_probs(n: int = 100, seed: int = 0):
    rng = np.random.default_rng(seed)
    probs = rng.uniform(0.2, 0.9, n).tolist()
    outcomes = [int(rng.random() < p) for p in probs]
    return probs, outcomes


def _overconfident_probs(n: int = 100, seed: int = 1):
    rng = np.random.default_rng(seed)
    probs = rng.uniform(0.70, 0.95, n).tolist()
    outcomes = [int(rng.random() < 0.50) for _ in probs]
    return probs, outcomes


def _underconfident_probs(n: int = 100, seed: int = 2):
    rng = np.random.default_rng(seed)
    probs = rng.uniform(0.50, 0.55, n).tolist()
    outcomes = [int(rng.random() < 0.70) for _ in probs]
    return probs, outcomes


# ---------------------------------------------------------------------------
# Brier score
# ---------------------------------------------------------------------------


class TestBrierScore:
    def test_perfect_prediction(self):
        assert ProbabilityCalibrator.brier_score([1.0, 0.0, 1.0], [1, 0, 1]) == pytest.approx(0.0)

    def test_worst_prediction(self):
        assert ProbabilityCalibrator.brier_score([0.0, 1.0], [1, 0]) == pytest.approx(1.0)

    def test_midpoint_baseline(self):
        bs = ProbabilityCalibrator.brier_score([0.5] * 100, [1] * 50 + [0] * 50)
        assert bs == pytest.approx(0.25, abs=1e-10)

    def test_empty_returns_nan(self):
        assert math.isnan(ProbabilityCalibrator.brier_score([], []))

    def test_bss_perfect_model(self):
        outcomes = [1] * 50 + [0] * 50
        probs = [float(o) for o in outcomes]
        bss = ProbabilityCalibrator.brier_skill_score(probs, outcomes)
        assert bss == pytest.approx(1.0, abs=1e-6)

    def test_bss_climatology(self):
        outcomes = [1] * 60 + [0] * 40
        probs = [0.6] * 100
        bss = ProbabilityCalibrator.brier_skill_score(probs, outcomes)
        assert bss == pytest.approx(0.0, abs=1e-9)

    def test_bss_overconfident_is_float(self):
        probs, outcomes = _overconfident_probs(200)
        bss = ProbabilityCalibrator.brier_skill_score(probs, outcomes)
        assert isinstance(bss, float)


class TestLogLoss:
    def test_near_perfect(self):
        ll = ProbabilityCalibrator.log_loss([0.9999, 0.0001], [1, 0])
        assert ll < 0.001

    def test_empty_returns_nan(self):
        assert math.isnan(ProbabilityCalibrator.log_loss([], []))


# ---------------------------------------------------------------------------
# ProbabilityCalibrator — fitting and inference
# ---------------------------------------------------------------------------


class TestCalibration:
    def test_insufficient_samples_unfitted(self):
        cal = ProbabilityCalibrator()
        cal.fit([0.6, 0.7], [1, 0])
        assert not cal.is_fitted
        assert cal.calibrate_single(0.6) == pytest.approx(0.6, abs=1e-6)

    def test_sufficient_samples_fitted(self):
        probs, outcomes = _perfect_probs(50)
        cal = ProbabilityCalibrator()
        cal.fit(probs, outcomes)
        assert cal.is_fitted

    def test_calibration_is_monotone(self):
        probs, outcomes = _overconfident_probs(120)
        cal = ProbabilityCalibrator()
        cal.fit(probs, outcomes)
        assert cal.is_fitted
        test_ps = [0.30, 0.45, 0.55, 0.65, 0.75, 0.85, 0.92]
        cal_ps = [cal.calibrate_single(p) for p in test_ps]
        for a, b in zip(cal_ps, cal_ps[1:]):
            assert a <= b + 1e-9, f"non-monotone: {a} > {b}"

    def test_calibrated_ece_not_worse(self):
        probs, outcomes = _overconfident_probs(200)
        cal = ProbabilityCalibrator()
        cal.fit(probs[:150], outcomes[:150])
        raw_ece = cal.ece(probs[150:], outcomes[150:])
        cal_probs = list(cal.calibrate(probs[150:]))
        cal_ece = cal.ece(cal_probs, outcomes[150:])
        assert cal_ece <= raw_ece + 0.05   # calibrated should be ≤ raw (small tolerance)

    def test_calibrate_batch_length_preserved(self):
        probs, outcomes = _perfect_probs(50)
        cal = ProbabilityCalibrator()
        cal.fit(probs, outcomes)
        result = cal.calibrate(probs)
        assert len(result) == len(probs)

    def test_calibrate_clamps_extreme_inputs(self):
        probs, outcomes = _perfect_probs(50)
        cal = ProbabilityCalibrator()
        cal.fit(probs, outcomes)
        assert 0 < cal.calibrate_single(0.0) < 1
        assert 0 < cal.calibrate_single(1.0) < 1

    def test_ece_well_calibrated_model(self):
        probs, outcomes = _perfect_probs(200)
        cal = ProbabilityCalibrator()
        ece = cal.ece(probs, outcomes)
        assert ece < 0.15

    def test_report_structure_and_types(self):
        probs, outcomes = _perfect_probs(50)
        cal = ProbabilityCalibrator()
        rpt = cal.report(probs, outcomes, league="test-league")
        assert isinstance(rpt, CalibrationReport)
        assert rpt.n_samples == 50
        assert isinstance(rpt.brier_score, float)
        assert rpt.league == "test-league"
        assert isinstance(rpt.reliability_bins, list)

    def test_report_summary_contains_metrics(self):
        probs, outcomes = _perfect_probs(40)
        cal = ProbabilityCalibrator()
        s = cal.report(probs, outcomes).summary()
        assert "Brier=" in s
        assert "ECE=" in s


# ---------------------------------------------------------------------------
# Persistence round-trip
# ---------------------------------------------------------------------------


class TestPersistence:
    def test_fitted_round_trip(self, tmp_path):
        probs, outcomes = _perfect_probs(60)
        cal = ProbabilityCalibrator()
        cal.fit(probs, outcomes)
        assert cal.is_fitted

        path = str(tmp_path / "cal.json")
        with open(path, "w") as fh:
            json.dump(cal.to_dict(), fh)
        with open(path) as fh:
            data = json.load(fh)
        cal2 = ProbabilityCalibrator.from_dict(data)

        assert cal2.is_fitted
        for p in [0.3, 0.5, 0.7, 0.9]:
            assert abs(cal.calibrate_single(p) - cal2.calibrate_single(p)) < 1e-6

    def test_unfitted_round_trip(self):
        cal = ProbabilityCalibrator()
        cal2 = ProbabilityCalibrator.from_dict(cal.to_dict())
        assert not cal2.is_fitted


# ---------------------------------------------------------------------------
# LeagueCalibrationRegistry
# ---------------------------------------------------------------------------


class TestLeagueCalibrationRegistry:
    def test_fit_single_league(self):
        reg = LeagueCalibrationRegistry()
        probs, outcomes = _perfect_probs(60)
        assert reg.fit_league("premier-league", probs, outcomes)
        assert reg.has_calibrator("premier-league")

    def test_insufficient_samples_not_fitted(self):
        reg = LeagueCalibrationRegistry()
        assert not reg.fit_league("tiny", [0.6], [1])
        assert not reg.has_calibrator("tiny")

    def test_unknown_league_passthrough(self):
        reg = LeagueCalibrationRegistry()
        assert reg.calibrate("unknown", 0.72) == pytest.approx(0.72, abs=1e-6)

    def test_calibrate_batch(self):
        reg = LeagueCalibrationRegistry()
        probs, outcomes = _perfect_probs(60)
        reg.fit_league("la-liga", probs, outcomes)
        result = reg.calibrate_batch("la-liga", probs[:5])
        assert len(result) == 5

    def test_fit_all(self):
        reg = LeagueCalibrationRegistry()
        data = {
            "premier-league": _perfect_probs(60),
            "la-liga": _perfect_probs(60, seed=5),
        }
        reg.fit_all(data)
        assert reg.has_calibrator("premier-league")
        assert reg.has_calibrator("la-liga")
        assert set(reg.leagues()) == {"premier-league", "la-liga"}

    def test_save_and_reload(self, tmp_path):
        reg = LeagueCalibrationRegistry(registry_dir=str(tmp_path))
        probs, outcomes = _perfect_probs(60)
        reg.fit_league("bundesliga", probs, outcomes)
        reg.save_all()

        reg2 = LeagueCalibrationRegistry(registry_dir=str(tmp_path))
        n = reg2.load_all()
        assert n == 1
        assert reg2.has_calibrator("bundesliga")

    def test_load_empty_dir(self, tmp_path):
        reg = LeagueCalibrationRegistry(registry_dir=str(tmp_path))
        assert reg.load_all() == 0

    def test_load_nonexistent_dir(self):
        reg = LeagueCalibrationRegistry(registry_dir="/no/such/dir/xyz")
        assert reg.load_all() == 0

    def test_corrupt_file_skipped(self, tmp_path):
        (tmp_path / "bad.json").write_text("not json {{")
        reg = LeagueCalibrationRegistry(registry_dir=str(tmp_path))
        assert reg.load_all() == 0   # corrupt file silently skipped

    def test_report_all_calibrated(self):
        reg = LeagueCalibrationRegistry()
        probs, outcomes = _perfect_probs(60)
        reg.fit_league("serie-a", probs, outcomes)
        reports = reg.report_all({"serie-a": (probs[:30], outcomes[:30])})
        assert "serie-a" in reports
        assert reports["serie-a"].is_calibrated

    def test_report_all_uncalibrated_league(self):
        reg = LeagueCalibrationRegistry()
        probs, outcomes = _perfect_probs(30)
        reports = reg.report_all({"ligue-1": (probs, outcomes)})
        assert not reports["ligue-1"].is_calibrated


# ---------------------------------------------------------------------------
# BrierScoreTracker
# ---------------------------------------------------------------------------


class TestBrierScoreTracker:
    def test_empty_returns_none(self):
        t = BrierScoreTracker()
        assert t.current_brier() is None
        assert t.current_bss() is None
        assert t.current_log_loss() is None

    def test_records_and_computes(self):
        t = BrierScoreTracker(window=50)
        rng = np.random.default_rng(3)
        for _ in range(30):
            p = float(rng.uniform(0.4, 0.8))
            y = int(rng.random() < p)
            t.record(p, y)
        assert t.n_samples() == 30
        b = t.current_brier()
        assert b is not None and 0.0 <= b <= 0.5

    def test_window_truncates(self):
        t = BrierScoreTracker(window=10)
        for i in range(25):
            t.record(0.5, i % 2)
        assert t.n_samples() == 10

    def test_to_dict_keys(self):
        t = BrierScoreTracker()
        t.record(0.7, 1)
        d = t.to_dict()
        assert {"brier_score", "brier_skill_score", "log_loss", "n_samples"}.issubset(d)


# ---------------------------------------------------------------------------
# calibrate_prediction helper
# ---------------------------------------------------------------------------


class TestCalibratePrediction:
    def _reg(self, league: str = "test") -> LeagueCalibrationRegistry:
        reg = LeagueCalibrationRegistry()
        reg.fit_league(league, *_perfect_probs(80))
        return reg

    def test_adds_calibration_flag(self):
        pred = {"home_win_prob": 0.55, "draw_prob": 0.25, "away_win_prob": 0.20}
        out = calibrate_prediction(pred, self._reg(), league="test")
        assert out.get("calibration_applied") is True
        assert out.get("calibration_league") == "test"

    def test_probs_sum_to_one(self):
        pred = {"home_win_prob": 0.55, "draw_prob": 0.25, "away_win_prob": 0.20}
        out = calibrate_prediction(pred, self._reg(), league="test")
        total = out["home_win_prob"] + out["draw_prob"] + out["away_win_prob"]
        assert total == pytest.approx(1.0, abs=1e-9)

    def test_no_registry_passthrough(self):
        pred = {"home_win_prob": 0.55, "draw_prob": 0.25, "away_win_prob": 0.20}
        assert calibrate_prediction(pred, None, league="x") == pred

    def test_unknown_league_passthrough(self):
        pred = {"home_win_prob": 0.55, "draw_prob": 0.25, "away_win_prob": 0.20}
        out = calibrate_prediction(pred, self._reg("known"), league="unknown")
        assert "calibration_applied" not in out

    def test_no_league_passthrough(self):
        pred = {"home_win_prob": 0.6, "draw_prob": 0.2, "away_win_prob": 0.2}
        out = calibrate_prediction(pred, self._reg(), league=None)
        assert out == pred
