from pathlib import Path

matches = list(Path("reports/leagues").glob("*/matches/*/prediction.json"))
print("matches count=", len(matches))
for m in matches:
    print(m)
