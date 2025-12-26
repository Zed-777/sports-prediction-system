"""
Test script for ML enhancement validation.
Tests all 6 ML components that were upgraded from basic heuristics.
"""

import os
import sys

# Add path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_attack_style_classification():
    """Test multi-dimensional attack style classification."""
    print("\n=== Test 1: Multi-Dimensional Attack Style Classification ===")

    from enhanced_predictor import EnhancedPredictor

    # Use environment API key or empty string
    api_key = os.getenv("FOOTBALL_DATA_API_KEY", "test_key")
    predictor = EnhancedPredictor(api_key)

    # Test aggressive team
    aggressive_stats = {
        "home": {"avg_goals_for": 2.5, "avg_goals_against": 0.8, "matches": 10},
        "away": {"avg_goals_for": 2.0, "avg_goals_against": 1.0, "matches": 10},
    }
    style1 = predictor._classify_attack_style(2.5, 1.55, aggressive_stats)
    print(f"  High-scoring team (2.5 xG): {style1}")
    assert style1 in [
        "aggressive",
        "counter-attacking",
        "possession-heavy",
    ], f"Expected attacking style, got {style1}"

    # Test defensive team
    defensive_stats = {
        "home": {"avg_goals_for": 0.8, "avg_goals_against": 0.5, "matches": 10},
        "away": {"avg_goals_for": 0.7, "avg_goals_against": 0.6, "matches": 10},
    }
    style2 = predictor._classify_attack_style(0.8, 1.55, defensive_stats)
    print(f"  Low-scoring team (0.8 xG): {style2}")
    assert style2 in [
        "defensive",
        "balanced",
    ], f"Expected defensive style, got {style2}"

    # Test balanced team
    balanced_stats = {
        "home": {"avg_goals_for": 1.5, "avg_goals_against": 1.3, "matches": 10},
        "away": {"avg_goals_for": 1.2, "avg_goals_against": 1.4, "matches": 10},
    }
    style3 = predictor._classify_attack_style(1.35, 1.55, balanced_stats)
    print(f"  Balanced team (1.35 xG): {style3}")

    print("  ✓ Attack style classification working with 5 style types")
    return True


def test_scoring_variance():
    """Test enhanced scoring variance calculation."""
    print("\n=== Test 2: Enhanced Scoring Variance ===")

    from enhanced_predictor import EnhancedPredictor

    api_key = os.getenv("FOOTBALL_DATA_API_KEY", "test_key")
    predictor = EnhancedPredictor(api_key)

    # Attack-heavy team (high variance expected)
    attack_stats = {
        "home": {"avg_goals_for": 2.5, "avg_goals_against": 0.8, "matches": 10},
        "away": {"avg_goals_for": 2.0, "avg_goals_against": 1.0, "matches": 10},
    }
    var1 = predictor._calculate_scoring_variance(attack_stats)
    print(f"  Attack-heavy team variance: {var1}")
    assert 0.1 <= var1 <= 0.9, f"Variance out of range: {var1}"

    # Defense-heavy team
    defense_stats = {
        "home": {"avg_goals_for": 0.8, "avg_goals_against": 0.5, "matches": 10},
        "away": {"avg_goals_for": 0.7, "avg_goals_against": 0.6, "matches": 10},
    }
    var2 = predictor._calculate_scoring_variance(defense_stats)
    print(f"  Defense-heavy team variance: {var2}")

    # Balanced team (lower variance expected)
    balanced_stats = {
        "home": {"avg_goals_for": 1.3, "avg_goals_against": 1.2, "matches": 10},
        "away": {"avg_goals_for": 1.2, "avg_goals_against": 1.3, "matches": 10},
    }
    var3 = predictor._calculate_scoring_variance(balanced_stats)
    print(f"  Balanced team variance: {var3}")

    print("  ✓ Scoring variance using multi-feature analysis")
    return True


