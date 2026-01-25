#!/usr/bin/env python3
from pathlib import Path
import json, sys
sys.path.insert(0, '.')
from generate_fast_reports import SingleMatchGenerator

p = Path('reports/leagues/premier-league/matches/crystal-palace-football-club_vs_tottenham-hotspur-football-club_2025-12-28/prediction.json')
md = json.loads(p.read_text(encoding='utf-8'))

gen = SingleMatchGenerator()
print('Calling save_image into palace match folder...')
try:
    gen.save_image(md, str(p.parent))
    print('Done')
except Exception as e:
    print('save_image raised', e)
