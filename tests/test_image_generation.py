import os


from generate_fast_reports import ensure_prediction_image_exists


def test_ensure_prediction_image_creates_file(tmp_path, monkeypatch):
    # Change cwd so that reports/formats/images does not pollute repo
    monkeypatch.chdir(tmp_path)

    # Create target match folder
    match_folder = "test-home_vs_test-away_2025-12-31"
    full_path = tmp_path / "reports" / "leagues" / "test-league" / "matches" / match_folder
    os.makedirs(full_path, exist_ok=True)

    match_data = {"home_team": "Test Home", "away_team": "Test Away"}

    # Ensure image created
    created = ensure_prediction_image_exists(str(full_path), match_data, match_folder)
    assert created is True

    img_path = full_path / "prediction_card.png"
    assert img_path.exists()
    assert img_path.stat().st_size > 0

    # Also check formats copy exists
    formats_copy = tmp_path / "reports" / "formats" / "images" / f"{match_folder}.png"
    assert formats_copy.exists()
    assert formats_copy.stat().st_size > 0
