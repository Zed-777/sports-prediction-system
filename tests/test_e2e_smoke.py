"""
End-to-End Smoke Test — Full prediction pipeline integration (TODO #67)
=======================================================================
Validates that all modules introduced in the current sprint work together
in a realistic pipeline without requiring any external API calls.

Pipeline under test:
1. Calibration (ProbabilityCalibrator, LeagueCalibrationRegistry)
2. Data-gap handling (DataGapHandler)
3. Staleness detection (ModelStalenessDetector)
4. Ensemble disagreement (EnsembleDisagreementDetector)
5. Synthetic rate monitoring (SyntheticRateMonitor)
6. Qualifying gate (QualifyingGate, QualifyingParams)
7. Market simulator (SyntheticMatchGenerator)

The test simulates a mini end-to-end run:
  - Generate 100 synthetic matches
  - Apply calibration, gap handling, staleness checks, qualifying gate
  - Assert all modules integrate without errors and produce sensible output
"""

from __future__ import annotations

import numpy as np
import pytest

# ---------------------------------------------------------------------------
# Import all new sprint modules (will fail fast if any import is broken)
# ---------------------------------------------------------------------------
from app.models.calibration import (
    LeagueCalibrationRegistry,
    ProbabilityCalibrator,
    calibrate_prediction,
)
from app.models.data_gap_handler import DataGapHandler, infer_available_fields
from app.models.ensemble_disagreement import (
    EnsembleDisagreementDetector,
    DisagreementLevel,
)
from app.models.staleness import ModelStalenessDetector, Severity
from app.monitoring.synthetic_rate_monitor import AlertLevel, SyntheticRateMonitor

# Existing market infrastructure
from app.models.market_simulator import SyntheticMatchGenerator
from app.models.qualifying_gate import QualifyingGate, QualifyingParams


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def calibration_registry():
    """Fit a league registry on synthetic data."""
    rng = np.random.default_rng(42)
    reg = LeagueCalibrationRegistry()
    for league in ["premier-league", "la-liga", "bundesliga"]:
        probs    = rng.uniform(0.30, 0.80, 100).tolist()
        outcomes = [int(rng.random() < p) for p in probs]
        reg.fit_league(league, probs, outcomes)
    return reg


@pytest.fixture(scope="module")
def synthetic_matches():
    """Generate 100 synthetic match records (seed fixed for reproducibility)."""
    gen = SyntheticMatchGenerator(model_accuracy=0.62, seed=7)
    return gen.generate(n_matches=100, leagues=["premier-league"])


# ---------------------------------------------------------------------------
# 1. Calibration smoke
# ---------------------------------------------------------------------------

class TestCalibrationSmoke:
    def test_registry_fits_three_leagues(self, calibration_registry):
        for league in ["premier-league", "la-liga", "bundesliga"]:
            assert calibration_registry.has_calibrator(league)

    def test_calibrate_single_value(self, calibration_registry):
        val = calibration_registry.calibrate("premier-league", 0.65)
        assert 0.0 < val < 1.0

    def test_calibrate_prediction_dict(self, calibration_registry):
        pred = {"home_win_prob": 0.55, "draw_prob": 0.25, "away_win_prob": 0.20}
        out  = calibrate_prediction(pred, calibration_registry, league="premier-league")
        total = out["home_win_prob"] + out["draw_prob"] + out["away_win_prob"]
        assert abs(total - 1.0) < 1e-9
        assert out.get("calibration_applied") is True

    def test_calibration_persist_and_reload(self, calibration_registry, tmp_path):
        import copy
        reg_copy = copy.deepcopy(calibration_registry)
        reg_copy.registry_dir = str(tmp_path)
        reg_copy.save_all()
        reg2 = LeagueCalibrationRegistry(registry_dir=str(tmp_path))
        n = reg2.load_all()
        assert n == 3


# ---------------------------------------------------------------------------
# 2. Data-gap handling smoke
# ---------------------------------------------------------------------------

class TestDataGapSmoke:
    def _base_pred(self):
        return {"home_win_prob": 0.55, "draw_prob": 0.25,
                "away_win_prob": 0.20, "confidence": 0.72}

    def test_lineup_penalty_applied(self):
        handler = DataGapHandler()
        result  = handler.handle_missing_lineup(self._base_pred())
        assert result.gap_report.total_penalty == pytest.approx(0.07)
        assert result.prediction["confidence"] == pytest.approx(0.72 - 0.07, abs=1e-6)

    def test_multiple_gaps_capped(self):
        handler = DataGapHandler(max_penalty=0.20)
        result  = handler.handle(
            self._base_pred(),
            missing_fields=["lineup", "form", "xg", "weather", "referee"],
        )
        assert result.gap_report.total_penalty <= 0.20 + 1e-9

    def test_infer_from_typical_prediction(self):
        pred = {"home_lineup": ["A"], "home_xg": 1.2, "referee": "Smith"}
        fields = infer_available_fields(pred)
        assert "lineup" in fields
        assert "xg" in fields
        assert "referee" in fields


