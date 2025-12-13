"""Quick test for FlashScore parser using cached HTML fixture.
This is not a full pytest file — it's a small runner to validate parsing locally.
"""
import json
import sys
from pathlib import Path

# Ensure project root is on sys.path for direct imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from flashscore_scraper import FlashScoreScraper

CACHE_DIR = Path("data/cache/flashscore")
# choose a page fixture that exists
fixture = CACHE_DIR / "page_2764.json"

if not fixture.exists():
    print(f"Fixture not found: {fixture}")
    raise SystemExit(1)

data = json.loads(fixture.read_text(encoding='utf-8'))
html = data.get('content') or data.get('html')
if not html:
    print('No HTML content found in fixture')
    raise SystemExit(1)

scraper = FlashScoreScraper()
# If the fixture content doesn't look like HTML (some cached fixtures may be corrupted),
# attempt a live fetch and update the fixture so tests remain deterministic.
if '<html' not in (html or '').lower():
    print('Fixture content does not look like HTML — attempting live fetch to refresh fixture')
    live_html = scraper.get_page('https://www.flashscore.es/futbol/espana/primera-division/', use_cache=False)
    if live_html:
        # overwrite fixture with fresh HTML
        data['content'] = live_html
        fixture.write_text(json.dumps({'url': 'https://www.flashscore.es/futbol/espana/primera-division/', 'content': live_html, 'timestamp': None}, ensure_ascii=False), encoding='utf-8')
        html = live_html

matches = scraper.parse_match_list(html, 'la-liga')
print(f'Parsed {len(matches)} matches from fixture {fixture.name}')
for i, m in enumerate(matches[:5], start=1):
    print(f"{i}. {m.get('home_team')} vs {m.get('away_team')} — {m.get('date')} {m.get('time')} ({m.get('status')})")

if len(matches) == 0:
    print('ERROR: Parser returned 0 matches; needs further tuning')
    raise SystemExit(2)

print('SUCCESS: parser extracted matches')
