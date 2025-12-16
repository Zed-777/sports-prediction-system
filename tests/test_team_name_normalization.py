from scripts.collect_historical_results import HistoricalResultsCollector
from pathlib import Path
import json


def test_canonical_mapping(tmp_path, monkeypatch):
    proj_root = Path(__file__).resolve().parents[1]
    cfg_path = proj_root / 'config' / 'team_name_map.yaml'
    # Ensure mapping exists
    assert cfg_path.exists()
    collector = HistoricalResultsCollector()
    # Use _match_and_update indirectly by creating historical file and calling fetch with fake API
    league = 'la-liga'
    hist_dir = proj_root / 'data' / 'historical'
    hist_dir.mkdir(parents=True, exist_ok=True)
    record = {
        'match_id': 'val1',
        'match_date': '2025-12-19T00:00:00+00:00',
        'home_team': 'Valencia Club de Fútbol',
        'away_team': 'RCD Mallorca',
        'prediction': {},
        'actual_result': None
    }
    out_file = hist_dir / f'{league}_results.json'
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump([record], f, indent=2)

    # Fake API match using variant name
    def fake_safe_request_get(url, headers=None, params=None, timeout=15, retries=3, backoff=0.5, min_interval=None, session=None, logger=None):
        class FakeResp:
            status_code = 200
            def json(self):
                return {'matches': [{'utcDate': '2025-12-19T15:00:00Z', 'homeTeam': {'name': 'Valencia'}, 'awayTeam': {'name': 'RCD Mallorca'}, 'score': {'fullTime': {'homeTeam': 1, 'awayTeam': 1}}}]}
        return FakeResp()

    monkeypatch.setenv('FOOTBALL_DATA_API_KEY', 'fake')
    monkeypatch.setattr('app.utils.http.safe_request_get', fake_safe_request_get)

    updated = collector.fetch_and_update_from_api(league, days_lookback=30)
    assert updated == 1

    with open(out_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    assert data[0]['actual_result']['home_score'] == 1
    assert data[0]['actual_result']['away_score'] == 1
