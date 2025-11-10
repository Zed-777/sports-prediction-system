#!/usr/bin/env python3
"""Test Market Intelligence with real data"""

import logging

import requests

import enhanced_predictor

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

# API setup
headers = {'X-Auth-Token': 'a8f3df9b70b14b6592b69fa04e38e9f4'}

# Check for upcoming matches
leagues = [
    ('Premier League', 'PL'),
    ('Ligue 1', 'FL1'),
    ('Bundesliga', 'BL1'),
    ('Serie A', 'SA'),
    ('Championship', 'ELC'),
    ('La Liga', 'PD')
]

print('🔍 Checking for upcoming matches...')
test_match = None
test_league = None

for name, code in leagues:
    url = f'https://api.football-data.org/v4/competitions/{code}/matches'
    params = {'status': 'SCHEDULED', 'limit': 1}

    try:
        response = requests.get(url, headers=headers, params=params)
        matches = response.json().get('matches', [])
        print(f'{name}: {len(matches)} upcoming matches')

        if matches and not test_match:
            test_match = matches[0]
            test_league = code
            print(f'✅ Using {name} match for testing')
            break

    except Exception as e:
        print(f'{name}: Error - {e}')

if not test_match:
    print("❌ No upcoming matches found. Creating synthetic match for testing...")
    test_match = {
        'id': 12345,
        'homeTeam': {'id': 86, 'name': 'Real Madrid', 'shortName': 'RMA'},
        'awayTeam': {'id': 81, 'name': 'Barcelona', 'shortName': 'BAR'},
        'utcDate': '2024-12-30T20:00:00Z'
    }
    test_league = 'PD'

print(f"\n🧪 Testing Market Intelligence with match: {test_match['homeTeam']['name']} vs {test_match['awayTeam']['name']}")
print("=" * 60)

# Test the enhanced predictor
ep = enhanced_predictor.EnhancedPredictor('a8f3df9b70b14b6592b69fa04e38e9f4')
result = ep.enhanced_prediction(test_match, test_league)

print('\n=== RESULT SUMMARY ===')
print(f'Market Intelligence Active: {result.get("market_intelligence_active", False)}')
print(f'Prediction Engine: {result.get("prediction_engine", "Unknown")}')
print(f'Has Betting Market Analysis: {"betting_market_analysis" in result}')
print(f'Result Keys: {list(result.keys())}')

if 'betting_market_analysis' in result:
    market_data = result['betting_market_analysis']
    print('\n💰 Market Intelligence Data Found:')
    print(f'   Accuracy Boost: {market_data.get("accuracy_boost", "N/A")}')
    print(f'   Sharp Money: {market_data.get("sharp_money_detected", "N/A")}')
    print(f'   Market Sentiment: {market_data.get("market_sentiment", "N/A")}')
else:
    print('\n❌ Market Intelligence Data NOT Found in result')
    print('   This is the core issue we need to fix!')
