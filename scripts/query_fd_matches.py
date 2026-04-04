import os

import requests

key = os.getenv("FOOTBALL_DATA_API_KEY")
headers = {"X-Auth-Token": key}
url = "https://api.football-data.org/v4/competitions/PL/matches"
params = {"dateFrom": "2025-12-18", "dateTo": "2025-12-21", "limit": 200}
print("Calling", url, params)
r = requests.get(url, headers=headers, params=params, timeout=30)
print("Status", r.status_code)
if r.ok:
    data = r.json()
    matches = data.get("matches", [])
    for m in matches:
        h = m.get("homeTeam", {}).get("name", "")
        a = m.get("awayTeam", {}).get("name", "")
        print(m.get("utcDate", ""), h, "vs", a, "status", m.get("status"))
else:
    print("Error:", r.text)