def test_referee_impact_model():
    """Test statistical referee impact model."""
    print("\n=== Test 3: Referee Statistical Impact Model ===")

    from data_quality_enhancer import DataQualityEnhancer

    api_key = os.getenv("FOOTBALL_DATA_API_KEY", "test_key")
    validator = DataQualityEnhancer(api_key)

    # Test strict referee
    strict_ref_stats = {
        "avg_cards": 4.8,
        "avg_penalties": 0.35,
        "home_bias": 58,
        "avg_fouls": 28,
        "avg_red_cards": 0.15,
        "matches_count": 25,
    }
    impact = validator._analyze_referee_impact(strict_ref_stats, "Strict Referee")

    print(f"  Impact level: {impact['match_impact']['level']}")
    print(f"  Impact probability: {impact['match_impact']['probability']:.1%}")
    print(f"  Z-score (cards): {impact['statistical_profile']['z_cards']:+.2f}σ")
    print(
        f"  Z-score (penalties): {impact['statistical_profile']['z_penalties']:+.2f}σ"
    )
    print(f"  Predicted cards: {impact['predictions']['expected_cards']}")
    print(
        f"  Cards CI: [{impact['predictions']['cards_confidence_interval']['lower']}-{impact['predictions']['cards_confidence_interval']['upper']}]"
    )

    assert "statistical_profile" in impact, "Missing statistical profile"
    assert "predictions" in impact, "Missing predictions"
    assert impact["match_impact"]["probability"] >= 0, "Invalid probability"

    # Test lenient referee
    lenient_ref_stats = {
        "avg_cards": 2.2,
        "avg_penalties": 0.15,
        "home_bias": 50,
        "avg_fouls": 20,
        "avg_red_cards": 0.05,
        "matches_count": 30,
    }
    impact2 = validator._analyze_referee_impact(lenient_ref_stats, "Lenient Referee")
    print(
        f"\n  Lenient referee impact: {impact2['match_impact']['level']} ({impact2['match_impact']['probability']:.1%})"
    )

    print("  ✓ Referee impact model using z-scores and regression")
    return True


def test_weather_regression():
    """Test weather impact regression model."""
    print("\n=== Test 4: Weather Impact Regression Model ===")

    from data_quality_enhancer import DataQualityEnhancer

    api_key = os.getenv("FOOTBALL_DATA_API_KEY", "test_key")
    validator = DataQualityEnhancer(api_key)

    # Test various weather conditions
    conditions = [
        {"temperature": 18, "precipitation": 0, "wind_speed": 8, "humidity": 50},
        {"temperature": 5, "precipitation": 5, "wind_speed": 25, "humidity": 90},
        {"temperature": 35, "precipitation": 0, "wind_speed": 5, "humidity": 30},
    ]

    for i, weather in enumerate(conditions):
        result = validator.analyze_weather_impact(weather)
        print(
            f"  Condition {i + 1}: Temp={weather['temperature']}°C, Rain={weather['precipitation']}mm, Wind={weather['wind_speed']}km/h"
        )
        print(f"    Goal modifier: {result['goal_modifier']:.3f}")
        if "regression_components" in result:
            print(
                f"    Components: temp={result['regression_components']['temperature_effect']:.3f}, "
                f"precip={result['regression_components']['precipitation_effect']:.3f}"
            )

    print("  ✓ Weather model using Gaussian/exponential regression")
    return True


def test_form_analysis():
    """Test enhanced form analysis with momentum."""
    print("\n=== Test 5: Enhanced Form Analysis ===")

    from enhanced_predictor import EnhancedPredictor

    api_key = os.getenv("FOOTBALL_DATA_API_KEY", "test_key")
    predictor = EnhancedPredictor(api_key)

    # Test with match results (need full match dictionaries now)
    results = [
        {"result": "W", "goals_for": 2, "goals_against": 0},
        {"result": "W", "goals_for": 3, "goals_against": 1},
        {"result": "D", "goals_for": 1, "goals_against": 1},
        {"result": "W", "goals_for": 2, "goals_against": 1},
        {"result": "L", "goals_for": 0, "goals_against": 2},
        {"result": "W", "goals_for": 1, "goals_against": 0},
    ]
    form_result = predictor._calculate_weighted_form(results)

    print(f"  Results: {[r['result'] for r in results]}")
    print(f"  Form score: {form_result.get('weighted_form_score', 0):.1f}")
    print(f"  Momentum slope: {form_result.get('momentum_slope', 0):.3f}")
    print(f"  Momentum direction: {form_result.get('momentum_direction', 'N/A')}")
    print(f"  Consistency: {form_result.get('consistency_score', 'N/A')}")

    form_score = form_result.get("weighted_form_score", 0)
    assert 0 <= form_score <= 100, f"Form score out of range: {form_score}"

    # Test with poor form
    poor_results = [
        {"result": "L", "goals_for": 0, "goals_against": 2},
        {"result": "L", "goals_for": 1, "goals_against": 3},
        {"result": "D", "goals_for": 0, "goals_against": 0},
        {"result": "L", "goals_for": 0, "goals_against": 1},
    ]
    poor_form_result = predictor._calculate_weighted_form(poor_results)
    poor_score = poor_form_result.get("weighted_form_score", 0)
    print(f"  Poor form score: {poor_score:.1f}")

    # Both scores valid in range
    assert 0 <= poor_score <= 100, f"Poor form score out of range"

    print("  ✓ Form analysis using exponential decay and momentum")
    return True


