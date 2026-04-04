import json
from pathlib import Path

from scripts.optimize_accuracy import AccuracyOptimizer


def test_run_backtest_calls_backtester(tmp_path, monkeypatch):
    project_root = Path(__file__).parent.parent
    hist_dir = project_root / "data" / "historical"
    hist_dir.mkdir(parents=True, exist_ok=True)

    league = "test-league"
    hist_file = hist_dir / f"{league}_results.json"
    sample = [
        {
            "id": "m1",
            "date": "2025-01-01",
            "league": league,
            "home_team": "A",
            "away_team": "B",
            "home_goals": 1,
            "away_goals": 0,
        },
        {
            "id": "m2",
            "date": "2025-01-05",
            "league": league,
            "home_team": "C",
            "away_team": "D",
            "home_goals": 0,
            "away_goals": 0,
        },
    ]
    hist_file.write_text(json.dumps(sample))

    called = {}

    class StubBacktester:
        def run_backtest(
            self, predictor=None, model_name=None, test_matches=None, **kwargs,
        ):
            # Record what we got
            called["predictor_callable"] = callable(predictor)
            called["test_matches_len"] = len(test_matches) if test_matches else 0
            return {"metrics": {"accuracy": 0.6}, "mode": "real"}

    # Monkeypatch the optimizer _load_tools to inject our stub backtester
    def fake_load(self):
        self.backtester = StubBacktester()
        self.ab_tester = None
        self.tracker = None

    monkeypatch.setattr(AccuracyOptimizer, "_load_tools", fake_load)

    opt = AccuracyOptimizer()
    res = opt.run_backtest(league=league)

    assert res["metrics"]["accuracy"] == 0.6
    assert called["predictor_callable"] is True
    assert called["test_matches_len"] == len(sample)
