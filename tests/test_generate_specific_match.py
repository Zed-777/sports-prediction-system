import os
import shutil


class FakeResp:
    def __init__(self, json_data):
        self._json = json_data
        self.status_code = 200

    def raise_for_status(self):
        return None

    def json(self):
        return self._json


def test_generate_specific_scheduled_match(monkeypatch, tmp_path, capsys):
    # Ensure key is present
    monkeypatch.setenv("FOOTBALL_DATA_API_KEY", "fake-key")

    # Prepare fake scheduled match
    match_date = "2026-01-10T16:00:00Z"
    fake_matches = {
        "matches": [
            {
                "homeTeam": {"name": "Manchester City"},
                "awayTeam": {"name": "Chelsea"},
                "utcDate": match_date,
            },
        ],
    }

    def fake_safe_request_get(url, headers=None, params=None, timeout=None, logger=None, **kwargs):
        return FakeResp(fake_matches)

    # Monkeypatch the safe_request_get used by the modules (both the shared http util
    # and the local top-level binding inside generate_fast_reports) to avoid any
    # real network calls during the test.
    monkeypatch.setenv("FOOTBALL_DATA_API_KEY", "fake-key")
    monkeypatch.setattr("app.utils.http.safe_request_get", fake_safe_request_get)

    import generate_fast_reports as gfr
    # Patch generate_fast_reports module-level reference too
    monkeypatch.setattr(gfr, "safe_request_get", fake_safe_request_get)

    gen = gfr.SingleMatchGenerator()

    # Run generator for a specific match
    gen.generate_matches_report(10, "premier-league", home_team="Manchester City", away_team="Chelsea")

    captured = capsys.readouterr()
    assert "Processing: Manchester City vs Chelsea" in captured.out

    # Check the directory was created
    folder = os.path.join(
        "reports",
        "leagues",
        "premier-league",
        "matches",
        "manchester-city_vs_chelsea_2026-01-10",
    )
    assert os.path.isdir(folder)

    # Cleanup: remove only the specific match folder created by this test (avoid removing existing reports)
    match_dir = os.path.join(
        "reports",
        "leagues",
        "premier-league",
        "matches",
        "manchester-city_vs_chelsea_2026-01-10",
    )
    if os.path.isdir(match_dir):
        shutil.rmtree(match_dir)

