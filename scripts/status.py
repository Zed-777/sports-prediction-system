"""Simple developer status script that lists disabled flags and metrics.

Usage:
  python scripts/status.py
"""

from __future__ import annotations

import json

from app.utils import state_sync
from app.utils.metrics import get_metrics


def main():
    flags = state_sync.list_disabled_flags()
    metrics = get_metrics()
    print("=== Disabled flags ===")
    if not flags:
        print("No disabled flags")
    else:
        print(json.dumps(flags, indent=2))
    print("\n=== Metrics ===")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
