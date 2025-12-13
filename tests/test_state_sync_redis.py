import json
import time
import pytest

from app.utils import state_sync


def test_state_sync_redis_ops_with_fakeredis():
    fakeredis = pytest.importorskip('fakeredis')
    r = fakeredis.FakeRedis()
    # Inject the fakeredis client for tests
    state_sync._set_redis_client_for_tests(r)

    host = 'test.example.com'
    path = '/v1/foo'

    # Ensure no flag set
    state_sync.clear_disabled_flag(host, path)
    assert state_sync.get_disabled_flag(host, path) is None

    disabled_until = time.time() + 3600
    state_sync.set_disabled_flag(host, path, disabled_until, reason='429', set_by='test')

    # Check Redis' storage and state_sync get method
    val = r.hget(f'disabled:{host}', path)
    assert val is not None
    obj = json.loads(val)
    assert float(obj.get('disabled_until')) == pytest.approx(disabled_until, rel=1e-3)
    assert state_sync.get_disabled_flag(host, path) is not None

    # Clearing should remove the flag
    state_sync.clear_disabled_flag(host, path)
    assert state_sync.get_disabled_flag(host, path) is None

    # Clean up the test-injected client
    state_sync._clear_redis_client_for_tests()


def test_state_sync_redis_expiry_with_fakeredis():
    fakeredis = pytest.importorskip('fakeredis')
    r = fakeredis.FakeRedis()
    state_sync._set_redis_client_for_tests(r)

    host = 'test.example.com'
    path = '/v1/short'
    short_ts = time.time() + 1
    state_sync.set_disabled_flag(host, path, short_ts, reason='429', set_by='test')
    assert state_sync.get_disabled_flag(host, path) is not None
    time.sleep(1.5)
    assert state_sync.get_disabled_flag(host, path) is None

    state_sync._clear_redis_client_for_tests()
