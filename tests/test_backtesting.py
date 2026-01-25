import json
from datetime import datetime, timedelta


from app.models.backtesting import BacktestingFramework


def make_sample_matches(n=10, start_date=datetime(2024, 1, 1)):
    matches = []
    for i in range(n):
        date = start_date + timedelta(days=i)
        home_goals = 2 if i % 3 == 0 else 1
        away_goals = 1 if i % 4 == 0 else 0
        outcome = "1" if home_goals > away_goals else "2" if away_goals > home_goals else "X"
        matches.append(
            {
                "id": f"m_{i}",
                "date": date,
                "league": "test-league",
                "home_team": f"Home {i}",
                "away_team": f"Away {i}",
                "home_goals": home_goals,
                "away_goals": away_goals,
                "outcome": outcome,
            }
        )
    return matches


def dummy_predictor_factory():
    def predict(match):
        # A naive predictor: always predicts home win with probability 60%
        return {
            "home_win_prob": 60.0,
            "draw_prob": 25.0,
            "away_win_prob": 15.0,
            "confidence": 60.0,
        }

    return predict


def test_load_historical_data_parsing(tmp_path):
    data_dir = tmp_path / "data"
    hist_dir = data_dir / "historical"
    hist_dir.mkdir(parents=True)

    sample = make_sample_matches(5)
    # Save as JSON list
    with open(hist_dir / "sample_matches.json", "w", encoding="utf-8") as f:
        json.dump(sample, f, default=str)

    framework = BacktestingFramework(data_dir=str(data_dir), results_dir=str(tmp_path / "reports"))
    matches = framework.load_historical_data()

    assert len(matches) == 5
    assert matches[0]["league"] == "test-league"


def test_run_backtest_and_results_written(tmp_path):
    sample_matches = make_sample_matches(30)

    results_dir = tmp_path / "backtests"
    results_dir.mkdir(parents=True)

    framework = BacktestingFramework(data_dir=str(tmp_path / "data"), results_dir=str(results_dir))

    predictor = dummy_predictor_factory()

    summary = framework.run_backtest(predictor=predictor, model_name="dummy", test_matches=sample_matches, train_window_days=10, test_window_days=5, min_train_matches=1)

    # Summary should be a BacktestSummary-like object
    assert summary.total_matches > 0
    assert 0.0 <= summary.accuracy <= 1.0

    # Check that summary and details files were created
    files = list(results_dir.glob("backtest_summary_*.json"))
    details = list(results_dir.glob("backtest_details_*.json"))

    assert len(files) >= 1
    assert len(details) >= 1
