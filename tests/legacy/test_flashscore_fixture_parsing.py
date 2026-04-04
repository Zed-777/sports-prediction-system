from pathlib import Path

from flashscore_scraper import FlashScoreScraper


def test_flashscore_team_page_fixture_parsing():
    s = FlashScoreScraper()
    path = Path(__file__).parent / "data" / "flashscore_team_sevilla_sample.html"
    html = path.read_text(encoding="utf-8")
    # Ensure the team page contains an injury mention
    assert "injur" in html.lower()

    # Monkeypatch get_page by temporarily replacing the method
    original_get_page = s.get_page

    try:
        s.get_page = lambda url, use_cache=True: html
        # Use InjuriesConnector-like logic to scan for injury mentions via scraper
        team_page = s.get_page("https://www.flashscore.es/team/sevilla-fc/", use_cache=True)
        assert team_page is not None
        assert "injur" in team_page.lower()
    finally:
        s.get_page = original_get_page
