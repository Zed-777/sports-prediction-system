"""Tests for scripts/run_backtest.py (BacktestingFramework CLI)
"""
import sys
from pathlib import Path

import pytest

_ROOT = str(Path(__file__).resolve().parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def test_run_backtest_no_data(tmp_path, monkeypatch):
    """run_backtest.py with no historical data exits cleanly and writes a marker file."""
    monkeypatch.setenv("SKIP_INJURIES", "1")


    from scripts.run_backtest import main

    # Patch sys.argv
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_backtest.py",
            "--skip-predictor",
            "--results-dir",
            str(tmp_path / "backtests"),
            "--days",
            "365",
        ],
    )

    # No historical data at all → should exit(0) and write marker
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 0

    marker_files = list((tmp_path / "backtests").glob("backtest_no_data_*.json"))
    assert len(marker_files) == 1

    import json
    with open(marker_files[0], encoding="utf-8") as f:
        data = json.load(f)
    assert data["status"] == "no_data"


def test_run_backtest_with_sample_data(tmp_path, monkeypatch):
    """run_backtest.py runs successfully with sample historical data."""
    import json
    from datetime import datetime, timedelta

    monkeypatch.setenv("SKIP_INJURIES", "1")

    # Create sample historical data
    hist_dir = tmp_path / "data" / "historical"
    hist_dir.mkdir(parents=True)

    # Use rolling dates relative to today so data always passes the --days filter
    base_date = datetime.now() - timedelta(days=49)
    matches = []
    for i in range(50):
        d = base_date + timedelta(days=i)
        hg = 2 if i % 3 == 0 else 1
        ag = 1 if i % 4 == 0 else 0
        matches.append(
            {
                "id": f"m{i}",
                "date": d.isoformat(),
                "league": "test-league",
                "home_team": "HomeFC",
                "away_team": "AwayFC",
                "home_goals": hg,
                "away_goals": ag,
            },
        )

    with open(hist_dir / "sample.json", "w", encoding="utf-8") as f:
        json.dump(matches, f, default=str)

    from scripts.run_backtest import main

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_backtest.py",
            "--skip-predictor",
            "--results-dir",
            str(tmp_path / "backtests"),
            "--days",
            "365",
            "--train-window",
            "20",
            "--test-window",
            "10",
        ],
    )
    monkeypatch.chdir(tmp_path)

    # Should run without error
    main()

    summary_files = list((tmp_path / "backtests").glob("backtest_summary_*.json"))
    assert len(summary_files) >= 1
