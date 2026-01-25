#!/usr/bin/env python3
"""
Fetch historical match data from API-Football (RapidAPI v3) for given league ids and seasons.

Writes CSVs to `data/backup_csv/` with columns that match existing backup CSVs so the collector can ingest them.

Usage (PowerShell):
  $env:API_FOOTBALL_KEY = "YOUR_RAPIDAPI_KEY"
  python scripts/fetch_api_football.py --leagues 140 --seasons 2018,2019,2020

Options:
  --leagues   Comma separated league ids (IDs used by API-Football)
  --seasons   Comma separated seasons (years)
  --outfile   Optional: write all matches to a single CSV (default: per league/season)

"""

import argparse
import csv
import os
import sys
import time
from pathlib import Path

from app.utils.http import safe_request_get

ROOT = Path(__file__).parent.parent
OUT_DIR = ROOT / "data" / "backup_csv"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def fetch_fixtures_for_league(api_key: str, league_id: int, season: int) -> list[dict]:
    url = (
        f"https://v3.football.api-sports.io/fixtures?league={league_id}&season={season}"
    )
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "v3.football.api-sports.io",
    }
    resp = safe_request_get(url, headers=headers, timeout=30, logger=None)
    if resp.status_code != 200:
        raise RuntimeError(f"API-Football error {resp.status_code}: {resp.text}")
    payload = resp.json()
    fixtures = []
    for item in payload.get("response", []):
        fixture = item.get("fixture", {})
        teams = item.get("teams", {})
        score = item.get("score", {})
        fixtures.append(
            {
                "id": fixture.get("id"),
                "date": (fixture.get("date") or "")[:10],
                "status": fixture.get("status", {}).get("short", "FT").lower(),
                "home_team": teams.get("home", {}).get("name"),
                "away_team": teams.get("away", {}).get("name"),
                "home_score": score.get("fulltime", {}).get("home"),
                "away_score": score.get("fulltime", {}).get("away"),
            }
        )
    return fixtures


def write_csv(rows: list[dict], out_path: Path):
    fieldnames = [
        "id",
        "home_team",
        "away_team",
        "date",
        "home_score",
        "away_score",
        "status",
    ]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--leagues", required=True, help="Comma-separated league ids (e.g., 140)"
    )
    parser.add_argument(
        "--seasons",
        required=True,
        help="Comma-separated seasons (years) e.g. 2019,2020",
    )
    parser.add_argument(
        "--outfile", help="Optional combined CSV path to write all matches into"
    )
    return parser.parse_args()


def read_env_file_for_key(key_name: str):
    env_file = Path(__file__).parent.parent / ".env"
    if not env_file.exists():
        return None
    for line in env_file.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            if k.strip() == key_name and v.strip():
                return v.strip()
    return None


def main():
    args = parse_args()
    # Try environment first; fallback to reading .env for convenience
    api_key = os.environ.get("API_FOOTBALL_KEY") or read_env_file_for_key(
        "API_FOOTBALL_KEY"
    )
    if not api_key:
        print(
            "No API_FOOTBALL_KEY found in environment or .env. Set it and re-run to fetch data."
        )
        sys.exit(0)

    leagues = [
        league_str.strip()
        for league_str in args.leagues.split(",")
        if league_str.strip()
    ]
    seasons = [int(s.strip()) for s in args.seasons.split(",") if s.strip()]

    all_rows = []
    for league in leagues:
        for season in seasons:
            print(
                f"Fetching API-Football fixtures: league {league}, season {season}..."
            )
            try:
                rows = fetch_fixtures_for_league(api_key, int(league), int(season))
                if not rows:
                    print(f"  -> no fixtures found for league {league} season {season}")
                    continue
                fname = OUT_DIR / f"api_football_{league}_{season}.csv"
                write_csv(rows, fname)
                print(f"  -> saved {len(rows)} fixtures to {fname}")
                all_rows.extend(rows)
                time.sleep(1)
            except Exception as e:
                print(
                    f"  -> failed to fetch fixtures for league {league} season {season}: {e}"
                )

    if args.outfile:
        out_path = Path(args.outfile)
        write_csv(all_rows, out_path)
        print(f"Wrote combined file: {out_path}")


if __name__ == "__main__":
    main()
