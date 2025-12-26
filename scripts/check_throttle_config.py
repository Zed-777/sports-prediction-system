#!/usr/bin/env python3
"""Simple helper to list per-provider throttle config and defaults"""

from pathlib import Path
import yaml
import json


def load_throttle_config() -> dict:
    cfg_path = Path(__file__).resolve().parents[1] / "config" / "settings.yaml"
    if not cfg_path.exists():
        return {}
    with cfg_path.open(encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    throttle_cfg = (cfg.get("data_sources") or {}).get("throttle_by_host", {})
    throttle_endpoint_cfg = (cfg.get("data_sources") or {}).get(
        "throttle_by_endpoint", {}
    )
    throttle_bucket_by_host = (cfg.get("data_sources") or {}).get(
        "throttle_bucket_by_host", {}
    )
    throttle_bucket_by_endpoint = (cfg.get("data_sources") or {}).get(
        "throttle_bucket_by_endpoint", {}
    )
    return {
        "throttle_by_host": throttle_cfg,
        "throttle_by_endpoint": throttle_endpoint_cfg,
        "throttle_bucket_by_host": throttle_bucket_by_host,
        "throttle_bucket_by_endpoint": throttle_bucket_by_endpoint,
    }


def main():
    throttle_cfg = load_throttle_config()
    if not throttle_cfg:
        print("No throttle configuration found in config/settings.yaml")
        return
    print("Configured throttle settings:")
    print(json.dumps(throttle_cfg, indent=2))


if __name__ == "__main__":
    main()