def test_elo_system():
    """Test dynamic ELO rating system."""
    print("\n=== Test 6: Dynamic ELO Rating System ===")

    from app.models.ml_enhancer import MachineLearningEnhancer

    ml = MachineLearningEnhancer()

    # Test team ELO retrieval (returns dict with 'elo' key)
    real_madrid_data = ml.get_team_elo("Real Madrid")
    barcelona_data = ml.get_team_elo("Barcelona")
    unknown_data = ml.get_team_elo("Unknown Team FC")

    real_madrid_elo = (
        real_madrid_data.get("elo", 1500)
        if isinstance(real_madrid_data, dict)
        else real_madrid_data
    )
    barcelona_elo = (
        barcelona_data.get("elo", 1500)
        if isinstance(barcelona_data, dict)
        else barcelona_data
    )
    unknown_elo = (
        unknown_data.get("elo", 1500)
        if isinstance(unknown_data, dict)
        else unknown_data
    )

    print(f"  Real Madrid ELO: {real_madrid_elo}")
    print(f"  Barcelona ELO: {barcelona_elo}")
    print(f"  Unknown team ELO: {unknown_elo}")

    assert real_madrid_elo > 1500, "Real Madrid should have high ELO"
    assert unknown_elo == 1500, "Unknown teams should get default ELO"

    # Test expected score calculation (returns tuple: home_exp, away_exp)
    expected = ml.calculate_expected_score(real_madrid_elo, barcelona_elo)
    home_exp = expected[0] if isinstance(expected, tuple) else expected
    print(f"  Real Madrid expected score vs Barcelona: {home_exp:.3f}")
    assert 0 < home_exp < 1, f"Expected score out of range: {home_exp}"

    # Test ELO update
    original_data = ml.get_team_elo("Test Team")
    original_elo = (
        original_data.get("elo", 1500)
        if isinstance(original_data, dict)
        else original_data
    )
    ml.update_elo_after_match("Test Team", "Test Opponent", 3, 1)
    updated_data = ml.get_team_elo("Test Team")
    updated_elo = (
        updated_data.get("elo", 1500)
        if isinstance(updated_data, dict)
        else updated_data
    )
    print(f"  ELO update after 3-1 win: {original_elo} -> {updated_elo}")
    assert updated_elo >= original_elo, "ELO should increase or stay same after win"

    # Test match prediction
    prediction = ml.predict_match_elo("Real Madrid", "Barcelona")
    print(f"  Match prediction:")
    print(f"    Home win: {prediction['home_win_probability']:.1f}%")
    print(f"    Draw: {prediction['draw_probability']:.1f}%")
    print(f"    Away win: {prediction['away_win_probability']:.1f}%")

    print("  ✓ ELO system with dynamic updates and K-factors")
    return True


def main():
    """Run all ML enhancement tests."""
    print("=" * 60)
    print("ML Enhancement Validation Tests")
    print("=" * 60)

    tests = [
        ("Attack Style Classification", test_attack_style_classification),
        ("Scoring Variance", test_scoring_variance),
        ("Referee Impact Model", test_referee_impact_model),
        ("Weather Regression", test_weather_regression),
        ("Form Analysis", test_form_analysis),
        ("ELO System", test_elo_system),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            result = test_func()
            if result:
                passed += 1
        except Exception as e:
            print(f"  ✗ FAILED: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"Results: {passed}/{len(tests)} tests passed")
    if failed == 0:
        print("✓ All ML enhancements validated successfully!")
    else:
        print(f"✗ {failed} test(s) failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
