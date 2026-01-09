import re
from pathlib import Path


def test_confidence_text_drawn_once_in_generate_fast_reports():
    repo_root = Path(__file__).resolve().parents[1]
    target = repo_root / "generate_fast_reports.py"
    content = target.read_text(encoding="utf-8")

    # Ensure the legacy/conflicting assignment was removed
    assert "confidence_display = int(round(confidence))" not in content

    # The actual text drawing calls for the confidence and data-quality percentages
    left_matches = re.findall(r"ax\.text\(\s*2\.65,\s*21\.6", content)
    right_matches = re.findall(r"ax\.text\(\s*7\.35,\s*21\.6", content)

    # Expect exactly one draw for the left and one for the right (no duplicates)
    assert len(left_matches) == 1, (
        f"Expected 1 left-confidence draw, found {len(left_matches)}"
    )
    assert len(right_matches) == 1, (
        f"Expected 1 right-data-quality draw, found {len(right_matches)}"
    )
