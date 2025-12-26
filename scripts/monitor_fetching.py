#!/usr/bin/env python3
"""
Simple monitoring script to parse fetch logs and metrics and raise alerts on frequent 403/429 responses.

It reads a metrics file `data/processed/historical/fetch_metrics.json` created by the fetch scripts when running with a `--metrics` flag (or we can log JSON lines).
"""

import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
METRICS = ROOT / "data" / "processed" / "historical" / "fetch_metrics.json"


def main():
    if not METRICS.exists():
        print(
            "No metrics file found. Run fetch scripts with metrics flag to create fetch_metrics.json"
        )
        return
    data = json.loads(METRICS.read_text(encoding="utf-8"))
    for provider, pv in data.items():
        total = pv.get("total_requests", 0)
        errors_403 = pv.get("403", 0)
        errors_429 = pv.get("429", 0)
        print(
            f"Provider: {provider} - Total: {total} - 403: {errors_403} - 429: {errors_429}"
        )
        if errors_403 > 0:
            print(
                "  -> WARNING: Permission errors observed: consider changing subscription or keys"
            )
        if errors_429 > 0:
            print(
                "  -> ALERT: Rate limits observed. Consider longer backoff or schedule frequency lower"
            )


if __name__ == "__main__":
    main()
