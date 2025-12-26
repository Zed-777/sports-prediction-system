import math

from app.utils.reliability_calculator import ReliabilityCalculator


def _to_percent_list(prob_dict):
    return [prob_dict[k] for k in ("home_win_prob", "draw_prob", "away_win_prob")]


def test_shrink_toward_neutral_applied():
    rc = ReliabilityCalculator()
    prediction = {"home_win_prob": 70.0, "draw_prob": 20.0, "away_win_prob": 10.0}
    reliability_metrics = {"score": 50.0}

    result = rc.apply_calibration(prediction, reliability_metrics)

    assert result["applied"] is True

    expected_shrink = (80.0 - 50.0) / 140.0
    assert math.isclose(
        result["shrink_factor"], round(expected_shrink, 3), rel_tol=1e-6
    )

    pre = result["pre_calibration_probabilities"]
    assert math.isclose(pre["home_win_prob"], 0.7, rel_tol=1e-6)
    assert math.isclose(pre["draw_prob"], 0.2, rel_tol=1e-6)
    assert math.isclose(pre["away_win_prob"], 0.1, rel_tol=1e-6)

    neutral = 1.0 / 3.0
    shrink = expected_shrink
    pre_probs = [0.7, 0.2, 0.1]
    calibrated = [(1 - shrink) * p + shrink * neutral for p in pre_probs]
    total = sum(calibrated)
    calibrated = [v / total for v in calibrated]

    expected_percentages = [round(v * 100.0, 2) for v in calibrated]
    out_percentages = _to_percent_list(result["probabilities"])

    for out_value, expected_value in zip(
        out_percentages, expected_percentages, strict=True
    ):
        assert math.isclose(out_value, expected_value, rel_tol=1e-6)


def test_no_shrink_when_high_reliability():
    rc = ReliabilityCalculator()
    prediction = {"home_win_prob": 55.0, "draw_prob": 25.0, "away_win_prob": 20.0}
    reliability_metrics = {"score": 85.0}

    result = rc.apply_calibration(prediction, reliability_metrics)

    assert result["applied"] is False

    pre = result["pre_calibration_probabilities"]
    assert math.isclose(pre["home_win_prob"], 0.55, rel_tol=1e-6)
    assert math.isclose(pre["draw_prob"], 0.25, rel_tol=1e-6)
    assert math.isclose(pre["away_win_prob"], 0.20, rel_tol=1e-6)

    pre_probs = [0.55, 0.25, 0.20]
    total = sum(pre_probs)
    expected = [round(v / total * 100.0, 2) for v in pre_probs]
    out_percentages = _to_percent_list(result["probabilities"])

    for out_value, expected_value in zip(out_percentages, expected, strict=True):
        assert math.isclose(out_value, expected_value, rel_tol=1e-6)
