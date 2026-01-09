import os
from pathlib import Path
import json
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
from generate_fast_reports import SingleMatchGenerator


def run(path):
    img_path = Path(path) / "test_image.png"
    match_data = {
        "home_team": "DebugHome",
        "away_team": "DebugAway",
        "date": "2025-12-20",
        "time": "17:30",
        "league": "premier-league",
        "expected_final_score": "2-1",
        "expected_home_goals": 2.0,
        "expected_away_goals": 1.0,
        "confidence": 0.8,
        "processing_time": 0.5,
        "generated_at": "2025-12-20T19:00:00",
    }
    gen = SingleMatchGenerator()
    try:
        gen.save_image(match_data, str(path))
        print("save_image call completed")
    except Exception as e:
        print("save_image raised", e)


if __name__ == "__main__":
    out = Path("tmp_debug")
    out.mkdir(exist_ok=True)
    run(out)
    print("Inspecting generated file")
    from PIL import Image, ImageStat

    im = Image.open(out / "prediction_card.png").convert("RGB")
    stat = ImageStat.Stat(im)
    print("mean", stat.mean, "var", stat.var)
