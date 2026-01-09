import json
import joblib
import numpy as np
from scripts.evaluate_model import evaluate


class SimpleHeuristicModel:
    def predict_proba(self, X):
        out = []
        for row in X:
            eh, ea, hp, dp, ap, conf = row
            diff = eh - ea
            if diff > 0.2:
                p0, p1, p2 = 0.7, 0.15, 0.15
            elif diff < -0.2:
                p0, p1, p2 = 0.15, 0.15, 0.7
            else:
                p0, p1, p2 = 0.33, 0.34, 0.33
            out.append([p0, p1, p2])
        return np.array(out)


def test_evaluate_small_model(tmp_path):
    # prepare historical
    hist_dir = tmp_path / "historical"
    hist_dir.mkdir()
    entries = [
        {
            "league": "test-l",
            "home_team": "A",
            "away_team": "B",
            "prediction": {
                "expected_home_goals": 2.0,
                "expected_away_goals": 1.0,
                "home_win_prob": 0.6,
                "draw_prob": 0.2,
                "away_win_prob": 0.2,
                "confidence": 0.9,
            },
            "actual_result": {"home_score": 2, "away_score": 1},
        },
        {
            "league": "test-l",
            "home_team": "C",
            "away_team": "D",
            "prediction": {
                "expected_home_goals": 0.5,
                "expected_away_goals": 1.7,
                "home_win_prob": 0.2,
                "draw_prob": 0.3,
                "away_win_prob": 0.5,
                "confidence": 0.8,
            },
            "actual_result": {"home_score": 0, "away_score": 2},
        },
        {
            "league": "test-l",
            "home_team": "E",
            "away_team": "F",
            "prediction": {
                "expected_home_goals": 1.2,
                "expected_away_goals": 1.1,
                "home_win_prob": 0.35,
                "draw_prob": 0.3,
                "away_win_prob": 0.35,
                "confidence": 0.7,
            },
            "actual_result": {"home_score": 1, "away_score": 1},
        },
    ]
    (hist_dir / "small_results.json").write_text(json.dumps(entries), encoding="utf-8")

    # write model
    model_path = tmp_path / "model.joblib"
    joblib.dump(SimpleHeuristicModel(), model_path)

    res = evaluate(model_path, hist_dir, bins=5)
    assert "n_matches" in res and res["n_matches"] == 3
    assert 0.0 <= res["accuracy"] <= 1.0
    assert "log_loss" in res and res["log_loss"] >= 0.0
    assert "brier_score" in res and res["brier_score"] >= 0.0
    assert "calibration" in res
