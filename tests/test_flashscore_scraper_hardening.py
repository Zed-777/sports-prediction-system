import gzip
import json
import zlib
from pathlib import Path

import pytest

from flashscore_scraper import FlashScoreScraper


def _load_fixture(path: Path) -> str:
    if not path.exists():
        pytest.skip("FlashScore fixture missing: {}".format(path))

    raw = path.read_text(encoding='utf-8', errors='ignore')
    try:
        obj = json.loads(raw)
        # older caches may wrap html under 'content'
        if isinstance(obj, dict) and 'content' in obj:
            return obj['content']
    except Exception:
        pass
    return raw


def test_parse_from_plain_fixture():
    path = Path('data/cache/flashscore/page_2764.json')
    html = _load_fixture(path)

    s = FlashScoreScraper()
    matches = s.parse_match_list(html, 'la-liga')

    assert isinstance(matches, list)
    assert len(matches) > 0, "Expected at least one match parsed from fixture"


def test_parse_from_compressed_variants():
    path = Path('data/cache/flashscore/page_2764.json')
    html = _load_fixture(path)

    s = FlashScoreScraper()

    # gzip
    gz = gzip.compress(html.encode('utf-8'))
    matches_gz = s.parse_match_list(gz, 'la-liga')
    assert isinstance(matches_gz, list)

    # zlib
    zl = zlib.compress(html.encode('utf-8'))
    matches_zl = s.parse_match_list(zl, 'la-liga')
    assert isinstance(matches_zl, list)

    # brotli if available
    try:
        import brotli as _brotli  # type: ignore
    except Exception:
        _brotli = None

    if _brotli is not None:
        br = _brotli.compress(html.encode('utf-8'))
        matches_br = s.parse_match_list(br, 'la-liga')
        assert isinstance(matches_br, list)
