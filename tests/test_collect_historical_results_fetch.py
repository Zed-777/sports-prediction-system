import json
from pathlib import Path
from scripts.collect_historical_results import HistoricalResultsCollector


def fake_fd_response(matches):
    return {"matches": matches}


class FakeResp:
    def __init__(self, json_data, status_code=200):
        self._json = json_data
        self.status_code = status_code

    def json(self):
        return self._json


def test_fetch_and_update_from_api(monkeypatch, tmp_path):
    # Create a small historical file
    proj_root = Path(__file__).resolve().parents[1]
    hist_dir = proj_root / "data" / "historical"
    hist_dir.mkdir(parents=True, exist_ok=True)
    league = "la-liga"
    record = {
        "match_id": "team-a_vs_team-b_2025-12-20",
        "league": league,
        "home_team": "Team A",
        "away_team": "Team B",
        "match_date": "2025-12-20T15:00:00+00:00",
        "prediction": {"home_win_prob": 0.6, "draw_prob": 0.2, "away_win_prob": 0.2},
        "actual_result": None,
    }
    out_file = hist_dir / f"{league}_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump([record], f, indent=2)

    # Fake API response
    match_data = {
        "id": 12345,
        "utcDate": "2025-12-20T15:00:00Z",
        "homeTeam": {"name": "Team A"},
        "awayTeam": {"name": "Team B"},
        "score": {"fullTime": {"homeTeam": 2, "awayTeam": 1}},
    }

    def fake_safe_request_get(
        url,
        headers=None,
        params=None,
        timeout=15,
        retries=3,
        backoff=0.5,
        min_interval=None,
        session=None,
        logger=None,
    ):
        return FakeResp(fake_fd_response([match_data]), status_code=200)

    monkeypatch.setenv("FOOTBALL_DATA_API_KEY", "fake-key")
    # Patch the http helper used inside the collector
    monkeypatch.setattr("app.utils.http.safe_request_get", fake_safe_request_get)

    collector = HistoricalResultsCollector()
    updated = collector.fetch_and_update_from_api(league, days_lookback=30)
    assert updated == 1

    # Verify file updated
    with open(out_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data[0]["actual_result"]["home_score"] == 2
    assert data[0]["actual_result"]["away_score"] == 1
    assert data[0]["prediction_correct"] is True
