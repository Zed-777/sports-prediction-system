import json
import re
from pathlib import Path


def extract_confidence_from_summary(md_text: str):
    # Match the line like: - **Prediction Confidence:** **70.3%**
    m = re.search(
        r"\*\*Prediction Confidence:\*\* \*\*(?P<p>[0-9]+\.?[0-9]*)%\*\*", md_text,
    )
    if not m:
        return None
    return float(m.group("p"))


def test_prediction_confidence_matches_json():
    repo_root = Path(__file__).resolve().parents[1]
    matches_dir = repo_root / "reports" / "leagues"
    assert matches_dir.exists(), "Reports directory not found"

    mismatches = []

    for league_dir in matches_dir.iterdir():
        if not league_dir.is_dir():
            continue
        for match_dir in (league_dir / "matches").iterdir():
            if not match_dir.is_dir():
                continue
            json_path = match_dir / "prediction.json"
            md_path = match_dir / "summary.md"
            if not json_path.exists() or not md_path.exists():
                continue
            data = json.loads(json_path.read_text(encoding="utf-8"))
            md = md_path.read_text(encoding="utf-8")

            # Determine confidence source
            if "report_accuracy_probability" in data:
                json_conf = float(data["report_accuracy_probability"]) * 100
            elif "confidence" in data:
                # If confidence is a 0-1 float, scale to percent
                c = float(data["confidence"])
                json_conf = c * 100 if c <= 1.1 else c
            else:
                continue

            md_conf = extract_confidence_from_summary(md)
            if md_conf is None:
                mismatches.append((match_dir, json_conf, None))
                continue

            if abs(json_conf - md_conf) > 0.6:
                mismatches.append((match_dir, json_conf, md_conf))

    assert not mismatches, f"Found confidence mismatches: {mismatches}"
