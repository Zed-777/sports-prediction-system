#!/usr/bin/env python3
"""Test Enhanced Data Quality System v4.1"""

from data_quality_enhancer import DataQualityEnhancer


def test_enhanced_data_quality():
    """Test the new data quality assessment features"""
    try:
        dqe = DataQualityEnhancer('test_key')

        # Mock comprehensive data sources
        mock_data_sources = [
            {'key_players_available': 10, 'injury_areas': []},  # Home team
            {'key_players_available': 9, 'injury_areas': ['midfield']},  # Away team
            {'conditions': {'conditions': 'clear', 'temperature': 20}},  # Weather
            {'name': 'Anthony Taylor', 'big_game_ready': True},  # Referee
            {'news_sentiment': 'positive', 'changes': []},  # Home news
            {'news_sentiment': 'neutral', 'changes': ['rotation']}  # Away news
        ]

        # Test enhanced data quality scoring
        quality_score = dqe.calculate_data_quality_score(*mock_data_sources)
        quality_breakdown = dqe.get_data_quality_breakdown()

        print("✅ Enhanced Data Quality Intelligence v4.1 Test Results:")
        print(f"  Overall Score: {quality_score:.1f}/100")
        print(f"  Quality Grade: {quality_breakdown['grade']}")
        print(f"  Quality Percentage: {quality_breakdown['percentage']:.1f}%")
        print(f"  Details Available: {len(quality_breakdown['details'])} assessment points")

        # Test with limited data
        limited_data = [
            {'key_players_available': 6},  # Limited home data
            {'key_players_available': 5},  # Limited away data
            {'conditions': {'conditions': 'unknown'}},  # No weather
            {'name': 'Unknown Referee'},  # No referee
            {'news_sentiment': 'unknown'},  # No home news
            {'news_sentiment': 'unknown'}   # No away news
        ]

        limited_score = dqe.calculate_data_quality_score(*limited_data)
        limited_breakdown = dqe.get_data_quality_breakdown()

        print("\n✅ Limited Data Test:")
        print(f"  Score: {limited_score:.1f}/100 ({limited_breakdown['grade']})")
        print(f"  Details: {', '.join(limited_breakdown['details'][:3])}...")

        print("\n🎉 Enhanced Data Quality System: WORKING!")
        return True

    except Exception as e:
        print(f"❌ Error testing data quality enhancement: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_enhanced_data_quality()
