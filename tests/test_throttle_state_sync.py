import time
from app.utils.throttle import ThrottleManager
from app.utils.state_sync import set_disabled_flag, get_disabled_flag


def test_throttle_manager_is_endpoint_disabled():
    tm = ThrottleManager()
    host = "api.football-data.org"
    path = "/v4/matches"
    tm.set_endpoint_min_interval(host, path, 1.0)
    # Ensure not disabled initially
    assert not tm.is_endpoint_disabled(f"https://{host}{path}")
    # Set disabled flag in state_sync
    disabled_until = time.time() + 5
    set_disabled_flag(path, disabled_until)
    # Now check
    assert tm.is_endpoint_disabled(f"https://{host}{path}")
    # Wait expiration
    time.sleep(5)
    assert not tm.is_endpoint_disabled(f"https://{host}{path}")
