from pathlib import Path
import sys
import os

# Ensure repo root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from flashscore_scraper import FlashScoreScraper
import json

p = Path("data/cache/flashscore/page_2764.json")
text = json.loads(p.read_text(encoding="utf-8")).get("content")
print("Text:", text)
s = FlashScoreScraper()
script_contents = s._extract_encoded_blocks(text)
print("Blocks found:", script_contents)

# Additional debug: run key/value regex directly against the text and print matches
import re

matches = re.findall(r"([A-Z]{1,3})÷([^¬]*)", text)
print("Direct re.findall matches:", matches)
