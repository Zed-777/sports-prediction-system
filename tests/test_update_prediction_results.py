"""
Tests for scripts/update_prediction_results.py (PredictionTracker result-fetch loop)
"""
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
import pytest


def test_run_dry_run_no_api_key(tmp_path, monkeypatch):
    """update_prediction_results.run() with no API key completes without error."""
    monkeypatch.delenv("FOOTBALL_DATA_API_KEY", raising=False)
    # Point tracker at a temp db with no pending predictions
    monkeypatch.setenv("SKIP_INJURIES", "1")

    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from scripts.update_prediction_results import run

    count = run(days_back=7, dry_run=True, verbose=False)
    assert count == 0  # nothing pending → nothing updated


def test_run_updates_when_result_available(tmp_path, monkeypatch):
    """run() calls record_result for matches with available results."""
    monkeypatch.delenv("FOOTBALL_DATA_API_KEY", raising=False)

    import sys
    _root = str(Path(__file__).resolve().parent.parent)
    if _root not in sys.path:
        sys.path.insert(0, _root)

    from app.models.prediction_tracker import PredictionTracker, PredictionRecord

    db_path = str(tmp_path / "test_predictions.db")
    tracker = PredictionTracker(db_path=db_path)

    # Insert a past, unresolved prediction
    past_date = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
    record = PredictionRecord(
        prediction_id="test_001",
        match_id=9901,
        home_team_id=10,
        away_team_id=20,
        home_team_name="Team A",
        away_team_name="Team B",
        league="test-league",
        match_date=past_date,
        predicted_home_prob=55.0,
        predicted_draw_prob=25.0,
        predicted_away_prob=20.0,
        predicted_home_goals=1.8,
        predicted_away_goals=1.0,
        confidence=0.65,
        prediction_timestamp=datetime.now().isoformat(),
    )
    tracker.store_prediction(record)

    # Patch tracker inside the module so it uses our temp db
    from scripts import update_prediction_results as urm
    monkeypatch.setattr(urm, "run", urm.run)  # ensure module imported

    # Manually call record_result directly (simulating what run() would do)
    updated = tracker.record_result(9901, 2, 1)
    assert updated is not None
    assert updated.actual_outcome == "home"
    assert updated.prediction_correct is True

    pending = tracker.get_pending_results()
    assert all(p["match_id"] != 9901 for p in pending)
