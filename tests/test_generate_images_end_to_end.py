import os
from pathlib import Path

import pytest

import generate_fast_reports as gfr


class FakeResponse:
    def __init__(self, matches):
        self._matches = matches

    def raise_for_status(self):
        return None

    def json(self):
        return {"matches": self._matches}


def test_generate_matches_creates_png(tmp_path, monkeypatch):
    # Use tmp dir to avoid polluting repo
    monkeypatch.chdir(tmp_path)

    # Provide a fake API key required by SingleMatchGenerator
    monkeypatch.setenv("FOOTBALL_DATA_API_KEY", "fakekey")

    # Fake match payload
    match = {
        "homeTeam": {"name": "Test Home"},
        "awayTeam": {"name": "Test Away"},
        "utcDate": "2025-12-31T20:00:00Z",
        "id": 12345,
    }

    # Patch the HTTP call used to fetch scheduled matches
    monkeypatch.setattr(
        "generate_fast_reports.safe_request_get",
        lambda url, headers, params, logger=None: FakeResponse([match]),
    )

    # Create generator instance
    gen = gfr.SingleMatchGenerator(skip_injuries=True)

    # Replace predictor with a dummy implementation to avoid external dependencies
    class DummyPred:
        def enhanced_prediction(self, match, code):
            return {
                "expected_home_goals": 1.2,
                "expected_away_goals": 0.8,
                "expected_final_score": "1-1",
                "home_win_prob": 50.0,
                "draw_prob": 30.0,
                "away_win_prob": 20.0,
                "confidence": 0.6,
                "score_probability": 45.0,
            }

    gen.enhanced_predictor = DummyPred()
    gen.phase2_lite_predictor = None

    # Run generation (should not raise)
    gen.generate_matches_report(1, "la-liga")

    # Expect match folder and image to exist
    match_folder = "test-home_vs_test-away_2025-12-31"
    full_path = tmp_path / "reports" / "leagues" / "la-liga" / "matches" / match_folder
    assert full_path.exists(), "Match folder was not created"

    image_path = full_path / "prediction_card.png"
    assert image_path.exists(), "prediction_card.png missing"
    assert image_path.stat().st_size > 0

    # Also check unified formats copy
    formats_copy = tmp_path / "reports" / "formats" / "images" / f"{match_folder}.png"
    assert formats_copy.exists() and formats_copy.stat().st_size > 0
