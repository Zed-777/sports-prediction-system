#!/usr/bin/env python3
"""Check Football-Data.org API key validity using the key found in environment or .env fallback.

This script will read the key from the environment `FOOTBALL_DATA_API_KEY`, or from `.env` file
if present in the workspace. It will then call a safe test endpoint and print results.

Note: This makes a single external request to Football-Data.org.
"""

import os
from pathlib import Path

from app.utils.http import safe_request_get

ROOT = Path(__file__).parent.parent
ENV_FILE = ROOT / ".env"


def read_env_file_for_key(key_name: str):
    if not ENV_FILE.exists():
        return None
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            if k.strip() == key_name and v.strip():
                return v.strip()
    return None


def main():
    key = os.getenv("FOOTBALL_DATA_API_KEY") or read_env_file_for_key(
        "FOOTBALL_DATA_API_KEY",
    )
    if not key:
        print("No Football-Data.org API key found in environment or .env file.")
        return

    print("Using Football-Data.org API key from environment or .env")

    url = "https://api.football-data.org/v4/competitions/PD"
    headers = {"X-Auth-Token": key}
    try:
        resp = safe_request_get(url, headers=headers, timeout=15, logger=None)
        print("Status code:", resp.status_code)
        if resp.status_code == 200:
            data = resp.json()
            print("Competition name:", data.get("name"))
            print("Available seasons count:", len(data.get("seasons", [])))
        else:
            print("Response body (truncated):", str(resp.text)[:200])
    except Exception as e:
        print("Error calling Football-Data API:", e)


if __name__ == "__main__":
    main()
