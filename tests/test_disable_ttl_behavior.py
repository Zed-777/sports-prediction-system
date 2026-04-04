import os
import time
from types import SimpleNamespace

from data_quality_enhancer import DataQualityEnhancer


def test_disable_on_429_uses_config_ttl(monkeypatch, tmp_path):
    # Setup settings to have a small TTL
    os.environ["API_FOOTBALL_KEY"] = "demo"

    # Create a small settings.yaml override in config to set TTL to 2 seconds for test
    import yaml

    cfg_path = "config/settings.yaml"
    cfg = yaml.safe_load(open(cfg_path, encoding="utf-8").read())
    # Temporarily set a smaller TTL for our tests
    cfg.setdefault("data_sources", {}).setdefault(
        "disable_on_429_seconds", {},
    ).setdefault("api-football-v1.p.rapidapi.com", {})["/v3/injuries"] = 2
    with open(cfg_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f)

    # Instantiate enhancer and simulate 429
    enhancer = DataQualityEnhancer("demo_key")

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

    _ = enhancer._fetch_injury_data_api_football(99)
    assert enhancer._injuries_disabled_until > time.time()
    # Wait 3 seconds for TTL to expire
    time.sleep(3)
    # After TTL, disabled flag should not prevent calls (skipping actual call since fake returns 429)
    # Re-invoke and ensure no exception; it should attempt and update disabled flag again
    _ = enhancer._fetch_injury_data_api_football(99)
    assert enhancer._injuries_disabled_until > time.time()
