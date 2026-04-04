import json
import os
import time
from types import SimpleNamespace

from data_quality_enhancer import DataQualityEnhancer


def _remove_disabled_file():
    path = "data/cache/injuries_disabled_until.json"
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


def _remove_cache_file(team_id):
    path = f"data/cache/injuries_{team_id}_{time.localtime().tm_year}.json"
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


def test_injury_disable_persistent_on_429(monkeypatch):
    os.environ["API_FOOTBALL_KEY"] = "demo_key"
    _remove_disabled_file()
    enhancer = DataQualityEnhancer("demo_key")

    # Simulate API returning 429
    def fake_safe_get(
        url,
        headers=None,
        params=None,
        timeout=None,
        retries=None,
        backoff=None,
        logger=None,
    ):
        return SimpleNamespace(status_code=429, text="429", json=dict)

    monkeypatch.setattr("data_quality_enhancer.safe_request_get", fake_safe_get)
    # Ensure no disabled state initially
    assert (
        enhancer._injuries_disabled_until == 0.0
        or enhancer._injuries_disabled_until < time.time()
    )

    # Trigger injuries fetch - should set disabled_until and persist to file
    res = enhancer._fetch_injury_data_api_football(99)
    assert res is None
    # Disabled flag should be set and persisted
    assert enhancer._injuries_disabled_until > time.time()
    assert os.path.exists("data/cache/injuries_disabled_until.json")
    with open("data/cache/injuries_disabled_until.json", encoding="utf-8") as f:
        payload = json.load(f)
    assert float(payload.get("disabled_until", 0)) == enhancer._injuries_disabled_until


def test_injury_cache_written_on_success(monkeypatch):
    os.environ["API_FOOTBALL_KEY"] = "demo_key"
    _remove_disabled_file()
    enhancer = DataQualityEnhancer("demo_key")
    team_id = 123
    _remove_cache_file(team_id)

    sample_payload = {
        "response": [
            {"player": {"name": "John Doe"}, "reason": "knee", "status": "out"},
        ],
    }

    def fake_safe_get(
        url,
        headers=None,
        params=None,
        timeout=None,
        retries=None,
        backoff=None,
        logger=None,
    ):
        return SimpleNamespace(status_code=200, text="{}", json=lambda: sample_payload)

    monkeypatch.setattr("data_quality_enhancer.safe_request_get", fake_safe_get)
    res = enhancer._fetch_injury_data_api_football(team_id)
    assert res is not None
    cache_file = f"data/cache/injuries_{team_id}_{time.localtime().tm_year}.json"
    assert os.path.exists(cache_file)
    with open(cache_file, encoding="utf-8") as f:
        payload = json.load(f)
    assert payload.get("data") is not None
    assert isinstance(payload.get("timestamp"), (int, float))
