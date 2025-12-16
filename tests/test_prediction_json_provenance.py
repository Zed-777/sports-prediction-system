import json
import os
import re

import pytest


class StubPredictor:
    def enhanced_prediction(self, match, competition_code):
        return {
            'home_win_probability': 50.0,
            'draw_probability': 25.0,
            'away_win_probability': 25.0,
            'confidence': 0.8,
            'report_accuracy_probability': 0.8,
            'expected_home_goals': 1.0,
            'expected_away_goals': 1.0,
            'processing_time': 0.1,
        }


class StubEnhancer:
    def comprehensive_data_enhancement(self, match):
        return {
            'data_provenance': {
                'weather_clamped': True,
                'weather_clamped_fields': {'wind_speed': {'original': 120.0, 'clamped_to': 60.0}},
                'home_injury_clamped': False
            },
            'player_availability': {'home_team': {}, 'away_team': {}},
            'weather_conditions': {},
            'data_quality_score': 90,
        }


def slugify(name: str) -> str:
    if not name:
        return 'team'
    s = name.lower()
    s = re.sub(r'[^a-z0-9]+', '-', s)
    s = s.strip('-')
    return s or 'team'


def test_prediction_json_contains_provenance(monkeypatch):
    # Set mock API key before importing module
    monkeypatch.setenv('FOOTBALL_DATA_API_KEY', 'test_key_for_unit_tests')
    
    from generate_fast_reports import SingleMatchGenerator
    
    # Fake API response from football-data
    fake_match = {
        'id': 9999,
        'utcDate': '2025-11-02T15:00:00Z',
        'homeTeam': {'name': 'Real Betis Balompié'},
        'awayTeam': {'name': 'RCD Mallorca'}
    }

    class DummyResponse:
        status_code = 200
        def raise_for_status(self):
            return None

        def json(self):
            return {'matches': [fake_match]}

    monkeypatch.setattr('requests.get', lambda *args, **kwargs: DummyResponse())

    gen = SingleMatchGenerator()
    # Replace real engines with stubs
    gen.enhanced_predictor = StubPredictor()
    gen.data_quality_enhancer = StubEnhancer()

    # Run generation for 1 match
    gen.generate_matches_report(1, 'la-liga')

    match_date = fake_match['utcDate'][:10]
    home = slugify(fake_match['homeTeam']['name'])
    away = slugify(fake_match['awayTeam']['name'])
    folder = f"reports/leagues/la-liga/matches/{home}_vs_{away}_{match_date}"

    json_path = os.path.join(folder, 'prediction.json')
    assert os.path.exists(json_path), f"prediction.json not found at {json_path}"

    with open(json_path, encoding='utf-8') as f:
        payload = json.load(f)

    # Ensure detailed provenance and promoted flags exist
    assert 'data_provenance_details' in payload
    details = payload['data_provenance_details']
    assert details.get('weather_clamped') is True

    # Promoted flag
    assert payload.get('data_provenance', {}).get('weather_clamped') is True

    # Cleanup created files to avoid clutter
    try:
        # remove prediction.json and summary/image files if present
        for fname in os.listdir(folder):
            os.remove(os.path.join(folder, fname))
        os.rmdir(folder)
    except Exception:
        pass
