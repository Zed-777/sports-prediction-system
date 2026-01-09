from __future__ import annotations

import threading
from collections import defaultdict
from typing import Dict


class MetricsCollector:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

    def increment(self, key: str, field: str, amount: int = 1) -> None:
        with self._lock:
            self._counts[key][field] += amount

    def get_counts(self) -> Dict[str, Dict[str, int]]:
        with self._lock:
            # return a shallow copy
            return {k: dict(v) for k, v in self._counts.items()}

    def reset(self) -> None:
        with self._lock:
            self._counts.clear()


# Global collector
_GLOBAL_METRICS = MetricsCollector()


def increment_metric(key: str, field: str, amount: int = 1) -> None:
    _GLOBAL_METRICS.increment(key, field, amount)


def get_metrics() -> Dict[str, Dict[str, int]]:
    return _GLOBAL_METRICS.get_counts()


def reset_metrics() -> None:
    _GLOBAL_METRICS.reset()
