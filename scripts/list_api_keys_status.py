#!/usr/bin/env python3
"""
List required API keys, whether they are present, and validate accessibility for supported providers.

This script:
- Reads environment variables and `.env.backup` if present to detect keys
- Validates Football-Data.org v4 key by calling `/competitions/PD`
- Validates API-Football key by calling a small fixture endpoint (if present)
- Reports other keys as present/missing; does not expose values
"""

import os
import re
from pathlib import Path

import requests
from app.utils.http import safe_request_get

ROOT = Path(__file__).parent.parent
ENV_BACKUP = ROOT / '.env.backup'
SECRETS_BACKUP = ROOT / 'secrets' / '.env.backup'

def parse_env_file(path: Path):
    out = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding='utf-8').splitlines():
        if '=' in line and not line.strip().startswith('#'):
            k, v = line.split('=', 1)
            out[k.strip()] = v.strip()
    return out


def get_key_value(name: str):
    # First check OS environment
    val = os.environ.get(name)
    if val:
        return val
    # Fallback to .env.backup
    if ENV_BACKUP.exists():
        envs = parse_env_file(ENV_BACKUP)
        return envs.get(name)
    # Also check secrets/.env.backup
    if SECRETS_BACKUP.exists():
        envs = parse_env_file(SECRETS_BACKUP)
        return envs.get(name)
    return None


def test_football_data_key(key: str):
    if not key:
        return False, 'No key provided'
    url = 'https://api.football-data.org/v4/competitions/PD'
    try:
        r = safe_request_get(url, headers={'X-Auth-Token': key}, timeout=15, logger=None)
        if r.status_code == 200:
            return True, '200 OK'
        return False, f'{r.status_code}: {r.text[:200]}'
    except Exception as e:
        return False, str(e)


def test_api_football_key(key: str, league_id: str = '140'):
    if not key:
        return False, 'No key provided'
    url = f'https://v3.football.api-sports.io/fixtures?league={league_id}&season=2023'
    try:
        r = safe_request_get(url, headers={'x-rapidapi-key': key, 'x-rapidapi-host': 'v3.football.api-sports.io'}, timeout=15, logger=None)
        if r.status_code == 200:
            return True, '200 OK'
        return False, f'{r.status_code}: {r.text[:200]}'
    except Exception as e:
        return False, str(e)


def presence_and_placeholder_check(key_value: str):
    if not key_value:
        return ('missing', '')
    # check for placeholder patterns
    if re.search(r'(YOUR_|your_|PLACEHOLDER|DUMMY|TEST_KEY)', key_value, re.IGNORECASE):
        return ('placeholder', '')
    return ('present', '')


def main():
    keys = [
        'FOOTBALL_DATA_API_KEY',
        'API_FOOTBALL_KEY',
        'SPORTSDATA_API_KEY',
        'SPORTSRADAR_API_KEY',
        'ODDS_API_KEY',
        'OPENMETEO_API_KEY'
    ]

    report = []
    for k in keys:
        val = get_key_value(k)
        status, _ = presence_and_placeholder_check(val)
        validated = 'n/a'
        notes = ''
        if k == 'FOOTBALL_DATA_API_KEY' and status == 'present':
            ok, msg = test_football_data_key(val)
            validated = 'OK' if ok else 'FAILED'
            notes = msg
        if k == 'API_FOOTBALL_KEY' and status == 'present':
            ok, msg = test_api_football_key(val)
            validated = 'OK' if ok else 'FAILED'
            notes = msg
        report.append({'key': k, 'status': status, 'validated': validated, 'notes': notes})

    # print report
    print('\n=== API Keys Status Report ===\n')
    for r in report:
        print(f"{r['key']}: {r['status']} (validated: {r['validated']}) {(' - ' + r['notes']) if r['notes'] else ''}")
    print('\nNote: Any key listed as "present" might still be restricted by subscription level (HTTP 403).')
    print('Keys marked as "placeholder" are placeholders and not real keys. Keys marked as "missing" are not set.')


if __name__ == '__main__':
    main()
