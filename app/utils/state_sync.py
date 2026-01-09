"""State synchronization utilities - file and optional Redis fallback.

Provides get_disabled_flag and set_disabled_flag for persisting endpoint disabled states.
If REDIS_URL is configured and redis-py is installed, Redis will be used for multi-process sync.
Otherwise, a JSON file under data/cache/disabled_flags.json is used.
"""

from __future__ import annotations

import json
import os
import time
from typing import Optional

_DISABLED_JSON_FILE = "data/cache/disabled_flags.json"

_REDIS_CLIENT = None
_USE_REDIS = False


def _init_redis() -> None:
    global _REDIS_CLIENT, _USE_REDIS
    try:
        import redis as _redis

        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            _REDIS_CLIENT = _redis.from_url(redis_url)
            _USE_REDIS = True
    except Exception:
        _REDIS_CLIENT = None
        _USE_REDIS = False


_init_redis()


def set_disabled_flag(
    host_or_path: str,
    path_or_disabled: float | str,
    disabled_until: float | None = None,
    reason: str | None = None,
    set_by: str = "app",
) -> None:
    """Set the disabled flag for a host+path combination or legacy key.

    Usage:
    - set_disabled_flag(host, path, disabled_until)
    - set_disabled_flag('/v3/injuries', disabled_until)  # legacy: stored under global
    """
    host = None
    path = None
    # Backward compatibility: if only two args and second is numeric, assume host_or_path is path
    if isinstance(path_or_disabled, (int, float)) and disabled_until is None:
        # called as set_disabled_flag('/v3/injuries', ts)
        host = "global"
        path = str(host_or_path)
        disabled_ts = float(path_or_disabled)
    else:
        # called as set_disabled_flag(host, path, disabled_until,..)
        host = str(host_or_path)
        path = str(path_or_disabled)
        disabled_ts = float(disabled_until or 0.0)

    if _USE_REDIS and _REDIS_CLIENT and host:
        try:
            # Use hash storage per host to store path metadata
            _REDIS_CLIENT.hset(
                f"disabled:{host}",
                path,
                json.dumps(
                    {
                        "disabled_until": disabled_ts,
                        "reason": reason or "unknown",
                        "set_by": set_by,
                    }
                ),
            )
            _REDIS_CLIENT.expire(
                f"disabled:{host}", int(max(1, disabled_ts - time.time()))
            )
            return
        except Exception:
            pass
    # Fallback to file-based storage (structured nested format)
    try:
        os.makedirs(os.path.dirname(_DISABLED_JSON_FILE), exist_ok=True)
        state = {}
        if os.path.exists(_DISABLED_JSON_FILE):
            with open(_DISABLED_JSON_FILE, "r", encoding="utf-8") as f:
                try:
                    state = json.load(f) or {}
                except Exception:
                    state = {}
        host_map = state.get(host, {}) or {}
        host_map[path] = {
            "disabled_until": float(disabled_ts),
            "reason": reason or "",
            "set_by": set_by,
        }
        state[host] = host_map
        with open(_DISABLED_JSON_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception:
        # Best effort: ignore errors
        return


def get_disabled_flag(host_or_path: str, path: str | None = None) -> Optional[float]:
    """Return the disabled_until epoch seconds for a given host & path or a legacy path-only lookup.

    Usage:
    - get_disabled_flag(host, path)
    - get_disabled_flag('/v3/injuries')  # legacy: checks global
    """
    # If path is not given, assume host_or_path is the legacy path under 'global'
    if path is None:
        host = "global"
        path = str(host_or_path)
    else:
        host = str(host_or_path)
    # Try Redis first
    if _USE_REDIS and _REDIS_CLIENT:
        try:
            val = _REDIS_CLIENT.hget(f"disabled:{host}", path)
            if val:
                try:
                    obj = json.loads(val)
                    ts = float(obj.get("disabled_until", 0.0))
                    if ts and ts > time.time():
                        return ts
                except Exception:
                    return None
        except Exception:
            pass
    # Fallback to file-based storage
    try:
        if os.path.exists(_DISABLED_JSON_FILE):
            with open(_DISABLED_JSON_FILE, "r", encoding="utf-8") as f:
                try:
                    state = json.load(f) or {}
                    host_map = state.get(host, {}) or {}
                    entry = host_map.get(path) or {}
                    val = float(entry.get("disabled_until", 0.0) or 0.0)
                    if val and val > time.time():
                        return val
                except Exception:
                    return None
    except Exception:
        return None
    return None


def _set_redis_client_for_tests(redis_client) -> None:
    """Helper for tests to inject a redis-like client (e.g., fakeredis) and enable Redis mode."""
    global _REDIS_CLIENT, _USE_REDIS
    _REDIS_CLIENT = redis_client
    _USE_REDIS = True


def _clear_redis_client_for_tests() -> None:
    """Helper for tests to clear test-injected redis client and disable Redis mode."""
    global _REDIS_CLIENT, _USE_REDIS
    _REDIS_CLIENT = None
    _USE_REDIS = False


def clear_disabled_flag(host_or_path: str, path: str | None = None) -> None:
    """Clear the disabled flag for host+path or legacy path.

    Usage:
    - clear_disabled_flag(host, path)
    - clear_disabled_flag('/v3/injuries')  # legacy: removes global path
    """
    if path is None:
        host = "global"
        path = str(host_or_path)
    else:
        host = str(host_or_path)
    if _USE_REDIS and _REDIS_CLIENT:
        try:
            _REDIS_CLIENT.hdel(f"disabled:{host}", path)
            return
        except Exception:
            pass
    # File fallback
    try:
        if os.path.exists(_DISABLED_JSON_FILE):
            with open(_DISABLED_JSON_FILE, "r", encoding="utf-8") as f:
                try:
                    state = json.load(f) or {}
                except Exception:
                    state = {}
            host_map = state.get(host, {}) or {}
            if path in host_map:
                del host_map[path]
            if host_map:
                state[host] = host_map
            else:
                state.pop(host, None)
            with open(_DISABLED_JSON_FILE, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
    except Exception:
        # best effort
        return


def list_disabled_flags() -> dict:
    """Return all disabled flags as a nested dict: {host: {path: metadata}}

    Works across Redis (lists hosts using key pattern) and file-based store.
    """
    if _USE_REDIS and _REDIS_CLIENT:
        try:
            out = {}
            keys = _REDIS_CLIENT.keys("disabled:*") or []
            for k in keys:
                host = (
                    k.decode().split(":", 1)[1]
                    if isinstance(k, bytes)
                    else str(k).split(":", 1)[1]
                )
                entries = _REDIS_CLIENT.hgetall(k)
                host_map = {}
                for p, v in entries.items():
                    try:
                        obj = json.loads(v)
                    except Exception:
                        obj = {}
                    host_map[p.decode() if isinstance(p, bytes) else p] = obj
                out[host] = host_map
            return out
        except Exception:
            return {}
    # File fallback
    try:
        if os.path.exists(_DISABLED_JSON_FILE):
            with open(_DISABLED_JSON_FILE, "r", encoding="utf-8") as f:
                try:
                    state = json.load(f) or {}
                except Exception:
                    state = {}
            return state
    except Exception:
        pass
    return {}


def clear_all_disabled_flags() -> None:
    """Clear all disabled flags from Redis or file store (best-effort)."""
    if _USE_REDIS and _REDIS_CLIENT:
        try:
            # Find keys and delete
            keys = _REDIS_CLIENT.keys("disabled:*") or []
            for k in keys:
                _REDIS_CLIENT.delete(k)
            return
        except Exception:
            pass
    # File fallback: delete the JSON file
    try:
        if os.path.exists(_DISABLED_JSON_FILE):
            os.remove(_DISABLED_JSON_FILE)
    except Exception:
        return
