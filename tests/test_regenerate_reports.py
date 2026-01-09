import os
import json
from pathlib import Path
import pytest
from scripts.regenerate_reports import prune_old_reports


def test_prune_old_reports(tmp_path):
    # Setup fake reports dir
    league = "la-liga"
    reports_dir = tmp_path / "reports" / "leagues" / league / "matches"
    reports_dir.mkdir(parents=True)

    # Create 5 fake match dirs with prediction.json
    for i in range(5):
        d = reports_dir / f"m{i}"
        d.mkdir()
        pred = d / "prediction.json"
        pred.write_text(json.dumps({"match_date": f"2025-12-{10 + i}T20:00"}))

    # Keep only 2
    removed = prune_old_reports(
        league=str(league),
        keep=2,
        debug=True,
        base_dir=tmp_path / "reports" / "leagues",
    )
    assert removed == 3
    # Ensure remaining count is 2
    remaining = list(reports_dir.iterdir())
    assert len([p for p in remaining if p.is_dir()]) == 2
