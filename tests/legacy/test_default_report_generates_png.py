import os

from generate_fast_reports import ensure_prediction_image_exists


def test_default_report_generation_creates_png_and_formats_copy(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    # Create a sample match prediction folder and minimal prediction.json
    match_folder = "sunderland-afc_vs_leeds-united-football-club_2025-12-28"
    league_dir = tmp_path / "reports" / "leagues" / "premier-league" / "matches" / match_folder
    os.makedirs(league_dir, exist_ok=True)

    match_data = {
        "home_team": "Sunderland AFC",
        "away_team": "Leeds United Football Club",
        "date": "2025-12-28",
        "time": "15:00",
        "expected_home_goals": 1.2,
        "expected_away_goals": 1.0,
        "expected_final_score": "1-1",
        "confidence": 0.63,
        "generated_at": "2025-12-28T00:00:00Z",
        "league": "premier-league",
    }

    # Ensure image created using the helper (this is the same guarantee used by the generator)
    created = ensure_prediction_image_exists(str(league_dir), match_data, match_folder)
    assert created is True

    img_path = league_dir / "prediction_card.png"
    assert img_path.exists(), "prediction_card.png should exist after generation"
    assert img_path.stat().st_size > 0, "prediction_card.png should be non-empty"

    # Also assert a copy exists in the formats directory
    formats_copy = tmp_path / "reports" / "formats" / "images" / f"{match_folder}.png"
    assert formats_copy.exists(), "Formats copy of PNG should exist"
    assert formats_copy.stat().st_size > 0, "Formats copy should be non-empty"
