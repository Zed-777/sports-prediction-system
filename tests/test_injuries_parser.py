from pathlib import Path

from app.data.connectors.injuries import InjuriesConnector


def test_parse_injuries_from_team_fixture():
    connector = InjuriesConnector(cache_dir="tests/data")
    path = Path(__file__).parent / "data" / "flashscore_team_sevilla_sample.html"
    html = path.read_text(encoding="utf-8")
    parsed = connector._parse_injuries_from_team_html(html, "https://www.flashscore.es/team/sevilla-fc/")
    assert isinstance(parsed, list)
    assert len(parsed) >= 1
    first = parsed[0]
    assert "player" in first
    assert "reason" in first
    assert first.get("reason") is not None
    # expected return should be parsed from the fixture
    assert first.get("estimated_return") == "2026-02-01"