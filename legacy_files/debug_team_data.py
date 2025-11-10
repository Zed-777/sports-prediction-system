#!/usr/bin/env python3

import json

from enhanced_predictor import EnhancedPredictor


def debug_team_data():
    """Debug what team data we're actually getting"""
    api_key = "17405508d1774f46a368390ff07f8a31"
    predictor = EnhancedPredictor(api_key)

    # Test with Real Oviedo vs Espanyol (the match we're analyzing)
    print("🔍 Debugging Team Data Fetching...")
    print("=" * 50)

    # Get the match info to see team IDs
    # Get upcoming matches for La Liga (PD)
    candidates = (
        "fetch_upcoming_matches",
        "get_upcoming_matches",
        "get_matches",
        "fetch_matches",
    )
    match_fetcher = None
    for candidate in candidates:
        if hasattr(predictor, candidate):
            match_fetcher = getattr(predictor, candidate)
            break

    if match_fetcher is None:
        print("🔍 Checking available methods...")
        available_methods = [method for method in dir(predictor) if not method.startswith('_')]
        match_methods = [method for method in available_methods if 'match' in method.lower()]
        print(f"Available match-related methods: {match_methods}")
        print("❌ No match fetching method found!")
        matches = []
    else:
        matches = match_fetcher('PD')
    if matches:
        match = matches[0]  # First upcoming match
        home_team_id = match['homeTeam']['id']
        away_team_id = match['awayTeam']['id']

        print(f"🏠 Home Team: {match['homeTeam']['name']} (ID: {home_team_id})")
        print(f"✈️ Away Team: {match['awayTeam']['name']} (ID: {away_team_id})")
        print()

        # Fetch home team stats
        print(f"📊 Fetching {match['homeTeam']['name']} performance...")
        home_stats = predictor.fetch_team_home_away_stats(home_team_id, 'PD')
        print(f"Home Stats: {json.dumps(home_stats, indent=2)}")
        print()

        # Fetch away team stats
        print(f"📊 Fetching {match['awayTeam']['name']} performance...")
        away_stats = predictor.fetch_team_home_away_stats(away_team_id, 'PD')
        print(f"Away Stats: {json.dumps(away_stats, indent=2)}")
        print()

        # Check cache files
        print("📂 Cache Files:")
        print(f"   home_away_{home_team_id}_PD.json")
        print(f"   home_away_{away_team_id}_PD.json")

    else:
        print("❌ No upcoming matches found!")

if __name__ == "__main__":
    debug_team_data()
