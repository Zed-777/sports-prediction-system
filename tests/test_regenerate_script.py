import json


def test_regenerate_script_generates_image_and_summary(monkeypatch, tmp_path):
    monkeypatch.setenv("FOOTBALL_DATA_API_KEY", "test_key")

    # Create a minimal prediction.json
    match_dir = (
        tmp_path
        / "reports"
        / "leagues"
        / "premier-league"
        / "matches"
        / "home_vs_away_2025-12-01"
    )
    match_dir.mkdir(parents=True)
    p = match_dir / "prediction.json"
    minimal = {
        "home_team": "Home FC",
        "away_team": "Away FC",
        "date": "2025-12-01",
        "league": "premier-league",
    }
    with open(p, "w", encoding="utf-8") as f:
        json.dump(minimal, f)

    # Use SingleMatchGenerator directly to simulate script behavior
    from generate_fast_reports import SingleMatchGenerator

    # Use SingleMatchGenerator to regenerate directly (as the script would)
    gen = SingleMatchGenerator()
    gen.save_summary(minimal, str(match_dir))
    gen.save_image(minimal, str(match_dir))

    assert (match_dir / "summary.md").exists()
    assert (match_dir / "prediction_card.png").exists()

    # Ensure image is not blank
    from PIL import Image

    im = Image.open(match_dir / "prediction_card.png").convert("RGB")
    nonwhite = sum(1 for px in im.getdata() if px != (255, 255, 255))
    assert nonwhite > 0, "Regenerated prediction_card.png appears blank"
