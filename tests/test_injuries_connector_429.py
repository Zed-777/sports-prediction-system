import json
import time
from types import SimpleNamespace


from app.data.connectors.injuries import InjuriesConnector


def test_429_persists_disabled_flag(monkeypatch, tmp_path):
    connector = InjuriesConnector(cache_dir=str(tmp_path))

    def fake_safe_get_429(url, headers=None, params=None, timeout=None, retries=None, backoff=None):
        return SimpleNamespace(status_code=429, headers={}, text="429", json=lambda: {})

    monkeypatch.setattr("app.data.connectors.injuries.safe_request_get", fake_safe_get_429)

    # Monkeypatch state_sync to capture set_disabled_flag calls
    calls = {}

    class FakeStateSync:
        def set_disabled_flag(self, host, path, disabled_until, reason=None):
            calls['host'] = host
            calls['path'] = path
            calls['disabled_until'] = disabled_until
            calls['reason'] = reason

    monkeypatch.setattr("app.data.connectors.injuries.state_sync", FakeStateSync())

    res = connector.fetch_injuries(99)
    assert res is None

    # File should exist with disabled_until data
    dfile = tmp_path / "injuries_disabled_until.json"
    assert dfile.exists()
    payload = json.loads(dfile.read_text(encoding="utf-8"))
    assert float(payload.get("disabled_until", 0)) > time.time() - 10
    # state_sync should have been called
    assert calls.get('host') == connector._host
    assert calls.get('path') == "/v3/injuries"
    assert calls.get('reason') == "429"