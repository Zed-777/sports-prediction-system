#!/usr/bin/env python3
"""
Unified fetcher for Football-Data.org (v4) and API-Football (RapidAPI v3).

Provides functions used by the tests and supports a small CLI to write CSV backups.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path

import requests
from app.utils.http import safe_request_get

ROOT = Path(__file__).parent.parent
BACKUP_CSV = ROOT / 'data' / 'backup_csv'
BACKUP_CSV.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR = ROOT / 'data' / 'processed' / 'historical'
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
LAST_PROCESSED = PROCESSED_DIR / 'last_processed.json'

FD_API_URL = 'https://api.football-data.org/v4'
AF_API_URL = 'https://v3.football.api-sports.io'


def read_env_file_for_key(key_name: str) -> str | None:
    env_file = ROOT / '.env'
    if not env_file.exists():
        return None
    for line in env_file.read_text(encoding='utf-8').splitlines():
        if '=' in line and not line.strip().startswith('#'):
            k, v = line.split('=', 1)
            if k.strip() == key_name and v.strip():
                return v.strip()
    return None


# Using centralized safe_request_get from app.utils.http for consistent throttling & retries


def fetch_fd_matches(api_key: str, competition: str, season: str) -> list[dict]:
    headers = {'X-Auth-Token': api_key}
    url = f"{FD_API_URL}/competitions/{competition}/matches?season={season}"
    resp = safe_request_get(url, headers=headers, retries=4)
    data = resp.json()
    results: list[dict] = []
    for m in data.get('matches', []):
        results.append({
            'id': m.get('id'),
            'date': (m.get('utcDate') or '')[:10],
            'home_team': m.get('homeTeam', {}).get('name'),
            'away_team': m.get('awayTeam', {}).get('name'),
            'home_score': (m.get('score') or {}).get('fullTime', {}).get('homeTeam'),
            'away_score': (m.get('score') or {}).get('fullTime', {}).get('awayTeam'),
            'status': (m.get('status') or 'FINISHED').lower(),
        })
    return results


def fetch_fd_match_detail(api_key: str, match_id: int) -> dict:
    headers = {'X-Auth-Token': api_key}
    url = f"{FD_API_URL}/matches/{match_id}"
    resp = safe_request_get(url, headers=headers, retries=3)
    data = resp.json()
    m = data.get('match', {})
    score = (m.get('score') or {}).get('fullTime', {})
    return {'home_score': score.get('homeTeam'), 'away_score': score.get('awayTeam')}


def fetch_af_matches(api_key: str, league_id: str, season: str) -> list[dict]:
    headers = {'x-rapidapi-key': api_key, 'x-rapidapi-host': 'v3.football.api-sports.io'}
    url = f"{AF_API_URL}/fixtures?league={league_id}&season={season}"
    resp = safe_request_get(url, headers=headers, retries=4)
    parsed = resp.json()
    results: list[dict] = []
    for item in parsed.get('response', []):
        fixture = item.get('fixture', {})
        teams = item.get('teams', {})
        score = item.get('score', {}).get('fulltime', {}) or {}
        results.append(
            {
                'id': fixture.get('id'),
                'date': (fixture.get('date') or '')[:10],
                'home_team': teams.get('home', {}).get('name'),
                'away_team': teams.get('away', {}).get('name'),
                'home_score': score.get('home'),
                'away_score': score.get('away'),
                'status': 'finished' if fixture.get('status', {}).get('short') == 'FT' else 'scheduled',
            }
        )
    return results


def write_csv(matches: list[dict], filename: str):
    out = BACKUP_CSV / filename
    with open(out, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(
            f, fieldnames=['id', 'home_team', 'away_team', 'date', 'home_score', 'away_score', 'status']
        )
        writer.writeheader()
        for m in matches:
            writer.writerow(
                {
                    'id': m.get('id'),
                    'home_team': m.get('home_team'),
                    'away_team': m.get('away_team'),
                    'date': m.get('date'),
                    'home_score': m.get('home_score'),
                    'away_score': m.get('away_score'),
                    'status': m.get('status'),
                }
            )


def load_last_processed() -> dict:
    if not LAST_PROCESSED.exists():
        return {}
    try:
        return json.loads(LAST_PROCESSED.read_text(encoding='utf-8'))
    except Exception:
        return {}


def save_last_processed(data: dict):
    LAST_PROCESSED.parent.mkdir(parents=True, exist_ok=True)
    LAST_PROCESSED.write_text(json.dumps(data, indent=2), encoding='utf-8')


def parse_cli_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Fetch historical matches for FD/AF')
    parser.add_argument('--fd', action='store_true', help='Fetch from Football-Data.org (v4)')
    parser.add_argument('--af', action='store_true', help='Fetch from API-Football (RapidAPI)')
    parser.add_argument('--competition', type=str, default='PD', help='FD competition code or AF league ID')
    parser.add_argument('--seasons', type=str, nargs='+', default=['2023'], help='Seasons to fetch (space separated)')
    parser.add_argument('--outfile', type=str, default=None, help='CSV filename (optional)')
    parser.add_argument('--incremental', action='store_true', help='Only fetch matches after last processed date')
    return parser.parse_args()


def _filter_incremental(matches: list[dict], last_date_str: str | None) -> list[dict]:
    if not last_date_str:
        return matches
    out = [m for m in matches if (m.get('date') or '') > last_date_str]
    return out


def main() -> None:
    args = parse_cli_args()
    last = load_last_processed()
    all_matches: list[dict] = []
    metrics = {
        'football_data': {'total_requests': 0, '403': 0, '429': 0},
        'api_football': {'total_requests': 0, '403': 0, '429': 0},
    }
    if args.fd:
        api_key = os.environ.get('FOOTBALL_DATA_API_KEY') or read_env_file_for_key('FOOTBALL_DATA_API_KEY')
        if not api_key:
            print('FOOTBALL_DATA_API_KEY not set; skipping FD fetch')
        else:
            for s in args.seasons:
                try:
                    print(f'Fetching FD {args.competition} season {s}...')
                    metrics['football_data']['total_requests'] += 1
                    matches = fetch_fd_matches(api_key, args.competition, s)
                    if args.incremental:
                        last_date = last.get('football_data', {}).get(args.competition)
                        matches = _filter_incremental(matches, last_date)
                    for m in matches:
                        if m.get('status') == 'finished' and (m.get('home_score') is None or m.get('away_score') is None):
                            try:
                                detail = fetch_fd_match_detail(api_key, int(m.get('id')))
                                m['home_score'] = detail.get('home_score')
                                m['away_score'] = detail.get('away_score')
                            except Exception as e:
                                print(f'  -> detail fetch failed for ID {m.get("id")}: {e}')
                    all_matches.extend(matches)
                    if matches:
                        max_date = max([m.get('date') or '' for m in matches])
                        last.setdefault('football_data', {})[args.competition] = max_date
                        save_last_processed(last)
                except requests.HTTPError as e:
                    status = getattr(e.response, 'status_code', None)
                    message = getattr(e.response, 'text', str(e))
                    print(f'Failed to fetch FD {args.competition} season {s}: HTTP {status} {message}')
                    if status and status == 403:
                        metrics['football_data']['403'] += 1
                        af_key = os.environ.get('API_FOOTBALL_KEY') or read_env_file_for_key('API_FOOTBALL_KEY')
                        af_league = os.environ.get('API_FOOTBALL_LEAGUE') or args.competition
                        if af_key:
                            print(f"  -> Attempting API-Football fallback for {af_league} season {s}...")
                            try:
                                matches_af = fetch_af_matches(af_key, af_league, s)
                                if matches_af:
                                    all_matches.extend(matches_af)
                                    print(f"  -> API-Football fallback saved {len(matches_af)} matches for season {s}")
                            except Exception as af_e:
                                print(f'  -> API-Football fallback failed: {af_e}')
                    elif status and status == 429:
                        metrics['football_data']['429'] += 1
                    if status == 403:
                        print('  -> Permission issue (403). Consider subscription level or using API-Football as fallback.')
                    elif status == 429:
                        print('  -> Rate limit exceeded (429). Increase wait/backoff or schedule fetchs later.')

    if args.af:
        api_key = os.environ.get('API_FOOTBALL_KEY') or read_env_file_for_key('API_FOOTBALL_KEY')
        if not api_key:
            print('API_FOOTBALL_KEY not set; skipping AF fetch')
        else:
            for s in args.seasons:
                try:
                    print(f'Fetching AF {args.competition} season {s}...')
                    metrics['api_football']['total_requests'] += 1
                    matches = fetch_af_matches(api_key, args.competition, s)
                    if args.incremental:
                        last_date = last.get('api_football', {}).get(args.competition)
                        matches = _filter_incremental(matches, last_date)
                    all_matches.extend(matches)
                    if matches:
                        max_date = max([m.get('date') or '' for m in matches])
                        last.setdefault('api_football', {})[args.competition] = max_date
                        save_last_processed(last)
                except requests.HTTPError as e:
                    status = getattr(e.response, 'status_code', None)
                    if status and status == 403:
                        metrics['api_football']['403'] += 1
                    elif status and status == 429:
                        metrics['api_football']['429'] += 1
                    print(f'Failed to fetch AF {args.competition} season {s}: HTTP {status} - {getattr(e.response, "text", str(e))}')
                except Exception as e:
                    print(f'Failed to fetch AF {args.competition} season {s}: {e}')

    if not args.fd and not args.af:
        print('No provider selected. Use --fd or --af')
        sys.exit(1)

    if not all_matches:
        print('No matches fetched.')
        sys.exit(0)

    out_file = args.outfile or f"{args.competition}_seasons_{'_'.join(args.seasons)}.csv"
    write_csv(all_matches, out_file)
    try:
        metrics_path = PROCESSED_DIR / 'fetch_metrics.json'
        metrics_path.write_text(json.dumps(metrics, indent=2), encoding='utf-8')
    except Exception:
        pass


if __name__ == '__main__':
    main()
