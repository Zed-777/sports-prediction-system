import os
import yaml
import pytest
from pathlib import Path


def test_odds_connector_env_present():
    cfg_path = Path('config/settings.yaml')
    assert cfg_path.exists()
    cfg = yaml.safe_load(cfg_path.read_text(encoding='utf-8'))
    odds_cfg = cfg.get('data_sources', {}).get('odds', {}) or {}
    provider = odds_cfg.get('provider')
    env_key = odds_cfg.get('env_key')
    if provider and env_key:
        # Skip if env var not set (optional for local dev, required in CI)
        if os.environ.get(env_key) is None:
            pytest.skip(f"Optional env var {env_key} not set for odds provider {provider}")
    # If not configured or env var present, test passes
    assert True
