from pathlib import Path
from PIL import Image


def test_prediction_images_nonblank():
    repo_root = Path(__file__).resolve().parents[1]
    images = list(repo_root.glob("reports/leagues/*/matches/*/prediction_card.png"))
    assert images, "No prediction images found to test"

    for img_path in images:
        im = Image.open(img_path).convert("RGB")
        w, h = im.size
        nonwhite = sum(1 for px in im.getdata() if px != (255, 255, 255))
        pct_nonwhite = 100.0 * nonwhite / (w * h)
        assert nonwhite > 100, (
            f"Image {img_path} appears blank (nonwhite pixels={nonwhite})"
        )
        assert pct_nonwhite > 0.2, (
            f"Image {img_path} has suspiciously low content ({pct_nonwhite:.3f}%)"
        )
