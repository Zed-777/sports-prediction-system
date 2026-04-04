import pytest

from generate_fast_reports import SingleMatchGenerator


def test_prediction_tracker_attached(monkeypatch):
    monkeypatch.setenv("FOOTBALL_DATA_API_KEY", "DUMMY_KEY")
    gen = SingleMatchGenerator(skip_injuries=True)
    assert hasattr(gen, "prediction_tracker")
    if gen.prediction_tracker is not None:
        # Ensure the enhanced_predictor also has a reference where applicable
        assert getattr(gen.enhanced_predictor, "prediction_tracker", None) is not None
    else:
        pytest.skip("PredictionTracker not available in this environment")
