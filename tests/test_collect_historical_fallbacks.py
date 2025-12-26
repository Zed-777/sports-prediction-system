import json
from pathlib import Path
from scripts.collect_historical_results import HistoricalResultsCollector


class FakeResp:
    def __init__(self, json_data, status_code=200):
        self._json = json_data
        self.status_code = status_code

    def json(self):
        return self._json


def test_fd_no_scores_uses_api_football_fallback(monkeypatch, tmp_path):
    proj_root = Path(__file__).resolve().parents[1]
    hist_dir = proj_root / "data" / "historical"
    hist_dir.mkdir(parents=True, exist_ok=True)
    league = "la-liga"
    record = {
        "match_id": "team-x_vs_team-y_2025-12-20",
        "league": league,
        "home_team": "Team X",
        "away_team": "Team Y",
        "match_date": "2025-12-20T15:00:00+00:00",
        "prediction": {"home_win_prob": 0.5, "draw_prob": 0.3, "away_win_prob": 0.2},
        "actual_result": None,
    }
    out_file = hist_dir / f"{league}_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump([record], f, indent=2)

    # Football-Data returns a match but with no final scores
    fd_match = {
        "id": 1111,
        "utcDate": "2025-12-20T15:00:00Z",
        "homeTeam": {"name": "Team X"},
        "awayTeam": {"name": "Team Y"},
        "score": {"fullTime": {"homeTeam": None, "awayTeam": None}},
    }

    # API-Football fallback payload
    af_payload = {
        "response": [
            {
                "teams": {"home": {"name": "Team X"}, "away": {"name": "Team Y"}},
                "score": {"fulltime": {"home": 2, "away": 1}},
                "fixture": {"id": 9999},
            }
        ]
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
        # Football-Data URL
        if "api.football-data.org" in url:
            return FakeResp({"matches": [fd_match]}, status_code=200)
        # API-Football URL
        if "v3.football.api-sports.io" in url:
            return FakeResp(af_payload, status_code=200)
        return FakeResp({}, status_code=404)

    monkeypatch.setenv("FOOTBALL_DATA_API_KEY", "fake-key")
    monkeypatch.setenv("API_FOOTBALL_KEY", "fake-key")
    monkeypatch.setattr("app.utils.http.safe_request_get", fake_safe_request_get)

    collector = HistoricalResultsCollector()
    updated = collector.fetch_and_update_from_api(league, days_lookback=30, debug=True)

    # Should have used fallback and updated the historical record
    assert updated == 1
    with open(out_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data[0]["actual_result"]["home_score"] == 2
    assert data[0]["actual_result"]["away_score"] == 1
    assert data[0]["prediction_correct"] in (True, False)
