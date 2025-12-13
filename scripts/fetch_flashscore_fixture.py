import json
import sys
from pathlib import Path

# Ensure project root on path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from flashscore_scraper import FlashScoreScraper

CACHE_DIR = Path('data/cache/flashscore')
CACHE_DIR.mkdir(parents=True, exist_ok=True)

scraper = FlashScoreScraper()
url = 'https://www.flashscore.es/futbol/espana/primera-division/'
print('Fetching', url)
html = scraper.get_page(url, use_cache=False)
if not html:
    print('Failed to fetch live HTML from FlashScore')
    sys.exit(1)

path = CACHE_DIR / 'page_2764.json'
with open(path, 'w', encoding='utf-8') as f:
    json.dump({'url': url, 'content': html, 'timestamp': None}, f, ensure_ascii=False)

print('WROTE', path)
