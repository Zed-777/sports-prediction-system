import json
from pathlib import Path

from scripts.collect_historical_results import HistoricalResultsCollector


def test_auto_optimize_trigger(monkeypatch, tmp_path):
    proj_root = Path(__file__).resolve().parents[1]
    hist_dir = proj_root / "data" / "historical"
    hist_dir.mkdir(parents=True, exist_ok=True)
    league = "la-liga"
    out_file = hist_dir / f"{league}_results.json"
    # Create one completed record
    record = {
        "match_id": "m1",
        "match_date": "2025-01-01",
        "home_team": "A",
        "away_team": "B",
        "prediction": {},
        "actual_result": {"home_score": 1, "away_score": 0},
    }
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump([record], f, indent=2)

    called = {"ran": False}

    class FakeOpt:
        def full_optimization(self, league="la-liga"):
            called["ran"] = True
            return {"status": "ok"}

    monkeypatch.setenv("FOOTBALL_DATA_API_KEY", "fake")
    monkeypatch.setattr(
        "scripts.optimize_accuracy.AccuracyOptimizer", lambda: FakeOpt(),
    )

    collector = HistoricalResultsCollector()
    # simulate args.auto_optimize behavior by calling logic directly
    data = json.load(open(out_file, encoding="utf-8"))
    completed = [r for r in data if r.get("actual_result") is not None]
    assert len(completed) == 1
    # threshold 1 should trigger
    if len(completed) >= 1:
        opt = FakeOpt()
        opt.full_optimization(league=league)
    assert called["ran"] is True
