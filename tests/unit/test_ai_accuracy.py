import pytest


def test_calculate_advanced_accuracy_nominal():
    try:
        from ai_ml_predictor import AIMLPredictor
    except Exception:
        pytest.skip("AIMLPredictor shim not available")

    model = AIMLPredictor()

    # Nominal inputs (prediction_strength is 0..1, data_quality 0..100, h2h 0..1, form_consistency 0..100)
    acc = model.calculate_advanced_accuracy(0.6, 75, 0.5, 50)

    assert isinstance(acc, float)
    assert 0.0 <= acc <= 1.0

    # expect reasonable value (not trivial 0 or 1)
    assert 0.1 < acc < 0.95


def test_calculate_advanced_accuracy_handles_missing_values():
    try:
        from ai_ml_predictor import AIMLPredictor
    except Exception:
        pytest.skip("AIMLPredictor shim not available")

    model = AIMLPredictor()

    # Missing / None inputs should not raise and should return a float in [0,1]
    acc = model.calculate_advanced_accuracy(None, None, None, None)
    assert isinstance(acc, float)
    assert 0.0 <= acc <= 1.0
