"""Utility to capture multi-season match snapshots for Phase 2 Lite.

This script fetches historical fixtures from football-data.org and stores
them under data/snapshots/<league>/season_<year>.json so that downstream
feature jobs can build rolling statistics without live API calls.

Usage examples:
    python scripts/data_ingest/historical_pull.py --league la-liga --seasons 2022,2023
    python scripts/data_ingest/historical_pull.py --league premier-league --years-back 3

To call the football-data.org API you must set the FOOTBALL_DATA_API_KEY
environment variable (or supply --api-key). The script is defensive about
rate limits and adds a lightweight retry with exponential back-off.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import requests

# football-data.org uses a limited set of league codes; we mirror the CLI mapping
LEAGUE_MAP: Dict[str, Tuple[str, str]] = {
    "la-liga": ("PD", "la-liga"),
    "laliga": ("PD", "la-liga"),
    "premier-league": ("PL", "premier-league"),
    "premierleague": ("PL", "premier-league"),
    "bundesliga": ("BL1", "bundesliga"),
    "serie-a": ("SA", "serie-a"),
    "seriea": ("SA", "serie-a"),
    "ligue-1": ("FL1", "ligue-1"),
    "ligue1": ("FL1", "ligue-1"),
}

RATE_LIMIT_STATUS = 429
DEFAULT_RETRIES = 3


@dataclass(frozen=True)
class LeagueInfo:
    code: str
    folder: str

    @classmethod
    def from_key(cls, key: str) -> "LeagueInfo":
        try:
            code, folder = LEAGUE_MAP[key.lower()]
        except KeyError as exc:
            raise ValueError(
                f"Unknown league '{key}'. Supported: {', '.join(sorted({k for k in LEAGUE_MAP.keys() if '-' in k}))}"
            ) from exc
        return cls(code=code, folder=folder)


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch historical fixtures and cache snapshots.")
    parser.add_argument("--league", required=True, help="League identifier (e.g. la-liga, premier-league).")
    parser.add_argument(
        "--seasons",
        help="Comma-separated list of seasons (e.g. 2021,2022). Overrides --years-back if provided.",
    )
    parser.add_argument(
        "--years-back",
        type=int,
        default=2,
        help="Number of completed seasons to pull counting backwards from the current season.",
    )
    parser.add_argument(
        "--api-key",
        help="Optional explicit football-data API key; otherwise FOOTBALL_DATA_API_KEY env var is used.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.2,
        help="Seconds to sleep between API calls when fetching multiple seasons (avoids rate limits).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing snapshot files instead of skipping them.",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def resolve_api_key(explicit: Optional[str]) -> str:
    api_key = explicit or os.getenv("FOOTBALL_DATA_API_KEY")
    if not api_key:
        raise SystemExit("FOOTBALL_DATA_API_KEY not set and --api-key not provided.")
    return api_key


def resolve_seasons(raw: Optional[str], years_back: int) -> List[int]:
    current_year = datetime.utcnow().year
    if raw:
        seasons: List[int] = []
        for chunk in raw.split(","):
            chunk = chunk.strip()
            if not chunk:
                continue
            try:
                seasons.append(int(chunk))
            except ValueError as exc:
                raise SystemExit(f"Invalid season value '{chunk}'. Must be an integer like 2023.") from exc
        return sorted(set(seasons))
    # Football seasons refer to starting year; assume we want completed seasons.
    return [current_year - offset for offset in range(1, years_back + 1)]


def fetch_matches(api_key: str, league: LeagueInfo, season: int) -> Dict:
    url = f"https://api.football-data.org/v4/competitions/{league.code}/matches"
    headers = {"X-Auth-Token": api_key}
    params = {"season": season}

    attempt = 0
    while True:
        attempt += 1
        response = requests.get(url, headers=headers, params=params, timeout=30)
        if response.status_code == RATE_LIMIT_STATUS and attempt <= DEFAULT_RETRIES:
            wait = min(5 * attempt, 20)
            print(f"[RATE LIMIT] 429 received for season {season}. Sleeping {wait}s before retry {attempt}/{DEFAULT_RETRIES}...")
            time.sleep(wait)
            continue
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise RuntimeError(
                f"Failed to fetch data for {league.code} season {season}: {exc} (status={response.status_code})"
            ) from exc
        payload = response.json()
        payload["fetched_at"] = datetime.utcnow().isoformat()
        payload["competition_code"] = league.code
        payload["season"] = season
        return payload


def write_snapshot(league: LeagueInfo, season: int, payload: Dict, force: bool) -> Path:
    base_dir = Path("data") / "snapshots" / league.folder
    base_dir.mkdir(parents=True, exist_ok=True)
    target = base_dir / f"season_{season}.json"
    if target.exists() and not force:
        print(f"[SKIP] Snapshot already exists: {target}")
        return target

    tmp_path = target.with_suffix(".tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    tmp_path.replace(target)
    print(f"[WRITE] Stored snapshot: {target}")
    return target


def main(argv: Optional[Iterable[str]] = None) -> None:
    args = parse_args(argv)
    try:
        league = LeagueInfo.from_key(args.league)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    api_key = resolve_api_key(args.api_key)
    seasons = resolve_seasons(args.seasons, args.years_back)
    print(f"[START] Fetching {len(seasons)} season(s) for {args.league} -> competition {league.code}")

    for index, season in enumerate(seasons, start=1):
        print(f"[FETCH] ({index}/{len(seasons)}) Season {season}")
        try:
            payload = fetch_matches(api_key, league, season)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            print(f"[ERROR] Failed to fetch season {season}: {exc}")
            continue
        write_snapshot(league, season, payload, force=args.force)
        if index < len(seasons):
            time.sleep(max(args.delay, 0.0))

    print("[DONE] Historical snapshots up to date.")


if __name__ == "__main__":
    main()
