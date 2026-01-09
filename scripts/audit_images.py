"""Audit all generated prediction_card.png images and report anomalies.

Reports are expected under: reports/leagues/<league>/matches/<match_dir>/prediction_card.png
This tool prints statistics and flags images that are blank (very few non-white pixels) or otherwise suspicious.

Usage:
  python scripts/audit_images.py
"""

from PIL import Image, ImageStat
from pathlib import Path

root = Path(__file__).resolve().parents[1]
pattern = root / "reports" / "leagues" / "*" / "matches" / "*" / "prediction_card.png"

images = list(root.glob("reports/leagues/*/matches/*/prediction_card.png"))

print(f"Found {len(images)} images to inspect")

issues = []
for p in images:
    try:
        im = Image.open(p).convert("RGB")
        stat = ImageStat.Stat(im)
        mean = stat.mean
        var = stat.var
        w, h = im.size
        nonwhite = sum(1 for px in im.getdata() if px != (255, 255, 255))
        pct_nonwhite = 100.0 * nonwhite / (w * h)
        print(
            f"{p}: size={w}x{h}, mean={mean}, var={var}, nonwhite={nonwhite} ({pct_nonwhite:.3f}%)"
        )

        # Heuristics for suspicious images
        if nonwhite < 100:
            issues.append((p, "blank", nonwhite, pct_nonwhite))
        elif pct_nonwhite < 0.5:
            issues.append((p, "very_low_content", nonwhite, pct_nonwhite))
    except Exception as e:
        issues.append((p, "error", str(e)))

print("\nSummary of flagged images:")
for it in issues:
    print(it)

if issues:
    raise SystemExit(2)
else:
    print("No suspicious images found")
    raise SystemExit(0)
