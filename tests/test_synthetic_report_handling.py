import json
from pathlib import Path

import os
import pytest

from generate_fast_reports import SingleMatchGenerator


def test_synthetic_reports_redirected(tmp_path, monkeypatch):
    # Ensure env var for generator
    monkeypatch.setenv("FOOTBALL_DATA_API_KEY", "DUMMY_KEY")

    gen = SingleMatchGenerator(skip_injuries=True)

    # Simulate calling save_json for a synthetic match
    match_folder = tmp_path / "reports" / "leagues" / "premier-league" / "matches" / "m_test"
    match_folder.mkdir(parents=True, exist_ok=True)

    match_data = {
        "id": "m_test",
        "home_team": "A Team",
        "away_team": "B Team",
        "is_synthetic": True,
        "synthetic_notice": "Test synthetic output - not real data",
        "league": "premier-league",
    }

    # Call save_json - should redirect to reports/simulated
    gen.save_json(match_data, str(match_folder))

    synthetic_path = Path("reports") / "simulated" / "premier-league" / "matches" / (Path(str(match_folder)).name + "_synthetic")

    assert synthetic_path.exists(), f"Expected synthetic dir at {synthetic_path}"
    pred_json = synthetic_path / "prediction.json"
    assert pred_json.exists(), "prediction.json not written for synthetic report"

    data = json.loads(pred_json.read_text(encoding="utf-8"))
    assert data.get("is_synthetic") is True
    assert "synthetic_notice" in data

    # Ensure original public path does not contain prediction.json
    public_json = match_folder / "prediction.json"
    assert not public_json.exists(), "Public report should not include synthetic prediction.json"