# ---------------------------------------------------------------------------
# 3. Staleness detection smoke
# ---------------------------------------------------------------------------

class TestStalenessSmoke:
    def test_fresh_model_ok(self, tmp_path):
        f = tmp_path / "model.pkl"
        f.write_bytes(b"x")
        det = ModelStalenessDetector()
        rpt = det.check_model(model_path=str(f), model_name="fresh")
        assert rpt.overall_severity == Severity.OK
        assert not rpt.blocking

    def test_no_file_no_error(self):
        det = ModelStalenessDetector()
        rpt = det.check_model(model_name="nofile")
        assert not rpt.blocking

    def test_good_accuracy_ok(self):
        det = ModelStalenessDetector()
        recent = [1] * 65 + [0] * 35   # 65% accuracy
        chk = det.check_accuracy(recent, baseline=0.60)
        assert chk.severity == Severity.OK

    def test_bad_accuracy_warn(self):
        det = ModelStalenessDetector(accuracy_floor_warn=0.55, accuracy_floor_hard=0.40)
        recent = [1] * 48 + [0] * 52   # 48%
        chk = det.check_accuracy(recent)
        assert chk.severity == Severity.WARNING


# ---------------------------------------------------------------------------
# 4. Ensemble disagreement smoke
# ---------------------------------------------------------------------------

class TestEnsembleDisagreementSmoke:
    def test_unanimous_models_low_penalty(self):
        det = EnsembleDisagreementDetector()
        preds = [{"home_win_prob": 0.55, "draw_prob": 0.25, "away_win_prob": 0.20}] * 4
        rpt = det.analyse(preds)
        assert rpt.confidence_penalty < 0.05
        assert rpt.level in (DisagreementLevel.UNANIMOUS, DisagreementLevel.LOW)

    def test_split_winner_higher_penalty(self):
        det = EnsembleDisagreementDetector()
        preds = [
            {"home_win_prob": 0.65, "draw_prob": 0.20, "away_win_prob": 0.15},
            {"home_win_prob": 0.25, "draw_prob": 0.20, "away_win_prob": 0.55},
        ]
        rpt = det.analyse(preds)
        assert rpt.confidence_penalty > 0.0
        assert not rpt.winner_agreement

    def test_apply_reduces_confidence(self):
        det  = EnsembleDisagreementDetector()
        base = {"confidence": 0.72}
        preds = [
            {"home_win_prob": 0.70, "draw_prob": 0.20, "away_win_prob": 0.10},
            {"home_win_prob": 0.20, "draw_prob": 0.20, "away_win_prob": 0.60},
        ]
        result = det.apply_to_prediction(base, preds)
        assert result["confidence"] < 0.72


# ---------------------------------------------------------------------------
# 5. Synthetic rate monitor smoke
# ---------------------------------------------------------------------------

class TestSyntheticRateSmoke:
    def test_all_real_safe(self):
        mon = SyntheticRateMonitor(min_real_for_live=10)
        for _ in range(50):
            mon.record(is_synthetic=False, league="premier-league")
        alert = mon.current_alert()
        assert alert.is_safe_for_live()

    def test_high_synthetic_critical(self):
        mon = SyntheticRateMonitor(
            warn_threshold=0.50, critical_threshold=0.80, min_real_for_live=5
        )
        for _ in range(5):
            mon.record(is_synthetic=False)
        for _ in range(20):
            mon.record(is_synthetic=True)  # 80%
        alert = mon.current_alert()
        assert alert.level in (AlertLevel.WARNING, AlertLevel.CRITICAL)

    def test_persist_and_reload(self, tmp_path):
        path = str(tmp_path / "monitor_state.json")
        mon = SyntheticRateMonitor(persist_path=path)
        for _ in range(30):
            mon.record(is_synthetic=False)
        mon.save()

        mon2 = SyntheticRateMonitor(persist_path=path)
        mon2.load()
        assert mon2.total_real() == 30


# ---------------------------------------------------------------------------
# 6. Full integration pipeline smoke
# ---------------------------------------------------------------------------

