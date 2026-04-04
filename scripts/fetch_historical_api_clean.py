#!/usr/bin/env python3
"""Clean unified fetcher for Football-Data.org (v4) and API-Football (RapidAPI v3).

This is a single, small script to replace the corrupted `fetch_historical_api.py` during cleanup.
"""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).parent.parent
BACKUP_CSV = ROOT / "data" / "backup_csv"
PROCESSED_DIR = ROOT / "data" / "processed" / "historical"
LAST_PROCESSED = PROCESSED_DIR / "last_processed.json"

FD_API_URL = "https://api.football-data.org/v4"
AF_API_URL = "https://v3.football.api-sports.io"


def read_env_file_for_key(key_name: str) -> str | None:
    env_file = ROOT / ".env"
    if not env_file.exists():
        return None
    for line in env_file.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            if k.strip() == key_name and v.strip():
                return v.strip()
    return None


# Reuse the centralized safe_request_get from app.utils.http for consistent throttling and backoff


def write_csv(matches: list[dict], filename: str):
    out = BACKUP_CSV / filename
    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "id",
                "home_team",
                "away_team",
                "date",
                "home_score",
                "away_score",
                "status",
            ],
        )
        writer.writeheader()
        for m in matches:
            writer.writerow(
                {
                    "id": m.get("id"),
                    "home_team": m.get("home_team"),
                    "away_team": m.get("away_team"),
                    "date": m.get("date"),
                    "home_score": m.get("home_score"),
                    "away_score": m.get("away_score"),
                    "status": m.get("status"),
                },
            )


def main() -> None:
    # small noisy program for tests — not intended for production
    print("This is fetch_historical_api_clean. Use it as a temporary clean fetcher.")


if __name__ == "__main__":
    main()
