import sys
from pathlib import Path

# Ensure repository root is on sys.path so top-level modules can be imported
ROOT = Path(__file__).parent.parent.resolve()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from generate_fast_reports import SingleMatchGenerator

if __name__ == "__main__":
    gen = SingleMatchGenerator()
    gen.generate_matches_report(50, "premier-league", home_team="Manchester City", away_team="Chelsea")
