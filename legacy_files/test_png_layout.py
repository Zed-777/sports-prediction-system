#!/usr/bin/env python3
"""Test PNG generation with enhanced horizontal layout"""

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

# Test data
test_data = {
    'home_team': 'Real Madrid',
    'away_team': 'Barcelona',
    'league': 'La Liga',
    'date': '2025-10-17',
    'time': '20:00',
    'expected_final_score': '2-1',
    'home_win_probability': 45.5,
    'draw_probability': 28.3,
    'away_win_probability': 26.2,
    'expected_home_goals': 1.8,
    'expected_away_goals': 1.2,
    'over_2_5_goals_probability': 58.3,
    'both_teams_score_probability': 65.2,
    'report_accuracy_probability': 0.72,
    'data_quality_score': 88,
    'processing_time': 1.25,
    'recommendation': 'Home Edge Expected',
    'alternative_scores': ['1-0', '2-0', '1-1']
}

def test_horizontal_png():
    """Generate test horizontal PNG with gauges"""

    # Create horizontal layout (18x10)
    fig, ax = plt.subplots(figsize=(18, 10))
    ax.set_xlim(0, 18)
    ax.set_ylim(0, 10)
    ax.axis('off')
    fig.patch.set_facecolor('#f8f9fa')

    # Main card background
    main_bg = Rectangle((0.5, 0.5), 17, 9, facecolor='#ffffff',
                       edgecolor='#1a252f', linewidth=3, alpha=1.0)
    ax.add_patch(main_bg)

    # Header section
    header_bg = Rectangle((0.7, 8.0), 16.6, 1.3, facecolor='#1a252f', alpha=1.0)
    ax.add_patch(header_bg)

    # Title
    ax.text(9, 8.7, f"{test_data['home_team']} vs {test_data['away_team']}",
            ha='center', va='center', fontsize=22, fontweight='bold', color='white')

    # League info
    ax.text(9, 8.3, f"{test_data['league']} • {test_data['date']} at {test_data['time']}",
            ha='center', va='center', fontsize=14, color='#ecf0f1')

    # Enhanced Intelligence badge
    badge_bg = Rectangle((7.5, 7.6), 3.0, 0.3, facecolor='#e74c3c', alpha=1.0)
    ax.add_patch(badge_bg)
    ax.text(9, 7.75, "ENHANCED INTELLIGENCE v4.0",
            ha='center', va='center', fontsize=11, fontweight='bold', color='white')

    # Win probabilities section
    ax.text(4.5, 7.2, "WIN PROBABILITIES", ha='center', va='center',
            fontsize=16, fontweight='bold', color='#1a252f')

    # Simple probability displays (without complex gauges for now)
    ax.text(2.5, 6.0, "HOME WIN", ha='center', va='center',
            fontsize=12, fontweight='bold', color='#27ae60')
    ax.text(2.5, 5.6, f"{test_data['home_win_probability']:.1f}%", ha='center', va='center',
            fontsize=20, fontweight='bold', color='#27ae60')

    ax.text(4.5, 6.0, "DRAW", ha='center', va='center',
            fontsize=12, fontweight='bold', color='#95a5a6')
    ax.text(4.5, 5.6, f"{test_data['draw_probability']:.1f}%", ha='center', va='center',
            fontsize=20, fontweight='bold', color='#95a5a6')

    ax.text(6.5, 6.0, "AWAY WIN", ha='center', va='center',
            fontsize=12, fontweight='bold', color='#e74c3c')
    ax.text(6.5, 5.6, f"{test_data['away_win_probability']:.1f}%", ha='center', va='center',
            fontsize=20, fontweight='bold', color='#e74c3c')

    # Center prediction
    pred_bg = Rectangle((8.5, 4.5), 4, 2.5, facecolor='#f39c12', alpha=0.1,
                       edgecolor='#f39c12', linewidth=2)
    ax.add_patch(pred_bg)

    ax.text(10.5, 6.5, "PREDICTED SCORE", ha='center', va='center',
            fontsize=14, fontweight='bold', color='#1a252f')
    ax.text(10.5, 6.0, test_data['expected_final_score'], ha='center', va='center',
            fontsize=28, fontweight='bold', color='#f39c12')
    ax.text(10.5, 5.5, f"Expected Goals: {test_data['expected_home_goals']:.1f} - {test_data['expected_away_goals']:.1f}",
            ha='center', va='center', fontsize=12, color='#1a252f')

    # Right side analysis
    ax.text(14.5, 7.2, "ANALYSIS QUALITY", ha='center', va='center',
            fontsize=16, fontweight='bold', color='#1a252f')

    # Simple quality displays
    ax.text(13.5, 6.0, "CONFIDENCE", ha='center', va='center',
            fontsize=12, fontweight='bold', color='#8e44ad')
    ax.text(13.5, 5.6, f"{test_data['report_accuracy_probability']*100:.1f}%", ha='center', va='center',
            fontsize=18, fontweight='bold', color='#8e44ad')

    ax.text(15.5, 6.0, "DATA QUALITY", ha='center', va='center',
            fontsize=12, fontweight='bold', color='#2980b9')
    ax.text(15.5, 5.6, f"{test_data['data_quality_score']:.0f}%", ha='center', va='center',
            fontsize=18, fontweight='bold', color='#2980b9')

    # Bottom markets
    market_bg = Rectangle((1.0, 2.5), 16, 1.5, facecolor='#ecf0f1', alpha=0.8,
                         edgecolor='#bdc3c7', linewidth=1)
    ax.add_patch(market_bg)

    ax.text(9, 3.7, "BETTING MARKETS", ha='center', va='center',
            fontsize=14, fontweight='bold', color='#1a252f')

    ax.text(4, 3.2, f"Over 2.5 Goals: {test_data['over_2_5_goals_probability']:.1f}%",
            ha='center', va='center', fontsize=12, fontweight='bold', color='#27ae60')
    ax.text(9, 3.2, f"Both Teams Score: {test_data['both_teams_score_probability']:.1f}%",
            ha='center', va='center', fontsize=12, fontweight='bold', color='#e67e22')
    ax.text(14, 3.2, f"Processing: {test_data['processing_time']:.2f}s",
            ha='center', va='center', fontsize=12, fontweight='bold', color='#7f8c8d')

    # Footer
    ax.text(9, 2.0, f"Enhanced Intelligence • Report Accuracy: {test_data['report_accuracy_probability']*100:.1f}%",
            ha='center', va='center', fontsize=10, color='#7f8c8d')
    ax.text(9, 1.6, "⚠️ For educational purposes only - Not financial advice",
            ha='center', va='center', fontsize=9, style='italic', color='#e74c3c')

    # Save
    plt.tight_layout()
    plt.savefig('test_horizontal_layout.png', dpi=300, bbox_inches='tight',
                facecolor='#f8f9fa', pad_inches=0.3)
    plt.close()

    print("✅ Test horizontal PNG generated: test_horizontal_layout.png")
    print("📐 Layout: 18x10 (horizontal)")
    print("🎨 Features: Enhanced styling, larger fonts, better organization")

if __name__ == "__main__":
    test_horizontal_png()
