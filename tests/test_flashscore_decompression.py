try:
    import brotli
except Exception:
    brotli = None

from flashscore_scraper import FlashScoreScraper


def test_decompression_heuristic_runs_without_error():
    if brotli is None:
        # Environment may not have brotli installed; skip gracefully
        return
    # Create a fake compressed payload (brotli of a simple html snippet)
    raw_html = '<html><body><script>var data = "";</script></body></html>'
    compressed = brotli.compress(raw_html.encode('utf-8'))
    # Construct a latin-1 string representation similar to what we observed
    payload = compressed.decode('latin-1', errors='ignore')

    fs = FlashScoreScraper(debug_dir=None)
    # Should not raise and should return a list (possibly empty)
    matches = fs.parse_match_list(payload, 'premier-league')
    assert isinstance(matches, list)
