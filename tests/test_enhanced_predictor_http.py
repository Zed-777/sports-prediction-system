import types

from enhanced_predictor import EnhancedPredictor


class DummyResponse:
    def __init__(self, payload):
        self._payload = payload
        self.status_code = 200

    def json(self):
        return self._payload


class DummyLogger:
    def debug(self, *args, **kwargs):
        pass

    def warning(self, *args, **kwargs):
        pass

    def error(self, *args, **kwargs):
        pass


def test_fetch_team_home_away_stats_uses_safe_http(monkeypatch):
    api_key = "test_key"
    ep = EnhancedPredictor(api_key)
    ep.logger = DummyLogger()

    called = {"count": 0}

    def fake_safe_request_get(
        url,
        headers=None,
        params=None,
        timeout=15,
        retries=3,
        backoff=0.5,
        min_interval=None,
        session=None,
        logger=None,
    ):
        called["count"] += 1
        payload = {"matches": []}
        return DummyResponse(payload)

    # Monkeypatch the safe_request_get in the enhanced_predictor module
    import enhanced_predictor as epmod

    monkeypatch.setattr("app.utils.http.safe_request_get", fake_safe_request_get)
    monkeypatch.setattr(epmod, "safe_request_get", fake_safe_request_get)

    res = ep.fetch_team_home_away_stats(1, "PL")
    assert isinstance(res, dict)
    assert called["count"] == 1
