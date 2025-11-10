#!/usr/bin/env python3
"""Test JSON serialization of market intelligence data"""

import json
import logging

import enhanced_predictor

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

# Create test match data
test_match = {
    'id': 12345,
    'homeTeam': {'id': 86, 'name': 'Real Madrid', 'shortName': 'RMA'},
    'awayTeam': {'id': 81, 'name': 'Barcelona', 'shortName': 'BAR'},
    'utcDate': '2024-12-30T20:00:00Z'
}

print("🧪 Testing JSON serialization of market intelligence data...")
print("=" * 60)

# Test the enhanced predictor
ep = enhanced_predictor.EnhancedPredictor('a8f3df9b70b14b6592b69fa04e38e9f4')
result = ep.enhanced_prediction(test_match, 'PD')

print("\n✅ Prediction completed successfully")
print(f"📊 Market Intelligence Active: {result.get('market_intelligence_active', False)}")
print(f"🏷️ Prediction Engine: {result.get('prediction_engine', 'Unknown')}")
print(f"📋 Has Betting Market Analysis: {'betting_market_analysis' in result}")

# Test JSON serialization
try:
    json_str = json.dumps(result, indent=2, ensure_ascii=False)
    print(f"\n✅ JSON serialization successful! ({len(json_str)} characters)")

    # Save to test file
    with open('test_market_intelligence_output.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print("💾 Test JSON file saved: test_market_intelligence_output.json")

    # Check if betting_market_analysis is in the serialized JSON
    if '"betting_market_analysis"' in json_str:
        print("✅ betting_market_analysis found in JSON output!")

        # Extract and display market intelligence section
        if 'betting_market_analysis' in result:
            market_data = result['betting_market_analysis']
            print("\n📊 Market Intelligence Summary:")
            print(f"   Active: {market_data.get('market_intelligence_active', False)}")
            if 'market_sentiment' in market_data:
                sentiment = market_data['market_sentiment']
                print(f"   Sentiment Type: {type(sentiment).__name__}")
                if isinstance(sentiment, dict):
                    print(f"   Sharp Money: {sentiment.get('sharp_money_pct', 'N/A')}%")
                    print(f"   Market Confidence: {sentiment.get('market_confidence', 'N/A')}")
                    print(f"   Value Opportunities: {len(sentiment.get('value_opportunities', []))}")
                else:
                    print(f"   Raw Sentiment: {sentiment}")
    else:
        print("❌ betting_market_analysis NOT found in JSON output")
        print(f"🔍 Available keys: {list(result.keys())}")

except Exception as e:
    print(f"❌ JSON serialization failed: {e}")
    print(f"🔍 Error type: {type(e).__name__}")

    # Try to identify the problematic data
    for key, value in result.items():
        try:
            json.dumps({key: value})
        except Exception as key_error:
            print(f"❌ Problem with key '{key}': {key_error}")
            print(f"   Value type: {type(value).__name__}")
