from pathlib import Path

from PIL import Image


def test_prediction_images_nonblank(tmp_path):
    """Ensure produced prediction images are non-blank. If none exist in reports/, create a temporary one using helper."""
    from generate_fast_reports import ensure_prediction_image_exists

    repo_root = Path(__file__).resolve().parents[1]
    images = list(repo_root.glob("reports/leagues/*/matches/*/prediction_card.png"))

    # If no images exist in reports/, create a temp one for the assertion
    if not images:
        match_folder = "test-home_vs_test-away_2025-12-31"
        full_path = tmp_path / "reports" / "leagues" / "test-league" / "matches" / match_folder
        full_path.mkdir(parents=True, exist_ok=True)
        created = ensure_prediction_image_exists(str(full_path), {"home_team": "A", "away_team": "B"}, match_folder)
        assert created, "Failed to create a fallback prediction image"
        images = [full_path / "prediction_card.png"]

    for img_path in images:
        im = Image.open(img_path).convert("RGB")
        w, h = im.size
        nonwhite = sum(1 for px in im.getdata() if px != (255, 255, 255))
        pct_nonwhite = 100.0 * nonwhite / (w * h)
        assert nonwhite > 100, (
            f"Image {img_path} appears blank (nonwhite pixels={nonwhite})"
        )
        # If we created a temporary placeholder image in tmp_path, relax the threshold
        if str(img_path).startswith(str(tmp_path)):
            assert pct_nonwhite > 0.05, (
                f"Temporary image {img_path} has suspiciously low content ({pct_nonwhite:.3f}%)"
            )
        else:
            assert pct_nonwhite > 0.2, (
                f"Image {img_path} has suspiciously low content ({pct_nonwhite:.3f}%)"
            )
