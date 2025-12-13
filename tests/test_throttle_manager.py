import time
from app.utils.throttle import wait_for_host


def test_throttle_waits_for_min_interval():
    url = 'https://example.com/path'
    # call once (sets last call); then immediately call again and ensure it waits
    wait_for_host(url, min_interval=0.3)
    start = time.time()
    wait_for_host(url, min_interval=0.3)
    elapsed = time.time() - start
    assert elapsed >= 0.29