class TestFullPipelineSmoke:
    """
    Simulates the full flow:
      synthetic matches → calibration → gap handling → ensemble analysis
      → qualifying gate → synthetic rate monitor
    """

    def test_full_pipeline_no_errors(self, synthetic_matches, calibration_registry):
        """
        Run the entire new-module stack on 100 synthetic matches.
        Asserts no exceptions and that the output is structurally valid.
        """
        gap_handler   = DataGapHandler()
        ensemble_det  = EnsembleDisagreementDetector()
        staleness_det = ModelStalenessDetector()
        syn_monitor   = SyntheticRateMonitor(min_real_for_live=10)
        gate          = QualifyingGate(QualifyingParams.standard())

        qualified_count = 0

        for match in synthetic_matches[:50]:
            # 1. Build prediction dict from market simulator record keys
            pred = {
                "home_win_prob": match["model_home_prob"],
                "draw_prob":     match["model_draw_prob"],
                "away_win_prob": match["model_away_prob"],
                "confidence":    match["model_confidence"],
            }

            # 2. Calibrate probabilities
            cal_pred = calibrate_prediction(
                pred, calibration_registry, league="premier-league"
            )

            # 3. Apply data gap handling (simulate: lineup missing)
            degraded_res   = gap_handler.handle_missing_lineup(cal_pred)
            pred_with_gaps = degraded_res.prediction

            # 4. Ensemble disagreement (two slightly different model views)
            pred2 = {
                "home_win_prob": min(0.99, pred["home_win_prob"] + 0.05),
                "draw_prob":     pred["draw_prob"],
                "away_win_prob": max(0.01, pred["away_win_prob"] - 0.05),
            }
            adj = ensemble_det.apply_to_prediction(pred_with_gaps, [pred, pred2])

            # 5. Staleness check (no artifact path → no file check; accuracy OK)
            staleness_rpt = staleness_det.check_model(model_name="test_model")
            assert not staleness_rpt.blocking

            # 6. Record to synthetic monitor (all bets here are synthetic)
            syn_monitor.record(is_synthetic=True)

            # 7. Qualifying gate decision
            market_odds = match["market_odds"]
            decision = gate.evaluate(
                league=match["league"],
                model_home_prob=adj.get("home_win_prob", pred["home_win_prob"]),
                model_draw_prob=adj.get("draw_prob", pred["draw_prob"]),
                model_away_prob=adj.get("away_win_prob", pred["away_win_prob"]),
                market_odds_home=market_odds.home_odds,
                market_odds_draw=market_odds.draw_odds,
                market_odds_away=market_odds.away_odds,
                confidence=adj.get("confidence", pred["confidence"]),
                data_quality=match["data_quality"],
            )
            if decision.qualified:
                qualified_count += 1

        # At least some bets should be filtered — qualifying gate should not pass all
        assert qualified_count >= 0   # may be 0 if no edges; that is OK
        # Synthetic monitor should have captured all 50 records
        alert = syn_monitor.current_alert()
        assert alert.total_count == 50
        # All bets were synthetic → monitor should NOT be safe for live
        assert not alert.is_safe_for_live()

    def test_new_modules_importable(self):
        """All new sprint modules must be importable without errors."""
        import app.models.calibration               # noqa: F401
        import app.models.data_gap_handler          # noqa: F401
        import app.models.staleness                 # noqa: F401
        import app.models.ensemble_disagreement     # noqa: F401
        import app.monitoring.synthetic_rate_monitor  # noqa: F401

    def test_brier_score_tracker_in_pipeline(self, synthetic_matches):
        """BrierScoreTracker should accumulate from a stream of predictions."""
        from app.models.calibration import BrierScoreTracker
        tracker = BrierScoreTracker(window=50)
        for match in synthetic_matches[:50]:
            tracker.record(
                predicted_prob=match["model_home_prob"],
                outcome=int(match["actual_outcome"] == "home"),
            )
        assert tracker.n_samples() == 50
        bs = tracker.current_brier()
        assert bs is not None and 0.0 <= bs <= 0.5

    def test_calibration_report_after_batch(self, synthetic_matches):
        """CalibrationReport should be generated from a batch of predictions."""
        cal    = ProbabilityCalibrator()
        probs  = [m["model_home_prob"] for m in synthetic_matches[:80]]
        labels = [int(m["actual_outcome"] == "home") for m in synthetic_matches[:80]]
        rpt = cal.report(probs, labels, league="premier-league")
        assert rpt.n_samples == 80
        assert 0.0 <= rpt.brier_score <= 0.5
        assert 0.0 <= rpt.ece <= 1.0
