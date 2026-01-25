from types import SimpleNamespace
from app.utils.http import safe_request_get
from app.utils.throttle import _GLOBAL_THROTTLE_MANAGER


class FakeBucket:
    def __init__(self):
        self.consumed = False
        self.last_args = None

    def consume(self, tokens=1.0, block=True):
        self.last_args = (tokens, block)
        self.consumed = True
        return True


class FakeSession:
    def __init__(self):
        self.called = False

    def get(self, url, headers=None, params=None, timeout=None):
        self.called = True
        # Return something that has status_code and json() method
        return SimpleNamespace(
            status_code=200, text="{}", json=lambda: {}, raise_for_status=lambda: None
        )


def test_safe_request_get_uses_token_bucket(monkeypatch):
    bucket = FakeBucket()

    # Monkeypatch manager to return our bucket for the host
    def fake_get_bucket(url):
        return bucket

    monkeypatch.setattr(_GLOBAL_THROTTLE_MANAGER, "get_bucket", fake_get_bucket)
    fake_session = FakeSession()
    # Call safe_request_get
    resp = safe_request_get(
        "https://api.football-data.org/v4/competitions/PD/matches",
        session=fake_session,
        timeout=1,
        retries=1,
        logger=None,
    )
    # Assert bucket consumed and session called
    assert bucket.consumed
    assert fake_session.called
    assert resp.status_code == 200
