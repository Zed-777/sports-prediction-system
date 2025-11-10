#!/usr/bin/env python3
"""Test Enhanced Referee Intelligence System"""

from data_quality_enhancer import DataQualityEnhancer


def test_enhanced_referee():
    """Test the new referee intelligence features"""
    try:
        dqe = DataQualityEnhancer('test_key')

        # Test with known referee
        referee_analysis = dqe.get_referee_analysis('Anthony Taylor')

        print("✅ Enhanced Referee Intelligence v4.1 Test Results:")
        print(f"  Referee: {referee_analysis['name']}")
        print(f"  Match Control Style: {referee_analysis.get('match_control_style', 'N/A')}")
        print(f"  VAR Tendency: {referee_analysis.get('var_tendency', 'N/A')}")
        print(f"  Big Game Ready: {referee_analysis.get('big_game_ready', 'N/A')}")
        print(f"  Crowd Resistance: {referee_analysis.get('crowd_resistance', 'N/A')}%")
        print(f"  Key Tendencies: {len(referee_analysis.get('key_tendencies', []))} patterns identified")

        # Test with unknown referee
        unknown_referee = dqe.get_referee_analysis('Test Referee')
        print("\n✅ Unknown Referee Profile Generated:")
        print(f"  Home Bias: {unknown_referee['home_bias_pct']}%")
        print(f"  Control Style: {unknown_referee.get('match_control_style', 'standard')}")

        print("\n🎉 Enhanced Referee Intelligence System: WORKING!")
        return True

    except Exception as e:
        print(f"❌ Error testing referee enhancement: {e}")
        return False

if __name__ == "__main__":
    test_enhanced_referee()
