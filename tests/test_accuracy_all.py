import json
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
HIST = PROJECT_ROOT / "data" / "historical"
REPORTS = PROJECT_ROOT / "reports" / "historical"


def test_accuracy_all_writes_summary(tmp_path):
    HIST.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    test_file = HIST / "unittest_temp_league_results.json"
    entry = [
        {
            "match_id": "t1",
            "league": "unittest_temp_league",
            "prediction": {
                "home_win_prob": 0.6,
                "draw_prob": 0.2,
                "away_win_prob": 0.2,
            },
            "actual_result": {"home_score": 1, "away_score": 0, "outcome": "home_win"},
        },
    ]
    test_file.write_text(json.dumps(entry), encoding="utf-8")

    try:
        # Run the script to generate accuracy summary
        subprocess.check_call(
            ["python", "scripts/collect_historical_results.py", "--accuracy-all"],
        )
        # Find the most recent accuracy_summary_*.json in reports/historical
        files = sorted(
            REPORTS.glob("accuracy_summary_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        assert files, "No accuracy summary files created"
        # load latest and ensure our league is present
        latest = files[0]
        data = json.loads(latest.read_text(encoding="utf-8"))
        assert "unittest_temp_league" in data
    finally:
        try:
            test_file.unlink()
        except Exception:
            pass
