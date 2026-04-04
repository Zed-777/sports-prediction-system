from __future__ import annotations

import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
import yaml

from app.utils import state_sync
from app.utils.metrics import increment_metric
from app.utils.throttle import _GLOBAL_THROTTLE_MANAGER, TokenBucket, wait_for_host


def safe_request_get(
    url: str,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    timeout: int = 15,
    retries: int = 3,
    backoff: float = 0.5,
    min_interval: float | None = None,
    session: requests.Session | None = None,
    logger: Any | None = None,
) -> requests.Response:
    """Perform a GET request with retries, exponential backoff and Retry-After handling.

    Returns the requests.Response object on success or raises requests.HTTPError on unrecoverable errors.
    """
    sess = session or requests
    # Host for metrics and throttle decisions
    host = url.rsplit("//", maxsplit=1)[-1].split("/", maxsplit=1)[0].lower()
    host = host.split(":")[0]
    # If endpoint is disabled via state_sync (direct path) or throttle manager, avoid external calls
    try:
        if state_sync.get_disabled_flag(
            urlparse(url).path,
        ) or _GLOBAL_THROTTLE_MANAGER.is_endpoint_disabled(url):
            from types import SimpleNamespace

            return SimpleNamespace(
                status_code=429, headers={}, text="disabled", json=dict,
            )
    except Exception:
        pass

    attempt = 0
    # Ensure throttle configuration is loaded (endpoint & bucket) once per process
    global _THROTTLE_CONFIG_LOADED
    try:
        _THROTTLE_CONFIG_LOADED
    except NameError:
        _THROTTLE_CONFIG_LOADED = False
    if not _THROTTLE_CONFIG_LOADED:
        try:
            cfg_path = Path(__file__).resolve().parents[2] / "config" / "settings.yaml"
            if cfg_path.exists():
                with cfg_path.open(encoding="utf-8") as f:
                    cfg = yaml.safe_load(f) or {}
                throttle_bucket_cfg = (cfg.get("data_sources") or {}).get(
                    "throttle_bucket_by_host", {},
                )
                for host, b in (throttle_bucket_cfg or {}).items():
                    try:
                        _GLOBAL_THROTTLE_MANAGER.set_bucket(
                            host,
                            TokenBucket(
                                capacity=b.get("capacity", 10), rate=b.get("rate", 1.0),
                            ),
                        )
                    except Exception:
                        pass
                throttle_bucket_endpoint_cfg = (cfg.get("data_sources") or {}).get(
                    "throttle_bucket_by_endpoint", {},
                )
                for host, endpoints in (throttle_bucket_endpoint_cfg or {}).items():
                    for path_prefix, b in endpoints.items():
                        try:
                            _GLOBAL_THROTTLE_MANAGER.set_endpoint_bucket(
                                host,
                                path_prefix,
                                TokenBucket(
                                    capacity=b.get("capacity", 10),
                                    rate=b.get("rate", 1.0),
                                ),
                            )
                        except Exception:
                            pass
                throttle_endpoint_cfg = (cfg.get("data_sources") or {}).get(
                    "throttle_by_endpoint", {},
                )
                for host, endpoints in (throttle_endpoint_cfg or {}).items():
                    for path_prefix, mi in endpoints.items():
                        try:
                            _GLOBAL_THROTTLE_MANAGER.set_endpoint_min_interval(
                                host, path_prefix, float(mi),
                            )
                        except Exception:
                            pass
        finally:
            _THROTTLE_CONFIG_LOADED = True

    # If provided, ensure we wait for per-host (or per-endpoint) min interval
    if min_interval is None:
        # Derive min_interval from config settings by host
        try:
            cfg_path = Path(__file__).resolve().parents[2] / "config" / "settings.yaml"
            if cfg_path.exists():
                with cfg_path.open(encoding="utf-8") as f:
                    cfg = yaml.safe_load(f) or {}
                throttle_cfg = (cfg.get("data_sources") or {}).get(
                    "throttle_by_host", {},
                )
                host = url.rsplit("//", maxsplit=1)[-1].split("/", maxsplit=1)[0].lower()
                # strip port if present
                host = host.split(":")[0]
                min_interval = float(throttle_cfg.get(host, 0.5))
                # if endpoint override exists, prefer that
                try:
                    endpoint_min = _GLOBAL_THROTTLE_MANAGER.get_min_interval(
                        url, default=min_interval,
                    )
                    if endpoint_min:
                        min_interval = float(endpoint_min)
                except Exception:
                    pass
            if logger:
                logger.debug(
                    f"[HTTP] Using min_interval={min_interval}s for host={host}",
                )
            else:
                min_interval = 0.5
        except Exception:
            min_interval = 0.5
    # If a token bucket is configured for this host, block until a token is available
    tb = _GLOBAL_THROTTLE_MANAGER.get_bucket(url)
    if tb is not None:
        try:
            tb.consume(tokens=1.0, block=True)
        except Exception:
            # fallback to host min_interval sleep
            if min_interval:
                try:
                    wait_for_host(url, min_interval)
                except Exception:
                    pass
    elif min_interval:
        try:
            wait_for_host(url, min_interval)
        except Exception:
            # best effort; do not fail if throttle module is unavailable
            pass

    attempt = 0
    while True:
        attempt += 1
        try:
            r = sess.get(url, headers=headers, params=params, timeout=timeout)
            if r.status_code == 429:
                # Rate limited — try to deduce wait time from Retry-After header
                retry_after = r.headers.get("Retry-After")
                wait = None
                if retry_after:
                    try:
                        wait = int(retry_after)
                    except Exception:
                        try:
                            # Fallback to converting via string -> float -> int
                            wait = int(float(str(retry_after)))
                        except Exception:
                            wait = None
                if wait is None:
                    wait = backoff * (2 ** (attempt - 1))
                    if logger:
                        logger.warning(
                            f"[HTTP] Rate limited (429) for {url}, attempt #{attempt}, sleeping {wait}s",
                        )
                    # metrics: increment host-level 429
                    try:
                        host_key = host
                        increment_metric(host_key, "429")
                    except Exception:
                        pass
                time.sleep(wait)
                if attempt >= retries:
                    # Re-raise status as exception
                    r.raise_for_status()
                    return r
                continue

            # Raise for 4xx/5xx except 429 which is handled above
            r.raise_for_status()
            return r

        except requests.HTTPError:
            # If we've tried enough times, rethrow
            if attempt >= retries:
                raise
            # If HTTP 5xx, apply backoff
            if logger:
                logger.warning(
                    f"[HTTP] HTTP error while fetching {url}. Attempt #{attempt}/{retries}. Retrying...",
                )
            # metrics: increment host-level http_error count
            try:
                host_key = url.rsplit("//", maxsplit=1)[-1].split("/", maxsplit=1)[0].split(":", maxsplit=1)[0]
                increment_metric(host_key, "http_error")
            except Exception:
                pass
            time.sleep(backoff * (2 ** (attempt - 1)))
            continue
        except requests.RequestException as exc:
            # Network issue or similar – retry
            if attempt >= retries:
                raise
            if logger:
                logger.warning(
                    f"[HTTP] Network error for {url}: {exc}. Attempt #{attempt}/{retries}. Retrying...",
                )
            try:
                host_key = url.rsplit("//", maxsplit=1)[-1].split("/", maxsplit=1)[0].split(":", maxsplit=1)[0]
                increment_metric(host_key, "network_error")
            except Exception:
                pass
            time.sleep(backoff * (2 ** (attempt - 1)))
            continue


def get_min_interval_for_host(url: str) -> float:
    """Return the configured min_interval per host; default to 0.5s."""
    try:
        cfg_path = Path(__file__).resolve().parents[2] / "config" / "settings.yaml"
        if cfg_path.exists():
            with cfg_path.open(encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
            throttle_cfg = (cfg.get("data_sources") or {}).get("throttle_by_host", {})
            host = url.rsplit("//", maxsplit=1)[-1].split("/", maxsplit=1)[0].lower()
            host = host.split(":")[0]
            return float(throttle_cfg.get(host, 0.5))
    except Exception:
        pass

    # If endpoint is disabled via throttle manager & state sync, return a 429-like response to avoid external calls
    # (disabled check handled earlier in the function)
    return 0.5
