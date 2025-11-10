import pytest


def test_extract_features_handles_none():
    """AIMLPredictor.extract_advanced_features should handle None/missing numeric fields and return a valid feature array."""
    try:
        from ai_ml_predictor import AIMLPredictor
    except Exception:
        pytest.skip("AIMLPredictor shim not available")

    if AIMLPredictor is None:
        pytest.skip("AIMLPredictor not available in this environment")

    model = AIMLPredictor()

    match_data = {'league': 'La Liga'}
    home_stats = {'home': {'win_rate': None, 'avg_goals_for': None, 'weighted_form_score': None}}
    away_stats = {'away': {'win_rate': None, 'avg_goals_for': None, 'weighted_form_score': None}}
    h2h_data = {}
    weather_data = {
        'conditions': {'temperature': None, 'precipitation': None, 'wind_speed': None, 'humidity': None},
        'impact_assessment': {'goal_modifier': None, 'weather_severity': None}
    }
    referee_data = {'home_bias_pct': None, 'cards_per_game': None, 'penalties_per_game': None, 'crowd_resistance': None}

    # Defer numpy import to runtime so tests can be skipped if numpy isn't installed in the environment
    try:
        import numpy as np
    except Exception:
        pytest.skip("numpy not available in test environment")

    features = model.extract_advanced_features(match_data, home_stats, away_stats, h2h_data, weather_data, referee_data)

    assert isinstance(features, np.ndarray)
    assert features.shape == (1, 48)
    # should not contain NaNs
    assert not np.isnan(features).any()


class _BrokenAIModule:
    def extract_advanced_features(self, *args, **kwargs):
        raise RuntimeError("simulated extractor failure")

    def predict_with_ml_ensemble(self, *args, **kwargs):
        raise RuntimeError("simulated predictor failure")


def test_enhanced_predictor_handles_ai_exceptions(monkeypatch):
    """EnhancedPredictor.ai_enhanced_prediction should not raise if the AI module fails; it should fall back to heuristics."""
    from enhanced_predictor import EnhancedPredictor

    predictor = EnhancedPredictor(api_key='TEST_KEY')

    # Force a broken ai_ml_predictor to simulate runtime exception during feature extraction
    predictor.ai_ml_predictor = _BrokenAIModule()
    # Ensure other optional modules are disabled for deterministic behavior
    predictor.neural_patterns = None
    predictor.ai_statistics = None

    match_data = {'homeTeam': {'name': 'Home'}, 'awayTeam': {'name': 'Away'}, 'league': 'La Liga'}
    home_stats = {'home': {'win_rate': 50, 'avg_goals_for': 1.5, 'weighted_form_score': 50}}
    away_stats = {'away': {'win_rate': 45, 'avg_goals_for': 1.3, 'weighted_form_score': 50}}
    h2h_data = {}
    weather_data = {'impact_assessment': {'goal_modifier': 1.0}}
    referee_data = {'home_bias_pct': 50, 'data_quality_score': 75}

    # Call the AI-enhanced prediction - should not raise
    result = predictor.ai_enhanced_prediction(match_data, home_stats, away_stats, h2h_data, weather_data, referee_data)

    assert isinstance(result, dict)
    # Final prediction should be present and shaped like probabilities
    final = result.get('final_prediction')
    assert isinstance(final, dict)
    assert 'home_win_probability' in final
    assert 'draw_probability' in final
    assert 'away_win_probability' in final
    # Ensure the pipeline used fallback/heuristics by checking presence of legacy_prediction
    assert 'legacy_prediction' in result
    # Even if AI failed, accuracy_estimate should be present
    assert 'accuracy_estimate' in result
