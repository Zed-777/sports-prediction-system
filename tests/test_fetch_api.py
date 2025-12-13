import os
import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest
import requests

from scripts.fetch_historical_api import (
    fetch_af_matches,
    fetch_fd_matches,
    safe_request_get,
)


@pytest.mark.parametrize('status,should_raise', [(200, False), (403, True), (429, True)])
def test_safe_request_get(tmp_path, status, should_raise):
    url = 'https://api.football-data.org/test'
    with mock.patch('requests.get') as mock_get:
        # configure a fake response
        resp = mock.Mock()
        resp.status_code = status
        resp.raise_for_status.side_effect = requests.HTTPError(response=resp) if status != 200 else None
        resp.json.return_value = {}
        mock_get.return_value = resp
        if should_raise:
            with pytest.raises(requests.HTTPError):
                safe_request_get(url, headers=None, retries=1, backoff=0.1)
        else:
            r = safe_request_get(url, headers=None, retries=1, backoff=0.1)
            assert r == resp

def test_fetch_fd_matches_parsing(monkeypatch):
    # Simulate a FD v4 response
    fake_data = {'matches': [{'id': 1, 'utcDate': '2023-09-01T15:00:00Z', 'homeTeam': {'name': 'A'}, 'awayTeam': {'name': 'B'}, 'score': {'fullTime': {'homeTeam': 2, 'awayTeam': 1}}, 'status': 'FINISHED'}]}
    with mock.patch('scripts.fetch_historical_api.safe_request_get') as mock_get:
        mock_resp = mock.Mock()
        mock_resp.json.return_value = fake_data
        mock_get.return_value = mock_resp
        matches = fetch_fd_matches('FAKEKEY', 'PD', '2023')
        assert len(matches) == 1
        assert matches[0]['home_score'] == 2

def test_fetch_af_matches_parsing(monkeypatch):
    fake_resp = {'response': [{'fixture': {'id': 1, 'date': '2023-09-01T15:00:00Z', 'status': {'short': 'FT'}}, 'teams': {'home': {'name': 'A'}, 'away': {'name': 'B'}}, 'score': {'fulltime': {'home': 1, 'away': 0}}}]}
    with mock.patch('scripts.fetch_historical_api.safe_request_get') as mock_get:
        mock_resp = mock.Mock()
        mock_resp.json.return_value = fake_resp
        mock_get.return_value = mock_resp
        matches = fetch_af_matches('FAKEKEY', '40', '2023')
        assert matches[0]['home_score'] == 1

BACKUP_CSV = Path('data/backup_csv')


def _read_env_key(key: str) -> str | None:
    """Read a key from .env file if present"""
    env_file = Path('.env')
    if not env_file.exists():
        return None
    with env_file.open() as f:
        for line in f:
            line = line.strip()
            if line.startswith(f'{key}='):
                value = line.split('=', 1)[1]
                # Remove quotes if present
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                return value
    return None


@pytest.mark.skip(reason="Requires real API key; for manual testing only")
def test_fetch_football_data_org():
    api_key = os.environ.get('FOOTBALL_DATA_API_KEY') or _read_env_key('FOOTBALL_DATA_API_KEY')
    if not api_key or api_key.startswith('YOUR_'):
        pytest.skip('FOOTBALL_DATA_API_KEY not set or placeholder; skipping Football-Data.org API test')
    # Try fetching one season for PD
    # Use sys.executable to ensure we use the same Python as the test
    cmd = f'{sys.executable} scripts/fetch_historical_api.py --competition PD --seasons 2021 --fd --outfile test_fd_pd_2021.csv'
    result = subprocess.run(cmd, shell=True)
    assert result.returncode == 0
    assert (BACKUP_CSV / 'test_fd_pd_2021.csv').exists()


@pytest.mark.skip(reason="Requires real API key; for manual testing only")
def test_fetch_api_football():
    api_key = os.environ.get('API_FOOTBALL_KEY') or _read_env_key('API_FOOTBALL_KEY')
    if not api_key or api_key.startswith('YOUR_'):
        pytest.skip('API_FOOTBALL_KEY not set or placeholder; skipping API-Football test')
    # Try fetching one season for La Liga (league id 140)
    # Use sys.executable to ensure we use the same Python as the test
    cmd = f'{sys.executable} scripts/fetch_historical_api.py --competition 140 --seasons 2021 --af --outfile test_af_140_2021.csv'
    result = subprocess.run(cmd, shell=True)
    assert result.returncode == 0
    assert (BACKUP_CSV / 'test_af_140_2021.csv').exists()
