"""Tests for:
app/models/staleness.py         (TODO #38 — model staleness detection)
app/models/data_gap_handler.py  (TODO #36 — graceful degradation)
"""

from __future__ import annotations

import os
import time

import pytest

from app.models.data_gap_handler import (
    DataGapHandler,
    infer_available_fields,
)
from app.models.staleness import (
    ModelStalenessDetector,
    Severity,
    StalenessReport,
    is_model_stale,
)

# ===========================================================================
# ModelStalenessDetector
# ===========================================================================


class TestFileAgeCheck:
    def test_missing_file_is_warning(self):
        det = ModelStalenessDetector()
        chk = det.check_file_age("/no/such/file.pkl")
        assert not chk.exists
        assert chk.severity == Severity.WARNING

    def test_fresh_file_is_ok(self, tmp_path):
        f = tmp_path / "model.pkl"
        f.write_bytes(b"x")
        det = ModelStalenessDetector(max_age_days_warn=5)
        chk = det.check_file_age(str(f))
        assert chk.exists
        assert chk.age_days is not None
        assert chk.age_days < 1
        assert chk.severity == Severity.OK

    def test_old_file_is_warning(self, tmp_path):
        f = tmp_path / "old_model.pkl"
        f.write_bytes(b"x")
        # Back-date the file
        old_time = time.time() - (10 * 86_400)      # 10 days ago
        os.utime(str(f), (old_time, old_time))
        det = ModelStalenessDetector(max_age_days_warn=7, max_age_days_hard=20)
        chk = det.check_file_age(str(f))
        assert chk.severity == Severity.WARNING

    def test_very_old_file_is_stale(self, tmp_path):
        f = tmp_path / "stale.pkl"
        f.write_bytes(b"x")
        old_time = time.time() - (35 * 86_400)
        os.utime(str(f), (old_time, old_time))
        det = ModelStalenessDetector(max_age_days_warn=7, max_age_days_hard=30)
        chk = det.check_file_age(str(f))
        assert chk.severity == Severity.STALE


class TestAccuracyCheck:
    def test_no_samples_is_ok(self):
        det = ModelStalenessDetector()
        chk = det.check_accuracy([])
        assert chk.severity == Severity.OK
        assert chk.rolling_accuracy is None

    def test_good_accuracy_ok(self):
        det = ModelStalenessDetector(accuracy_floor_warn=0.55)
        chk = det.check_accuracy([1] * 70 + [0] * 30)  # 70% accuracy
        assert chk.severity == Severity.OK
        assert chk.rolling_accuracy == pytest.approx(0.70)

    def test_below_warn_floor(self):
        det = ModelStalenessDetector(accuracy_floor_warn=0.55, accuracy_floor_hard=0.40)
        chk = det.check_accuracy([1] * 50 + [0] * 50)  # 50%
        assert chk.severity == Severity.WARNING

    def test_below_hard_floor(self):
        det = ModelStalenessDetector(accuracy_floor_warn=0.55, accuracy_floor_hard=0.45)
        chk = det.check_accuracy([1] * 30 + [0] * 70)  # 30%
        assert chk.severity == Severity.STALE


class TestDriftCheck:
    def test_too_few_samples_is_ok(self):
        det = ModelStalenessDetector()
        chk = det.check_drift([0.6, 0.7])
        assert chk.severity == Severity.OK
        assert chk.shift is None

    def test_low_drift_ok(self):
        det = ModelStalenessDetector(drift_warn=0.10)
        probs = [0.62] * 50     # mean = 0.62, baseline = 0.60 → shift = 0.02
        chk = det.check_drift(probs, baseline_mean_prob=0.60)
        assert chk.severity == Severity.OK
        assert chk.shift == pytest.approx(0.02, abs=1e-9)

    def test_medium_drift_warning(self):
        det = ModelStalenessDetector(drift_warn=0.10, drift_hard=0.20)
        probs = [0.75] * 50    # mean = 0.75, baseline = 0.60 → shift = 0.15
        chk = det.check_drift(probs, baseline_mean_prob=0.60)
        assert chk.severity == Severity.WARNING

    def test_high_drift_stale(self):
        det = ModelStalenessDetector(drift_warn=0.10, drift_hard=0.20)
        probs = [0.85] * 50    # shift = 0.25
        chk = det.check_drift(probs, baseline_mean_prob=0.60)
        assert chk.severity == Severity.STALE


