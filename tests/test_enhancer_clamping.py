import pytest

from data_quality_enhancer import DataQualityEnhancer


def make_enhancer_with_settings(constants_override: dict):
    enh = DataQualityEnhancer(football_api_key='test')
    # Ensure settings structure exists
    enh._settings.setdefault('constants', {})
    enh._settings['constants'].update(constants_override)
    return enh


def test_injury_clamping_enabled():
    # Configure with enforce_caps = True and low max_reduction_pct to force clamping
    constants = {
        'enforce_caps': True,
        'injury': {
            'per_player_pct': 10.0,
            'midfield_penalty': 5,
            'defense_penalty': 3,
            'max_reduction_pct': 20
        }
    }
    enh = make_enhancer_with_settings(constants)

    # Create synthetic injury input with many injured -> base_reduction > max
    injury_input = {
        'injured_count': 3,  # 3 * 10 = 30
        'affected_positions': ['midfield', 'defense']
    }

    reduced = enh.calculate_strength_reduction(injury_input)
    # With enforce_caps True and max 20, the returned value should be <= max
    assert reduced <= 20
    # Provenance should be recorded in enh._last_injury_clamps
    assert isinstance(getattr(enh, '_last_injury_clamps', {}), dict)
    assert 'strength_reduction' in enh._last_injury_clamps


def test_injury_clamping_disabled():
    constants = {
        'enforce_caps': False,
        'injury': {
            'per_player_pct': 10.0,
            'midfield_penalty': 5,
            'defense_penalty': 3,
            'max_reduction_pct': 20
        }
    }
    enh = make_enhancer_with_settings(constants)

    injury_input = {
        'injured_count': 3,  # 3 * 10 = 30
        'affected_positions': ['midfield', 'defense']
    }

    reduced = enh.calculate_strength_reduction(injury_input)
    # Without clamping the reduction equals base_reduction = 30 + midfield + defense -> 38
    assert reduced > 20
    # _last_injury_clamps should be empty
    assert getattr(enh, '_last_injury_clamps', {}) == {}


def test_weather_clamping_enabled():
    constants = {
        'enforce_caps': True,
        'caps': {
            'wind_speed': {'min': 0.0, 'max': 60.0},
            'temperature': {'min': -10, 'max': 45},
            'precipitation': {'min': 0.0, 'max': 50.0},
            'humidity': {'min': 0.0, 'max': 100.0}
        },
        'provenance': {'record_clamps': True}
    }
    enh = make_enhancer_with_settings(constants)

    # Create an absurd weather dict
    weather = {
        'temperature': 10,
        'precipitation': 0.0,
        'wind_speed': 120.0,
        'humidity': 50
    }

    impact = enh.analyze_weather_impact(weather)
    # When clamping enabled, result should include weather_clamped True and clamped_fields
    assert impact.get('weather_clamped') is True
    assert 'wind_speed' in impact.get('clamped_fields', {})


def test_weather_clamping_disabled():
    constants = {
        'enforce_caps': False,
        'caps': {
            'wind_speed': {'min': 0.0, 'max': 60.0}
        },
        'provenance': {'record_clamps': True}
    }
    enh = make_enhancer_with_settings(constants)

    weather = {
        'temperature': 10,
        'precipitation': 0.0,
        'wind_speed': 120.0,
        'humidity': 50
    }

    impact = enh.analyze_weather_impact(weather)
    # With enforce_caps False, no clamping should occur
    assert impact.get('weather_clamped') is False or impact.get('weather_clamped') is None
    assert impact.get('clamped_fields', {}) == {}
