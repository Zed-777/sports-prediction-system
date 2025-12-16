"""Test Phase 4 Advanced Predictions Integration."""

from enhanced_predictor import EnhancedPredictor


def test_phase4_integration():
    """Test that Phase 4 advanced predictions are integrated and working."""
    # Initialize predictor with dummy API key
    predictor = EnhancedPredictor(api_key='test_key')
    print('=== Phase 4 Integration Test ===')
    print()

    # Check Phase 4 module loaded
    if predictor.advanced_predictions is not None:
        print('✅ Phase 4 Advanced Predictions: LOADED')
    else:
        print('❌ Phase 4 Advanced Predictions: NOT LOADED')
        return

    # Test prediction with all phases - using expected match format
    match = {
        'homeTeam': {'id': 65, 'name': 'Manchester City'},
        'awayTeam': {'id': 64, 'name': 'Liverpool'},
        'utcDate': '2025-01-19T16:30:00Z',
        'competition': {'name': 'Premier League', 'code': 'PL'},
        'venue': 'Etihad Stadium'
    }

    result = predictor.enhanced_prediction(match, competition_code='PL')

    print()
    print('=== Prediction Result ===')
    print(f"Home Win: {result.get('home_win_prob', 0):.1%}")
    print(f"Draw: {result.get('draw_prob', 0):.1%}")
    print(f"Away Win: {result.get('away_win_prob', 0):.1%}")
    print(f"Confidence: {result.get('confidence', 0):.1%}")
    print()

    # Check Phase 4 outputs
    if result.get('phase4_enhanced'):
        print('✅ Phase 4 Enhanced: TRUE')
        
        if 'btts' in result:
            btts = result['btts']
            print(f"   BTTS: {btts.get('prediction')} (Yes: {btts.get('yes_prob', 0):.1%}, No: {btts.get('no_prob', 0):.1%})")
        
        if 'over_under' in result:
            ou = result['over_under']
            if 'lines' in ou:
                line25 = ou['lines'].get('2.5', {})
                print(f"   O/U 2.5: {line25.get('prediction')} (Over: {line25.get('over_prob', 0):.1%}, Under: {line25.get('under_prob', 0):.1%})")
        
        if 'exact_scores' in result:
            scores = result['exact_scores']
            if 'top_scores' in scores:
                top = scores['top_scores'][:3]
                top_str = ', '.join([f"{s['score']}: {s['prob']:.1%}" for s in top])
                print(f"   Top Scores: {top_str}")
        
        if 'two_stage_score' in result:
            print(f"   Two-Stage Score: {result['two_stage_score']}")
    else:
        print('❌ Phase 4 Enhanced: FALSE')

    # Show all enhancement phases
    print()
    print('=== Enhancement Phases Active ===')
    print(f"Phase 1: {result.get('phase1_enhanced', False)}")
    print(f"Phase 2: {result.get('phase2_enhanced', False)}") 
    print(f"Phase 3: {result.get('phase3_enhanced', False)}")
    print(f"Phase 4: {result.get('phase4_enhanced', False)}")
    
    # Assertions for pytest
    assert predictor.advanced_predictions is not None, "Phase 4 module should be loaded"
    assert result.get('phase4_enhanced') == True, "Phase 4 should be active"
    assert 'btts' in result, "BTTS prediction should be present"
    assert 'over_under' in result, "Over/Under prediction should be present"
    assert 'exact_scores' in result, "Exact scores should be present"
    
    print()
    print('✅ All Phase 4 integration tests passed!')


if __name__ == '__main__':
    test_phase4_integration()
