from flashscore_scraper import FlashScoreScraper


def test_extract_json_payload_and_match():
    fs = FlashScoreScraper(debug_dir=None)
    payload = '''<script>window.__INITIAL_STATE__ = {"matches": [{"id": 12345, "homeTeam": {"name": "Team A"}, "awayTeam": {"name": "Team B"}, "utcDate": "2025-12-07T19:45:00Z", "score": {"fullTime": {"home": 2, "away": 1}}}]};</script>'''

    jsons = fs._extract_json_payloads(payload)
    assert len(jsons) >= 1
    matches = fs._find_matches_in_payload(jsons[0], 'premier-league')
    assert isinstance(matches, list)
    assert matches[0]['home_team'] == 'Team A'
    assert matches[0]['away_team'] == 'Team B'
    assert matches[0]['home_score'] == 2
    assert matches[0]['away_score'] == 1
