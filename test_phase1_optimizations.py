#!/usr/bin/env python3
"""
Phase 1 Optimization Verification Test
Tests all three Phase 1 optimizations
"""

import json
import sys
from pathlib import Path

# Add workspace to path
sys.path.insert(0, str(Path(__file__).parent))

def test_adaptive_weights():
    """Test 1: Adaptive Ensemble Weights"""
    print("\n" + "="*70)
    print("TEST 1: ADAPTIVE ENSEMBLE WEIGHTS (OPTIMIZATION #1)")
    print("="*70)
    
    try:
        from enhanced_predictor import EnhancedPredictor
        
        predictor = EnhancedPredictor(api_key='test')
        
        # Test context classification
        home_stats = {'strength': 80, 'form': 75}
        away_stats = {'strength': 60, 'form': 70}
        
        context = predictor._classify_match_context(home_stats, away_stats)
        print(f"✅ Context classification: {context}")
        
        # Test weight calculation
        weights = predictor._calculate_adaptive_weights(1.5, 1.2, context)
        print(f"✅ Adaptive weights calculated:")
        for model, weight in weights.items():
            print(f"   - {model}: {weight:.3f}")
        
        # Verify weights sum to 1.0
        weight_sum = sum(weights.values())
        assert abs(weight_sum - 1.0) < 0.001, f"Weights don't sum to 1.0: {weight_sum}"
        print(f"✅ Weights sum verification: {weight_sum:.4f} ≈ 1.0")
        
        print("✅ TEST 1 PASSED: Adaptive Ensemble Weights working correctly")
        return True
    except Exception as e:
        print(f"❌ TEST 1 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_data_freshness_scoring():
    """Test 2: Data Freshness Scoring"""
    print("\n" + "="*70)
    print("TEST 2: DATA FRESHNESS SCORING (OPTIMIZATION #2)")
    print("="*70)
    
    try:
        from enhanced_predictor import DataFreshnessScorer
        import time
        
        scorer = DataFreshnessScorer()
        
        # Test with fresh data
        fresh_data = {
            'team_stats_age_seconds': 300,      # 5 minutes
            'h2h_data_age_seconds': 600,        # 10 minutes
            'injury_data_age_seconds': 1200,    # 20 minutes
            'form_data_age_seconds': 1800,      # 30 minutes
            'weather_data_age_seconds': 600     # 10 minutes
        }
        
        score_fresh, mult_fresh = scorer.calculate_freshness_score(fresh_data)
        print(f"✅ Fresh data (5-30 min old):")
        print(f"   - Score: {score_fresh:.2f}")
        print(f"   - Multiplier: {mult_fresh:.3f}")
        assert mult_fresh >= 0.99, f"Fresh data should give ~1.0x multiplier, got {mult_fresh:.4f}"
        
        # Test with stale data
        stale_data = {
            'team_stats_age_seconds': 86400,    # 24 hours
            'h2h_data_age_seconds': 172800,     # 48 hours
            'injury_data_age_seconds': 86400,   # 24 hours
            'form_data_age_seconds': 86400,     # 24 hours
            'weather_data_age_seconds': 3600    # 1 hour
        }
        
        score_stale, mult_stale = scorer.calculate_freshness_score(stale_data)
        print(f"✅ Stale data (1-48 hours old):")
        print(f"   - Score: {score_stale:.2f}")
        print(f"   - Multiplier: {mult_stale:.3f}")
        assert 0.4 <= mult_stale < 1.0, "Stale data multiplier should be 0.4-1.0"
        assert mult_stale < mult_fresh, "Stale data should have lower multiplier"
        
        print("✅ TEST 2 PASSED: Data Freshness Scoring working correctly")
        return True
    except Exception as e:
        print(f"❌ TEST 2 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_advanced_features():
    """Test 3: Advanced Feature Engineering"""
    print("\n" + "="*70)
    print("TEST 3: ADVANCED FEATURE ENGINEERING (OPTIMIZATION #3)")
    print("="*70)
    
    try:
        from app.features.feature_engineering import AdvancedFeatures
        
        features = AdvancedFeatures()
        
        # Create test match data
        match_data = {
            'home_days_since_last_match': 3,
            'away_days_since_last_match': 1,
            'home_injured_players': [
                {'position': 'F', 'name': 'Striker1'},
                {'position': 'M', 'name': 'Midfielder1'}
            ],
            'away_injured_players': [],
            'referee_id': 'REF123',
            'home_set_piece_goals': 3,
            'home_total_goals': 12,
            'away_set_piece_goals': 1,
            'away_total_goals': 8,
            'home_shots': 15,
            'home_expected_goals': 1.5,
            'away_shots': 12,
            'away_expected_goals': 1.0,
            'weather_data': {
                'wind_speed_kmh': 15,
                'rain_intensity': 0.3
            },
            'opening_odds_home': 2.0,
            'current_odds_home': 1.95,
            'venue_id': 'VEN123',
            'home_team_id': 'TEAM123'
        }
        
        # Extract features
        feature_dict = features.extract_all_features(match_data)
        
        print(f"✅ Extracted {len(feature_dict)} features:")
        for fname, fvalue in sorted(feature_dict.items()):
            print(f"   - {fname}: {fvalue:.3f}")
        
        # Verify all features are in valid range [-1, 1]
        for fname, fvalue in feature_dict.items():
            assert -1.0 <= fvalue <= 1.0, f"{fname} out of range: {fvalue}"
        
        # Test specific features
        rest_diff = features.calculate_rest_differential(match_data)
        print(f"\n✅ Rest Differential (home +2 days): {rest_diff:.3f}")
        assert rest_diff > 0, "Home should have advantage (3 vs 1 day rest)"
        
        injury_impact = features.calculate_injury_impact(match_data)
        print(f"✅ Injury Impact (home missing F+M): {injury_impact:.3f}")
        assert injury_impact < 0, "Home should be disadvantaged"
        
        print("✅ TEST 3 PASSED: Advanced Feature Engineering working correctly")
        return True
    except Exception as e:
        print(f"❌ TEST 3 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("PHASE 1 OPTIMIZATION VERIFICATION SUITE")
    print("="*70)
    
    results = []
    
    # Run all tests
    results.append(("Adaptive Weights", test_adaptive_weights()))
    results.append(("Data Freshness", test_data_freshness_scoring()))
    results.append(("Advanced Features", test_advanced_features()))
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL PHASE 1 OPTIMIZATIONS VERIFIED SUCCESSFULLY!")
        return 0
    else:
        print("\n⚠️  Some tests failed - see above for details")
        return 1


if __name__ == '__main__':
    sys.exit(main())
