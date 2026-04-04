#!/usr/bin/env python3
import json
import sys
from pathlib import Path

sys.path.insert(0, ".")
from generate_fast_reports import SingleMatchGenerator

p = Path("reports/leagues/premier-league/matches/sunderland-afc_vs_leeds-united-football-club_2025-12-28/prediction.json")
md = json.loads(p.read_text(encoding="utf-8"))

gen = SingleMatchGenerator()
print("Calling save_image into actual match folder...")
gen.save_image(md, str(p.parent))
print("Done")
