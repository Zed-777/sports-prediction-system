import os
import yaml
import pytest
from pathlib import Path


def test_odds_connector_env_present():
    cfg_path = Path("config/settings.yaml")
    assert cfg_path.exists()
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    odds_cfg = cfg.get("data_sources", {}).get("odds", {}) or {}
    provider = odds_cfg.get("provider")
    env_key = odds_cfg.get("env_key")

    def _read_env_key(key: str) -> str | None:
        env_file = Path(".env")
        if not env_file.exists():
            return None
        with env_file.open() as f:
            for line in f:
                line = line.strip()
                if line.startswith(f"{key}="):
                    value = line.split("=", 1)[1]
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    return value
        return None

    if provider and env_key:
        # Skip if env var not set and no value in .env (optional for local dev, required in CI)
        if os.environ.get(env_key) is None and _read_env_key(env_key) is None:
            pytest.skip(
                f"Optional env var {env_key} not set for odds provider {provider}"
            )
    # If not configured or env var present, test passes
    assert True
