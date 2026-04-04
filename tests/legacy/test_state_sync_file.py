import os
import time

from app.utils import state_sync


def _cleanup_file():
    try:
        state_sync._clear_redis_client_for_tests()
    except Exception:
        pass
    try:
        os.remove("data/cache/disabled_flags.json")
    except Exception:
        pass


def test_state_sync_file_ops():
    _cleanup_file()
    host = "filehost.example"
    path = "/v1/test"
    ts = time.time() + 1800

    # Ensure no flag set
    assert state_sync.get_disabled_flag(host, path) is None

    # Set with host/path
    state_sync.set_disabled_flag(host, path, ts, reason="429", set_by="test")
    val = state_sync.get_disabled_flag(host, path)
    assert val is not None and val > time.time()

    # Clean with host/path
    state_sync.clear_disabled_flag(host, path)
    assert state_sync.get_disabled_flag(host, path) is None

    # Legacy path-only
    legacy_path = "/v2/legacy"
    ts2 = time.time() + 900
    state_sync.set_disabled_flag(legacy_path, ts2)
    val = state_sync.get_disabled_flag(legacy_path)
    assert val is not None and val > time.time()

    # Clean again
    state_sync.clear_disabled_flag(legacy_path)
    assert state_sync.get_disabled_flag(legacy_path) is None

    # TTL expiration: set a short TTL and ensure it expires
    short_path = "/v2/shortttl"
    ts_short = time.time() + 1
    state_sync.set_disabled_flag(short_path, ts_short)
    assert state_sync.get_disabled_flag(short_path) is not None
    time.sleep(1.5)
    assert state_sync.get_disabled_flag(short_path) is None

    _cleanup_file()
