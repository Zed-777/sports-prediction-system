from __future__ import annotations

import threading
import time
from typing import Dict
from urllib.parse import urlparse
from app.utils import state_sync


class ThrottleManager:
    """Global per-host throttling manager.

    Use ThrottleManager.wait(url, min_interval) before making an HTTP call to ensure the minimum
    spacing between calls to a host is respected. This is a simple cooperative throttle suitable
    for single-process use and for small concurrent programs.
    """

    def __init__(self) -> None:
        self._last_call: Dict[str, float] = {}
        self._locks: Dict[str, threading.Lock] = {}
        self._buckets: Dict[str, 'TokenBucket'] = {}
        # Endpoint specific mappings: host -> {path_prefix: min_interval}
        self._endpoint_min_intervals: Dict[str, Dict[str, float]] = {}
        # Endpoint specific token buckets: host -> {path_prefix: TokenBucket}
        self._endpoint_buckets: Dict[str, Dict[str, 'TokenBucket']] = {}

    def _get_host(self, url: str) -> str:
        parsed = urlparse(url)
        return parsed.netloc.lower()

    def wait(self, url: str, min_interval: float = 0.5) -> None:
        host = self._get_host(url)
        if host not in self._locks:
            self._locks[host] = threading.Lock()
        lock = self._locks[host]

        with lock:
            now = time.time()
            last = self._last_call.get(host, 0.0)
            elapsed = now - last
            if elapsed < min_interval:
                sleep_for = min_interval - elapsed
                time.sleep(sleep_for)
            self._last_call[host] = time.time()

    def set_bucket(self, host: str, bucket: 'TokenBucket') -> None:
        self._buckets[host] = bucket

    def set_endpoint_bucket(self, host: str, path_prefix: str, bucket: 'TokenBucket') -> None:
        m = self._endpoint_buckets.get(host)
        if m is None:
            m = {}
            self._endpoint_buckets[host] = m
        m[path_prefix] = bucket

    def set_endpoint_min_interval(self, host: str, path_prefix: str, min_interval: float) -> None:
        m = self._endpoint_min_intervals.get(host)
        if m is None:
            m = {}
            self._endpoint_min_intervals[host] = m
        m[path_prefix] = float(min_interval)

    def get_bucket(self, url: str) -> 'TokenBucket | None':
        host = self._get_host(url)
        # Prefer endpoint-specific bucket matching the longest path prefix
        path = urlparse(url).path
        endpoint_buckets = self._endpoint_buckets.get(host) or {}
        if endpoint_buckets:
            # Find the longest matching prefix
            matching = [(p, b) for p, b in endpoint_buckets.items() if path.startswith(p)]
            if matching:
                matching.sort(key=lambda x: len(x[0]), reverse=True)
                return matching[0][1]
        # Fall back to host-level bucket
        return self._buckets.get(host)

    def is_endpoint_disabled(self, url: str) -> bool:
        """Check if an endpoint is disabled via state_sync. Accepts full URL and checks
        for the longest matching configured endpoint prefix.
        """
        try:
            host = self._get_host(url)
            path = urlparse(url).path
            # First check direct path in state_sync for a forced disabled flag
            try:
                if state_sync.get_disabled_flag(path):
                    return True
            except Exception:
                pass
            # Then try to find a matching endpoint prefix
            endpoint_map = self._endpoint_min_intervals.get(host, {}) or {}
            matching = [(p, v) for p, v in endpoint_map.items() if path.startswith(p)]
            # Prefer longest match
            if matching:
                matching.sort(key=lambda x: len(x[0]), reverse=True)
                prefix = matching[0][0]
                # Use state_sync to check disabled flag for this prefix key
                try:
                    disabled_until = state_sync.get_disabled_flag(prefix)
                    if disabled_until and disabled_until > time.time():
                        return True
                except Exception:
                    pass
            return False
        except Exception:
            return False

    def get_min_interval(self, url: str, default: float = 0.5) -> float:
        host = self._get_host(url)
        path = urlparse(url).path
        # Check endpoint-specific intervals first
        endpoint_map = self._endpoint_min_intervals.get(host) or {}
        if endpoint_map:
            matching = [(p, v) for p, v in endpoint_map.items() if path.startswith(p)]
            if matching:
                matching.sort(key=lambda x: len(x[0]), reverse=True)
                return float(matching[0][1])
        # Fall back to host-level bucket interval if available
        return default


# A global manager usable by other modules
_GLOBAL_THROTTLE_MANAGER = ThrottleManager()


def wait_for_host(url: str, min_interval: float = 0.5) -> None:
    _GLOBAL_THROTTLE_MANAGER.wait(url, min_interval)


class TokenBucket:
    """Simple token bucket implementation for rate limiting.

    - capacity: max tokens stored
    - rate: tokens replenished per second
    """

    def __init__(self, capacity: float = 1.0, rate: float = 1.0) -> None:
        self.capacity = float(capacity)
        self.rate = float(rate)
        self._tokens = self.capacity
        self._last = time.time()
        self._lock = threading.Lock()

    def _add_tokens(self) -> None:
        now = time.time()
        elapsed = now - self._last
        self._last = now
        added = elapsed * self.rate
        self._tokens = min(self.capacity, self._tokens + added)

    def consume(self, tokens: float = 1.0, block: bool = True) -> bool:
        """Consume tokens. If `block` is True, wait until tokens are available.
        Returns True if tokens were consumed, False otherwise (non-blocking).
        """
        while True:
            with self._lock:
                self._add_tokens()
                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return True
            if not block:
                return False
            # Wait a bit and try again
            time.sleep(max(0.01, 1.0 / (self.rate or 1.0)))

