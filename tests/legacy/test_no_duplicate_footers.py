from pathlib import Path


def test_no_duplicate_footer_texts_in_generate_fast_reports():
    repo_root = Path(__file__).resolve().parents[1]
    target = repo_root / "generate_fast_reports.py"
    content = target.read_text(encoding="utf-8")

    import re

    count_footer1 = len(re.findall(r"ax\.text\s*\(\s*5\s*,\s*3\.6", content))
    count_footer2 = len(re.findall(r"ax\.text\s*\(\s*5\s*,\s*2\.6", content))

    assert count_footer1 == 1, (
        f"Expected exactly one footer line at y=3.6, found {count_footer1}"
    )
    assert count_footer2 == 1, (
        f"Expected exactly one footer line at y=2.6, found {count_footer2}"
    )
