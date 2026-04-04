from flashscore_scraper import FlashScoreScraper


class DummyResponse:
    def __init__(self, text, status_code=200):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


def test_get_page_saves_debug_file_on_suspicious_html(monkeypatch, tmp_path):
    debug_dir = str(tmp_path / "debug")
    fs = FlashScoreScraper(debug_dir=debug_dir, max_attempts=1)

    # Simulate a short/invalid HTML response
    def fake_get(url, timeout=30):
        return DummyResponse("<not-html />")

    monkeypatch.setattr(fs.session, "get", fake_get)

    result = fs.get_page("https://example.com/leagues/test", use_cache=False)

    # Result should be None due to invalid HTML
    assert result is None

    # A debug HTML file should have been written into debug_dir
    files = list((tmp_path / "debug").glob("*.html"))
    assert len(files) >= 1

    # content should contain the string we returned
    content = files[0].read_text(encoding="utf-8")
    assert "<not-html" in content
