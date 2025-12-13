from types import SimpleNamespace
import enhanced_predictor
from enhanced_predictor import EnhancedPredictor
from app.utils import http as http_utils


class FakeResp:
    def __init__(self, payload):
        self.status_code = 200
        self._payload = payload

    def json(self):
        return self._payload


def test_fetch_team_home_away_stats_uses_safe_request(monkeypatch):
    # Replace safe_request_get with a fake that returns controlled data
    payload = {
        'matches': [
            {
                'utcDate': '2025-11-01T18:00:00Z',
                'homeTeam': {'id': 1, 'name': 'Test Home'},
                'awayTeam': {'id': 2, 'name': 'Test Away'},
                'score': {'fullTime': {'home': 2, 'away': 1}},
                'referees': []
            }
        ]
    }

    # Craft a fake response class that mimics `requests.Response` enough for the code under test
    class FakeRespObj:
        def __init__(self, payload):
            self.status_code = 200
            self._payload = payload

        def json(self):
            return self._payload

        def raise_for_status(self):
            return None

    fake_resp = lambda *args, **kwargs: FakeRespObj(payload)
    # Patch both the http utils and the already-imported symbol inside enhanced_predictor
    monkeypatch.setattr(http_utils, 'safe_request_get', fake_resp)
    monkeypatch.setattr(enhanced_predictor, 'safe_request_get', fake_resp)

    ep = EnhancedPredictor('test_key')
    stats = ep.fetch_team_home_away_stats(1, 'PD')
    assert 'home' in stats
    assert stats['home']['matches'] >= 1
