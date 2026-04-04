"""Tests for app/monitoring/synthetic_rate_monitor.py (TODO #49)
"""

from __future__ import annotations

import pytest

from app.monitoring.synthetic_rate_monitor import (
    AlertLevel,
    SyntheticRateAlert,
    SyntheticRateMonitor,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _monitor(**kwargs) -> SyntheticRateMonitor:
    defaults = dict(warn_threshold=0.50, critical_threshold=0.80, min_real_for_live=10)
    defaults.update(kwargs)
    return SyntheticRateMonitor(**defaults)


def _fill(mon: SyntheticRateMonitor, n_real: int, n_synthetic: int, league: str = "pl") -> None:
    for _ in range(n_real):
        mon.record(is_synthetic=False, league=league)
    for _ in range(n_synthetic):
        mon.record(is_synthetic=True, league=league)


# ---------------------------------------------------------------------------
# Basic recording
# ---------------------------------------------------------------------------


class TestRecording:
    def test_empty_monitor(self):
        mon = _monitor()
        assert mon.rolling_synthetic_rate() is None
        assert mon.total_real() == 0
        assert mon.total_synthetic() == 0
        assert mon.n_recorded() == 0

    def test_single_real(self):
        mon = _monitor()
        mon.record(is_synthetic=False)
        assert mon.total_real() == 1
        assert mon.total_synthetic() == 0
        assert mon.rolling_synthetic_rate() == pytest.approx(0.0)

    def test_single_synthetic(self):
        mon = _monitor()
        mon.record(is_synthetic=True)
        assert mon.total_real() == 0
        assert mon.total_synthetic() == 1
        assert mon.rolling_synthetic_rate() == pytest.approx(1.0)

    def test_mixed_rate(self):
        mon = _monitor()
        _fill(mon, n_real=60, n_synthetic=40)
        assert mon.rolling_synthetic_rate() == pytest.approx(0.40)
        assert mon.total_real() == 60
        assert mon.total_synthetic() == 40
        assert mon.n_recorded() == 100

    def test_window_caps_rolling_buffer(self):
        mon = _monitor(window=10)
        _fill(mon, n_real=20, n_synthetic=0)
        # All-time counters not capped
        assert mon.total_real() == 20
        # Rolling rate looks at last 10 only → still 0% synthetic
        assert mon.rolling_synthetic_rate() == pytest.approx(0.0)


class TestRecordBatch:
    def test_batch_recording(self):
        mon = _monitor()
        records = [
            {"is_synthetic": False, "league": "prem"},
            {"is_synthetic": True,  "league": "la-liga"},
            {"is_synthetic": False, "league": "prem"},
        ]
        mon.record_batch(records)
        assert mon.total_real() == 2
        assert mon.total_synthetic() == 1

    def test_batch_without_league(self):
        mon = _monitor()
        mon.record_batch([{"is_synthetic": False}, {"is_synthetic": True}])
        assert mon.n_recorded() == 2


# ---------------------------------------------------------------------------
# Alert levels
# ---------------------------------------------------------------------------


class TestAlertLevels:
    def test_safe_when_all_real(self):
        mon = _monitor(min_real_for_live=5)
        _fill(mon, n_real=10, n_synthetic=0)
        alert = mon.current_alert()
        assert alert.level == AlertLevel.SAFE
        assert alert.min_real_met

    def test_warning_when_below_min_real(self):
        mon = _monitor(min_real_for_live=100)
        _fill(mon, n_real=10, n_synthetic=10)
        alert = mon.current_alert()
        # synthetic rate = 50% → WARNING threshold; also min_real not met
        assert alert.level in (AlertLevel.WARNING, AlertLevel.CRITICAL)

    def test_warning_when_synthetic_rate_high(self):
        mon = _monitor(warn_threshold=0.50, critical_threshold=0.80, min_real_for_live=5)
        _fill(mon, n_real=10, n_synthetic=40)   # 80% *exactly* hits critical
        alert = mon.current_alert()
        # 40/50 = 80% >= critical_threshold = 0.80
        assert alert.level == AlertLevel.CRITICAL

    def test_warning_between_thresholds(self):
        mon = _monitor(warn_threshold=0.50, critical_threshold=0.80, min_real_for_live=5)
        _fill(mon, n_real=35, n_synthetic=65)   # 65%
        alert = mon.current_alert()
        assert alert.level == AlertLevel.WARNING

    def test_critical_above_threshold(self):
        mon = _monitor(warn_threshold=0.50, critical_threshold=0.80, min_real_for_live=5)
        _fill(mon, n_real=10, n_synthetic=90)   # 90%
        alert = mon.current_alert()
        assert alert.level == AlertLevel.CRITICAL

    def test_empty_monitor_is_safe(self):
        mon = _monitor()
        alert = mon.current_alert()
        # No data → synthetic rate = 0 → SAFE, but min_real not met → WARNING
        assert alert.level in (AlertLevel.SAFE, AlertLevel.WARNING)


class TestMinRealCriteria:
    def test_is_safe_for_live_true(self):
        mon = _monitor(min_real_for_live=5, warn_threshold=0.50)
        _fill(mon, n_real=10, n_synthetic=0)
        assert mon.current_alert().is_safe_for_live()

    def test_is_safe_for_live_false_not_enough_real(self):
        mon = _monitor(min_real_for_live=100)
        _fill(mon, n_real=10, n_synthetic=0)
        assert not mon.current_alert().is_safe_for_live()

    def test_is_safe_for_live_false_high_synthetic(self):
        mon = _monitor(min_real_for_live=5, warn_threshold=0.50)
        _fill(mon, n_real=10, n_synthetic=60)   # 86% synthetic
        assert not mon.current_alert().is_safe_for_live()


# ---------------------------------------------------------------------------
# Alert structure
# ---------------------------------------------------------------------------


class TestAlertStructure:
    def test_alert_fields_populated(self):
        mon = _monitor(min_real_for_live=5)
        _fill(mon, n_real=30, n_synthetic=20)
        alert = mon.current_alert()
        assert isinstance(alert, SyntheticRateAlert)
        assert alert.total_count == 50
        assert alert.synthetic_count == 20
        assert alert.real_count == 30
        assert alert.synthetic_rate == pytest.approx(0.40)
        assert alert.real_rate == pytest.approx(0.60)
        assert isinstance(alert.checked_at, str)
        assert isinstance(alert.message, str)

    def test_summary_string(self):
        mon = _monitor(min_real_for_live=5)
        _fill(mon, n_real=10, n_synthetic=0)
        s = mon.current_alert().summary()
        assert "SAFE" in s
        assert "real" in s.lower()

    def test_per_league_breakdown(self):
        mon = _monitor(min_real_for_live=5)
        mon.record(is_synthetic=False, league="prem")
        mon.record(is_synthetic=True,  league="la-liga")
        alert = mon.current_alert()
        assert "prem" in alert.per_league
        assert "la-liga" in alert.per_league
        assert alert.per_league["prem"]["real"] == 1
        assert alert.per_league["la-liga"]["synthetic"] == 1


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


class TestPersistence:
    def test_save_and_load(self, tmp_path):
        path = str(tmp_path / "synthetic_state.json")
        mon = _monitor(persist_path=path)
        _fill(mon, n_real=40, n_synthetic=20)
        mon.save()
        assert (tmp_path / "synthetic_state.json").exists()

        mon2 = _monitor(persist_path=path)
        mon2.load()
        assert mon2.total_real() == 40
        assert mon2.total_synthetic() == 20

    def test_load_nonexistent_does_not_crash(self):
        mon = _monitor()
        mon.load("/no/such/file.json")   # should silently pass

    def test_corrupt_state_starts_fresh(self, tmp_path):
        path = str(tmp_path / "corrupt.json")
        with open(path, "w") as fh:
            fh.write("not json {{{")
        mon = _monitor(persist_path=path)
        mon.load()
        assert mon.total_real() == 0

    def test_reset_clears_state(self):
        mon = _monitor()
        _fill(mon, n_real=10, n_synthetic=5)
        mon.reset()
        assert mon.total_real() == 0
        assert mon.total_synthetic() == 0
        assert mon.n_recorded() == 0
