#!/usr/bin/env python3
"""
Test your Football-Data.org API key
"""


import requests

# Your API key
API_KEY = "17405508d1774f46a368390ff07f8a31"

def test_api():
    print("🔑 Testing your Football-Data.org API key...")
    print(f"Key: {API_KEY[:8]}...{API_KEY[-8:]}")

    headers = {'X-Auth-Token': API_KEY}
    url = "https://api.football-data.org/v4/competitions/PL/matches"

    try:
        print("📡 Making API request...")
        response = requests.get(url, headers=headers, timeout=10)

        print(f"📊 Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            matches = data.get('matches', [])
            print(f"✅ SUCCESS! Found {len(matches)} Premier League matches")

            if matches:
                match = matches[0]
                print(f"📅 Next match: {match['homeTeam']['name']} vs {match['awayTeam']['name']}")
                print(f"📍 Date: {match['utcDate'][:10]}")
                print(f"🏆 Status: {match['status']}")

            return True

        elif response.status_code == 403:
            print("❌ API key is invalid or expired")
            return False

        elif response.status_code == 429:
            print("⏰ Rate limited - too many requests")
            return False

        else:
            print(f"❌ API error: {response.status_code}")
            print(response.text[:200])
            return False

    except requests.exceptions.RequestException as e:
        print(f"🌐 Network error: {e}")
        return False

if __name__ == "__main__":
    success = test_api()
    if success:
        print("\n🎉 Your API key is working! The system can now fetch real match data.")
    else:
        print("\n⚠️  API key test failed. Check the key or try again later.")
