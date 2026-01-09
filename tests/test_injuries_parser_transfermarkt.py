from pathlib import Path

from app.data.connectors.injuries import InjuriesConnector


def test_parse_transfermarkt_fixture():
    connector = InjuriesConnector(cache_dir="tests/data")
    path = Path(__file__).parent / "data" / "transfermarkt_team_sample.html"
    html = path.read_text(encoding="utf-8")
    parsed = connector._parse_transfermarkt_html(html, "https://www.transfermarkt.com/sevilla/verletzungen/")
    assert isinstance(parsed, list)
    assert len(parsed) >= 2
    first = parsed[0]
    assert first.get("estimated_return") == "2026-02-01"
    second = parsed[1]
    assert second.get("estimated_return") == "2026-03-01"