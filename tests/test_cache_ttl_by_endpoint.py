from enhanced_predictor import EnhancedPredictor


def test_get_intelligent_cache_duration_respects_settings():
    p = EnhancedPredictor('FAKEKEY')
    # Provide custom settings simulating config/settings.yaml entries
    p._settings['data_sources'] = {
        'cache_ttl_by_endpoint': {
            'api.football-data.org': {
                '/v4/matches/': 3600,
                '/v4/teams/': 7200
            }
        }
    }
    # h2h -> maps to /v4/matches/
    ttl_h2h = p._get_intelligent_cache_duration('h2h_1_2', {})
    assert ttl_h2h == 3600
    # home_away -> teams
    ttl_ha = p._get_intelligent_cache_duration('home_away_123_2024', {})
    assert ttl_ha == 7200
    # weather should fallback to base_duration unless overridden
    t_weather = p._get_intelligent_cache_duration('weather_2024-01-01', {})
    assert t_weather == p.cache_duration
