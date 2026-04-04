import pytest

from enhanced_predictor import EnhancedPredictor


@pytest.fixture
def predictor(monkeypatch):
    instance = EnhancedPredictor("demo")
    # Prevent actual odds fetching during tests
    instance.odds_connector = None
    return instance


def test_apply_market_adjustment_blends_probabilities(predictor):
    base_prediction = {
        "home_win_probability": 60.0,
        "draw_probability": 20.0,
        "away_win_probability": 20.0,
    }
    market_probs = {"home": 0.5, "draw": 0.25, "away": 0.25}

    predictor.market_blend_weight = 0.2

    adjusted = predictor._apply_market_adjustment(base_prediction, market_probs)

    assert pytest.approx(adjusted["home_win_probability"], rel=1e-3) == 58.0
    assert pytest.approx(adjusted["draw_probability"], rel=1e-3) == 21.0
    assert pytest.approx(adjusted["away_win_probability"], rel=1e-3) == 21.0
    assert base_prediction["home_win_probability"] == 60.0  # original untouched


def test_apply_market_adjustment_handles_zero_total(predictor):
    base_prediction = {
        "home_win_probability": 40.0,
        "draw_probability": 30.0,
        "away_win_probability": 30.0,
    }
    market_probs = {"home": 0.0, "draw": 0.0, "away": 0.0}

    adjusted = predictor._apply_market_adjustment(base_prediction, market_probs)

    assert adjusted["home_win_probability"] == pytest.approx(40.0)
    assert adjusted["draw_probability"] == pytest.approx(30.0)
    assert adjusted["away_win_probability"] == pytest.approx(30.0)
