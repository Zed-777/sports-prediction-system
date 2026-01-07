import os
import json
import time
from types import SimpleNamespace

import pytest

from app.data.connectors.injuries import InjuriesConnector


def test_api_success_writes_cache(monkeypatch, tmp_path):
    connector = InjuriesConnector(cache_dir=str(tmp_path))

    def fake_safe_get(url, headers=None, params=None, timeout=None, retries=None, backoff=None):
        payload = {"response": [{"player": {"name": "John Doe"}, "reason": "knee", "status": "out"}]}
        return SimpleNamespace(status_code=200, json=lambda: payload)

    monkeypatch.setattr("app.data.connectors.injuries.safe_request_get", fake_safe_get)
    res = connector.fetch_injuries(123)
    assert res is not None
    cache_file = tmp_path / f"injuries_123_{time.localtime().tm_year}.json"
    assert cache_file.exists()
    data = json.loads(cache_file.read_text(encoding="utf-8"))
    assert data.get("data") is not None


def test_api_429_fallback_to_flashscore(monkeypatch, tmp_path):
    connector = InjuriesConnector(cache_dir=str(tmp_path))

    # Simulate 429 from API-Football
    def fake_safe_get_429(url, headers=None, params=None, timeout=None, retries=None, backoff=None):
        return SimpleNamespace(status_code=429, headers={}, text="429", json=lambda: {})

    monkeypatch.setattr("app.data.connectors.injuries.safe_request_get", fake_safe_get_429)

    # Simulate FlashScore page containing injury keywords
    class FakeScraper:
        def get_page(self, url, use_cache=True):
            return "<html>Recent injuries: Player X out with hamstring injury. More text...</html>"

    monkeypatch.setattr("app.data.connectors.injuries.FlashScoreScraper", FakeScraper)

    res = connector.fetch_injuries(99, team_name="Sevilla FC")
    assert res is not None
    assert isinstance(res, list)
    assert any("provenance" in item or item.get("reason") == "site_mention" for item in res)


def test_no_api_or_fallback_returns_none(monkeypatch, tmp_path):
    connector = InjuriesConnector(cache_dir=str(tmp_path))

    def fake_safe_get_none(url, headers=None, params=None, timeout=None, retries=None, backoff=None):
        raise Exception("network")

    monkeypatch.setattr("app.data.connectors.injuries.safe_request_get", fake_safe_get_none)
    # Ensure FlashScore not available by monkeypatching to raise
    monkeypatch.setattr("app.data.connectors.injuries.FLASHSCORE_AVAILABLE", False)

    res = connector.fetch_injuries(999, team_name="Missing FC")
    assert res is None
