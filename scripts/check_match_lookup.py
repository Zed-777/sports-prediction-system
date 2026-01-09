import sys
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from generate_fast_reports import SingleMatchGenerator


def check(home, away, league, days):
    gen = SingleMatchGenerator()
    print(f"Searching for '{home}' vs '{away}' in {league} next {days} days")
    gen.generate_match_by_team_names(home, away, league, lookahead_days=days)


if __name__ == "__main__":
    check("Tottenham Hotspur", "Liverpool", "premier-league", 30)
    check("Tottenham", "Liverpool", "premier-league", 60)
    check("Tottenham", "Liverpool", "premier-league", 3)
    check("Tottenham Hotspur", "Liverpool", "premier-league", 1)
    check("Aston Villa", "Manchester United", "premier-league", 30)
    check("Aston Villa", "Manchester United", "premier-league", 7)
    check("Aston Villa", "Manchester United", "premier-league", 1)