class TestRecordPrediction:
    def test_buffer_grows_and_truncates(self):
        det = ModelStalenessDetector(prob_window=5)
        for i in range(10):
            det.record_prediction(0.6, i % 2 == 0)
        assert len(det._recent_correct) == 5
        assert len(det._recent_probs)   == 5

    def test_reset_clears_buffers(self):
        det = ModelStalenessDetector()
        det.record_prediction(0.7, True)
        det.reset_buffers()
        assert det._recent_correct == []
        assert det._recent_probs   == []


class TestAggregateReport:
    def test_ok_report_not_blocking(self, tmp_path):
        f = tmp_path / "fresh.pkl"
        f.write_bytes(b"x")
        det = ModelStalenessDetector()
        report = det.check_model(model_path=str(f), model_name="fresh-model")
        assert isinstance(report, StalenessReport)
        assert not report.blocking
        assert report.overall_severity == Severity.OK

    def test_stale_file_blocking(self, tmp_path):
        f = tmp_path / "stale.pkl"
        f.write_bytes(b"x")
        old_time = time.time() - (35 * 86_400)
        os.utime(str(f), (old_time, old_time))
        det = ModelStalenessDetector(max_age_days_warn=7, max_age_days_hard=30)
        report = det.check_model(model_path=str(f))
        assert report.blocking

    def test_summary_string(self, tmp_path):
        f = tmp_path / "m.pkl"
        f.write_bytes(b"x")
        det = ModelStalenessDetector()
        report = det.check_model(model_path=str(f), model_name="my-model")
        s = report.summary()
        assert "my-model" in s

    def test_check_many(self, tmp_path):
        f = tmp_path / "m.pkl"
        f.write_bytes(b"x")
        det = ModelStalenessDetector()
        reports = det.check_many({"model-a": str(f), "model-b": "/no/file.pkl"})
        assert "model-a" in reports
        assert "model-b" in reports

    def test_any_blocking(self, tmp_path):
        f = tmp_path / "m.pkl"
        f.write_bytes(b"x")
        det = ModelStalenessDetector()
        reports = {"ok": det.check_model(str(f))}
        assert not det.any_blocking(reports)


class TestIsModelStale:
    def test_fresh_file_not_stale(self, tmp_path):
        f = tmp_path / "m.pkl"
        f.write_bytes(b"x")
        assert not is_model_stale(str(f))

    def test_missing_file_not_hard_stale(self):
        # Missing file → WARNING not STALE in default config
        result = is_model_stale("/no/file.pkl")
        assert isinstance(result, bool)

    def test_bad_accuracy_is_stale(self, tmp_path):
        f = tmp_path / "m.pkl"
        f.write_bytes(b"x")
        assert is_model_stale(str(f), recent_accuracy=0.30, accuracy_floor=0.55)


# ===========================================================================
# DataGapHandler
# ===========================================================================


def _pred(confidence: float = 0.72) -> dict:
    return {
        "home_win_prob": 0.55,
        "draw_prob": 0.25,
        "away_win_prob": 0.20,
        "confidence": confidence,
    }


class TestDataGapHandlerNoGaps:
    def test_no_args_returns_unchanged(self):
        handler = DataGapHandler()
        result  = handler.handle(_pred())
        assert not result.degraded
        assert result.gap_report.total_penalty == 0.0

    def test_all_fields_available(self):
        handler = DataGapHandler()
        result  = handler.handle(_pred(), available_fields=list(handler._penalties.keys()))
        assert not result.degraded


