
from generate_fast_reports import SingleMatchGenerator


def test_save_image_with_missing_fields(monkeypatch, tmp_path):
    """Ensure save_image writes a prediction_card.png even when optional fields are missing."""
    # Provide minimal env var expected by SingleMatchGenerator
    monkeypatch.setenv("FOOTBALL_DATA_API_KEY", "test_key")

    minimal = {
        # Intentionally omit expected_final_score, time, and some metrics
        "home_team": "Home FC",
        "away_team": "Away FC",
        "date": "2025-11-01",
        "league": "premier-league",
        "confidence": 0.5,
    }

    gen = SingleMatchGenerator()
    out_dir = tmp_path / "match"
    out_dir.mkdir()

    gen.save_image(minimal, str(out_dir))

    assert (out_dir / "prediction_card.png").exists(), (
        "prediction_card.png was not created"
    )
    # The image should have visible (non-white) pixels
    from PIL import Image

    im = Image.open(out_dir / "prediction_card.png").convert("RGB")
    nonwhite = sum(1 for px in im.getdata() if px != (255, 255, 255))
    assert nonwhite > 0, "prediction_card.png appears to be blank (all white)"
