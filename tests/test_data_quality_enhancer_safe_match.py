import copy

import pytest

from data_quality_enhancer import DataQualityEnhancer


class _DummyIntegrator:
    def __init__(self):
        self.received_match = None

    def enhance_match_data(self, match, league_key):
        self.received_match = copy.deepcopy(match)
        # Ensure keys needed by downstream consumers exist
        assert 'home_team' in match
        assert 'away_team' in match
        return {
            'home_team_stats': {},
            'away_team_stats': {},
            'advanced_metrics': {},
            'odds_data': {},
            'data_quality_score': 82
        }


@pytest.fixture
def enhancer(monkeypatch):
    instance = DataQualityEnhancer("demo")
    dummy = _DummyIntegrator()
    instance.flashscore_integrator = dummy

    # Avoid external IO by stubbing heavy methods
    monkeypatch.setattr(
        instance,
        "get_player_injury_impact",
        lambda *args, **kwargs: instance.get_default_injury_data(),
    )
    monkeypatch.setattr(
        instance,
        "get_weather_impact",
        lambda *args, **kwargs: {**instance.get_default_weather_data(), "provenance": {}},
    )
    monkeypatch.setattr(
        instance,
        "get_referee_analysis",
        lambda *args, **kwargs: instance.get_default_referee_data(),
    )
    monkeypatch.setattr(
        instance,
        "parse_team_news",
        lambda *args, **kwargs: instance.get_default_team_news(),
    )

    return instance, dummy


def test_comprehensive_handles_mixed_team_keys(enhancer):
    instance, dummy = enhancer
    match_payload = {
        "homeTeam": "Test FC",
        "away_team": {"name": "Opponent FC"},
        "utcDate": "2025-12-01T12:00:00Z",
    }

    result = instance.comprehensive_data_enhancement(match_payload)

    assert result["player_availability"]["home_team"]["key_players_available"] == instance.get_default_injury_data()["key_players_available"]
    assert result["team_news"]["home_team"]["formation_expected"]
    assert result["weather_conditions"]["impact_assessment"]
    assert dummy.received_match["home_team"] == "Test FC"
    assert dummy.received_match["away_team"] == "Opponent FC"