class TestDataGapHandlerWithMissing:
    def test_single_missing_field(self):
        handler = DataGapHandler()
        result  = handler.handle(_pred(0.72), missing_fields=["lineup"])
        assert result.degraded
        assert result.gap_report.total_penalty == pytest.approx(0.07)
        assert result.gap_report.adjusted_confidence == pytest.approx(0.72 - 0.07, abs=1e-6)

    def test_multiple_missing_fields(self):
        handler = DataGapHandler()
        result  = handler.handle(_pred(0.80), missing_fields=["lineup", "form"])
        expected_penalty = min(0.07 + 0.08, 0.30)
        assert result.gap_report.total_penalty == pytest.approx(expected_penalty, abs=1e-6)

    def test_penalty_capped_at_max(self):
        handler = DataGapHandler(max_penalty=0.20)
        # Many missing → would exceed 0.20 without cap
        all_fields = list(handler._penalties.keys())
        result = handler.handle(_pred(), missing_fields=all_fields)
        assert result.gap_report.total_penalty <= 0.20 + 1e-9

    def test_is_critical_when_confidence_drops_below_floor(self):
        handler = DataGapHandler(confidence_floor=0.60)
        result  = handler.handle(_pred(0.65), missing_fields=["form"])  # penalty = 0.08
        # 0.65 - 0.08 = 0.57 < 0.60 → critical
        assert result.gap_report.is_critical

    def test_not_critical_when_confidence_stays_above_floor(self):
        handler = DataGapHandler(confidence_floor=0.50)
        result  = handler.handle(_pred(0.80), missing_fields=["venue"])
        # 0.80 - 0.01 = 0.79 > 0.50 → not critical
        assert not result.gap_report.is_critical

    def test_prediction_confidence_key_updated(self):
        handler = DataGapHandler()
        result  = handler.handle(_pred(0.72), missing_fields=["lineup"])
        assert result.prediction["confidence"] == pytest.approx(0.72 - 0.07, abs=1e-6)

    def test_data_gaps_key_added(self):
        handler = DataGapHandler()
        result  = handler.handle(_pred(), missing_fields=["xg", "weather"])
        assert set(result.prediction["data_gaps"]) == {"xg", "weather"}

    def test_degraded_flag_in_prediction(self):
        handler = DataGapHandler()
        result  = handler.handle(_pred(), missing_fields=["referee"])
        assert result.prediction["degraded"] is True

    def test_inferred_missing_from_available(self):
        handler = DataGapHandler()
        # Provide only "lineup" as available → everything else is missing
        result = handler.handle(_pred(0.90), available_fields=["lineup"])
        # Many fields missing → degraded
        assert result.degraded
        assert "lineup" not in result.gap_report.missing_fields

    def test_no_confidence_key_unchanged(self):
        handler = DataGapHandler()
        pred = {"home_win_prob": 0.55}   # no confidence key
        result = handler.handle(pred, missing_fields=["xg"])
        # Should not crash; confidence key not added if absent
        assert "confidence" not in result.prediction


class TestDataGapHandlerShortcuts:
    def test_handle_missing_lineup(self):
        handler = DataGapHandler()
        result  = handler.handle_missing_lineup(_pred(0.75))
        assert result.gap_report.total_penalty == pytest.approx(0.07)

    def test_handle_missing_xg(self):
        handler = DataGapHandler()
        result  = handler.handle_missing_xg(_pred(0.75))
        assert result.gap_report.total_penalty == pytest.approx(0.05)

    def test_handle_missing_form(self):
        handler = DataGapHandler()
        result  = handler.handle_missing_form(_pred(0.75))
        assert result.gap_report.total_penalty == pytest.approx(0.08)


class TestDataGapHandlerBatch:
    def test_batch_length_preserved(self):
        handler = DataGapHandler()
        preds   = [_pred(0.7), _pred(0.6), _pred(0.8)]
        results = handler.handle_batch(preds, missing_fields=["weather"])
        assert len(results) == 3

    def test_batch_all_same_penalty(self):
        handler  = DataGapHandler()
        preds    = [_pred(0.7 + i * 0.01) for i in range(5)]
        results  = handler.handle_batch(preds, missing_fields=["venue"])
        penalties = {r.gap_report.total_penalty for r in results}
        assert len(penalties) == 1   # same penalty for all


class TestDataGapHandlerSummary:
    def test_summary_no_gaps(self):
        handler = DataGapHandler()
        result  = handler.handle(_pred())
        assert "No data gaps" in result.gap_report.summary()

    def test_summary_with_gaps(self):
        handler = DataGapHandler()
        result  = handler.handle(_pred(), missing_fields=["lineup"])
        s = result.gap_report.summary()
        assert "lineup" in s
        assert "→" in s


class TestDataGapHandlerPenaltyTable:
    def test_returns_list(self):
        handler = DataGapHandler()
        table   = handler.penalty_table()
        assert isinstance(table, list)
        assert len(table) > 0
        assert "field" in table[0]
        assert "effective_penalty" in table[0]


class TestInferAvailableFields:
    def test_empty_dict(self):
        assert infer_available_fields({}) == []

    def test_detects_lineup(self):
        assert "lineup" in infer_available_fields({"home_lineup": ["A", "B"]})

    def test_detects_xg(self):
        assert "xg" in infer_available_fields({"home_xg": 1.2, "away_xg": 0.9})

    def test_detects_weather(self):
        assert "weather" in infer_available_fields({"temperature": 15, "precipitation": 0.2})

    def test_detects_form(self):
        assert "form" in infer_available_fields({"home_form": "WWDL", "away_form": "DDDW"})

    def test_detects_multiple(self):
        pred = {"home_xg": 1.2, "referee": "J.Smith", "injuries": []}
        fields = infer_available_fields(pred)
        assert "xg" in fields
        assert "referee" in fields
        assert "injury_news" in fields
