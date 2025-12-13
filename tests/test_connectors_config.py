import os
import yaml
from pathlib import Path


def test_odds_connector_env_present():
    cfg_path = Path('config/settings.yaml')
    assert cfg_path.exists()
    cfg = yaml.safe_load(cfg_path.read_text(encoding='utf-8'))
    odds_cfg = cfg.get('data_sources', {}).get('odds', {}) or {}
    provider = odds_cfg.get('provider')
    env_key = odds_cfg.get('env_key')
    if provider and env_key:
        # If provider configured, env var should be set in environment for CI runs
        assert os.environ.get(env_key) is not None, f"Env var {env_key} required for odds provider {provider}"
    else:
        # If not configured, test passes (optional)
        assert True
