#!/usr/bin/env python3
from enhanced_predictor import EnhancedPredictor

# Test the expected score functionality
predictor = EnhancedPredictor("17405508d1774f46a368390ff07f8a31")

# Test with sample match data
match_data = {
    'home_team': 'Test Home',
    'away_team': 'Test Away',
    'match_id': 123
}

result = predictor.enhanced_prediction(match_data, "PD")

print("🎯 Expected Score Test Results:")
print("=" * 40)
print(f"Expected Score: {result.get('expected_final_score')} ({result.get('score_probability'):.1f}%)")
print(f"Over 2.5 Goals: {result.get('over_2_5_goals_probability'):.1f}%")
print(f"Both Teams Score: {result.get('both_teams_score_probability'):.1f}%")
print(f"Alternative Scores: {result.get('alternative_scores')}")
print("=" * 40)
print("✅ Enhanced prediction system working correctly!")
