"""Pytest for FlashScore parser using cached HTML fixture.

This test is safe for CI: it will skip if the cached fixture is missing.
"""
import json
from pathlib import Path
try:
    import pytest
except Exception:  # pragma: no cover - allow editor environments without pytest
    class _PyTestStub:
        def skip(self, *args, **kwargs):
            return None

    pytest = _PyTestStub()

from flashscore_scraper import FlashScoreScraper


def test_flashscore_parser_fixture():
    cache_dir = Path("data/cache/flashscore")
    fixture = cache_dir / "page_2764.json"

    if not fixture.exists():
        pytest.skip(f"Fixture not found: {fixture}")

    data = json.loads(fixture.read_text(encoding='utf-8'))
    html = data.get('content') or data.get('html')
    if not html or '<html' not in html.lower():
        pytest.skip("Fixture does not contain valid HTML content")

    scraper = FlashScoreScraper()
    matches = scraper.parse_match_list(html, 'la-liga')
    assert matches, "Parser returned no matches from fixture"
