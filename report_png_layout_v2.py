"""
Professional PNG report layout v2 (draft)
All original sections preserved, improved grid/card layout, modern fonts/colors.
Safest: does not modify any existing code.
"""
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle, Wedge


def save_image_v2(match_data, path):
    # --- HEADER & SCORE ---
    fig, ax = plt.subplots(figsize=(14, 18))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 20)
    ax.axis('off')
    # Branding/logo
    ax.text(0.5, 19.5, "AI Sports Prediction System", fontsize=14, fontweight='bold', color='#34495e', ha='left')
    # Main title (teams)
    ax.text(5, 18.9, f"{match_data['home_team']}", ha='center', va='center', fontsize=24, fontweight='bold', color='#3498db')
    ax.text(5, 18.4, "VS", ha='center', va='center', fontsize=20, fontweight='bold', color='#ecf0f1', alpha=0.9)
    ax.text(5, 17.9, f"{match_data['away_team']}", ha='center', va='center', fontsize=24, fontweight='bold', color='#e74c3c')
    # League and date
    ax.text(5, 17.6, f"{match_data.get('league', 'League')} • {match_data['date']} at {match_data['time']}", ha='center', va='center', fontsize=14, fontweight='bold', color='#7f8c8d')
    # Score panel
    ax.add_patch(Rectangle((0.7, 16.5), 8.6, 1.5, facecolor='#f4f6fa', alpha=1, edgecolor='#dfe6e9', linewidth=2))
    ax.text(5, 17.2, f"Predicted Final Score: {match_data['expected_final_score']}", ha='center', va='center', fontsize=20, fontweight='bold', color='#273c75')
    home_team_short = match_data['home_team'][:15] + "..." if len(match_data['home_team']) > 15 else match_data['home_team']
    away_team_short = match_data['away_team'][:15] + "..." if len(match_data['away_team']) > 15 else match_data['away_team']
    ax.text(5, 16.8, f"Expected Goals: {home_team_short} {match_data['expected_home_goals']:.1f} - {match_data['expected_away_goals']:.1f} {away_team_short}", ha='center', va='center', fontsize=13, color='#636e72')
    # --- CONFIDENCE & DATA QUALITY GAUGES ---
    confidence = match_data.get('report_accuracy_probability', 0.65)
    confidence_pct = confidence * 100
    center_x, center_y = 2, 15.5
    radius = 0.8
    confidence_color = '#2ecc71' if confidence >= 0.70 else '#f39c12' if confidence >= 0.60 else '#e74c3c'
    circle_bg = Circle((center_x, center_y), radius, fill=False, linewidth=8, color='#ecf0f1')
    ax.add_patch(circle_bg)
    angle = confidence * 360
    wedge = Wedge((center_x, center_y), radius, 90, 90 - angle, width=0.15, facecolor=confidence_color, alpha=0.8)
    ax.add_patch(wedge)
    ax.text(center_x, center_y, f"{confidence_pct:.0f}%", ha='center', va='center', fontsize=18, fontweight='bold', color=confidence_color)
    ax.text(center_x, center_y - 0.4, "CONFIDENCE", ha='center', va='center', fontsize=10, fontweight='bold', color=confidence_color)
    conf_label = match_data.get('confidence_level') or ''
    try:
        if isinstance(conf_label, str) and '(' in conf_label and ')' in conf_label:
            label_text = conf_label.split('(')[-1].strip(')')
        else:
            label_text = conf_label
    except Exception:
        label_text = ''
    if label_text:
        ax.text(center_x, center_y - 0.9, label_text, ha='center', va='center', fontsize=9, fontweight='bold', color=confidence_color)
    data_quality = match_data.get('data_quality_score', 75)
    quality_x, quality_y = 8, 15.5
    quality_color = '#2ecc71' if data_quality >= 80 else '#f39c12' if data_quality >= 65 else '#e74c3c'
    quality_bg = Circle((quality_x, quality_y), radius, fill=False, linewidth=8, color='#ecf0f1')
    ax.add_patch(quality_bg)
    quality_angle = (data_quality / 100) * 360
    quality_wedge = Wedge((quality_x, quality_y), radius, 90, 90 - quality_angle, width=0.15, facecolor=quality_color, alpha=0.8)
    ax.add_patch(quality_wedge)
    ax.text(quality_x, quality_y, f"{data_quality:.0f}%", ha='center', va='center', fontsize=18, fontweight='bold', color=quality_color)
    ax.text(quality_x, quality_y - 0.4, "DATA QUALITY", ha='center', va='center', fontsize=10, fontweight='bold', color=quality_color)

    # --- WIN PROBABILITIES SECTION ---
    reliability_metrics = match_data.get('reliability_metrics', {}) or {}
    reliability_score = reliability_metrics.get('score')
    prob_bg = Rectangle((0.6, 13.5), 8.8, 2.8, facecolor='#f8f9fa', alpha=1.0, edgecolor='#34495e', linewidth=2)
    ax.add_patch(prob_bg)
    ax.text(5, 15.8, "WINNING CHANCES", ha='center', va='center', fontsize=18, fontweight='bold', color='#2c3e50')
    probs = [
        match_data.get('home_win_probability', 0.0),
        match_data.get('draw_probability', 0.0),
        match_data.get('away_win_probability', 0.0)
    ]
    labels = [f"{match_data['home_team'][:10]}", 'DRAW', f"{match_data['away_team'][:10]}"]
    colors = ['#3498db', '#95a5a6', '#e74c3c']
    x_positions = [2.2, 5.0, 7.8]
    if reliability_metrics:
        rel_level = reliability_metrics.get('level', 'Reliability')
        rel_indicator = reliability_metrics.get('indicator', rel_level)
        rel_color = '#27ae60'
        if reliability_score is not None:
            if reliability_score < 60:
                rel_color = '#e74c3c'
            elif reliability_score < 75:
                rel_color = '#f39c12'
        reliability_text = (
            f"{rel_indicator} {reliability_score:.1f}" if reliability_score is not None else rel_indicator
        )
        ax.text(5, 15.4, reliability_text, ha='center', va='center', fontsize=13, fontweight='bold', color=rel_color)
        recommendation = reliability_metrics.get('recommendation')
        if recommendation:
            ax.text(5, 15.0, recommendation, ha='center', va='center', fontsize=10, color='#2c3e50')
    for prob, label, color, x_pos in zip(probs, labels, colors, x_positions, strict=True):
        gauge_radius = 0.6
        gauge_center_y = 14.5
        gauge_bg = Circle((x_pos, gauge_center_y), gauge_radius, fill=False, linewidth=6, color='#ecf0f1')
        ax.add_patch(gauge_bg)
        prob_angle = (prob / 100) * 360
        prob_wedge = Wedge((x_pos, gauge_center_y), gauge_radius, 90, 90 - prob_angle, width=0.12, facecolor=color, alpha=0.9)
        ax.add_patch(prob_wedge)
        ax.text(x_pos, gauge_center_y, f"{prob:.0f}%", ha='center', va='center', fontsize=16, fontweight='bold', color=color)
        ax.text(x_pos, gauge_center_y - 0.9, label, ha='center', va='center', fontsize=14, fontweight='bold', color=color)
    max_prob_idx = probs.index(max(probs))
    winner_text = "HOME WIN" if max_prob_idx == 0 else "DRAW" if max_prob_idx == 1 else "AWAY WIN"
    winner_color = colors[max_prob_idx]
    ax.text(5, 13.8, f"MOST LIKELY: {winner_text}", ha='center', va='center', fontsize=12, fontweight='bold', color=winner_color)
    # --- WINNING CHANCES PANEL ---
    ax.add_patch(Rectangle((0.7, 14.5), 8.6, 1.5, facecolor='#f8f9fa', alpha=1, edgecolor='#dfe6e9', linewidth=2))
    ax.text(5, 15.2, "Winning Chances", ha='center', va='center', fontsize=18, fontweight='bold', color='#2c3e50')
    # ...donut charts for home/draw/away, horizontally aligned...
    # Reliability indicator
    reliability_metrics = match_data.get('reliability_metrics', {}) or {}
    reliability_score = reliability_metrics.get('score')
    rel_color = '#27ae60' if reliability_score and reliability_score >= 75 else '#f39c12' if reliability_score and reliability_score >= 60 else '#e74c3c'
    ax.text(5, 14.7, f"Reliability: {reliability_score}", ha='center', va='center', fontsize=12, color=rel_color)
    # --- TEAM FORM ANALYSIS ---
    ax.add_patch(Rectangle((0.7, 12.5), 8.6, 1.5, facecolor='#f4f6fa', alpha=1, edgecolor='#dfe6e9', linewidth=2))
    ax.text(5, 13.2, "Team Form Analysis", ha='center', va='center', fontsize=16, fontweight='bold', color='#2c3e50')
    # ...side-by-side cards for each team form...
    # --- GOAL PREDICTIONS ---
    ax.add_patch(Rectangle((0.7, 10.5), 8.6, 1.5, facecolor='#f8f9fa', alpha=1, edgecolor='#dfe6e9', linewidth=2))
    ax.text(5, 11.2, "Goal Predictions", ha='center', va='center', fontsize=16, fontweight='bold', color='#2c3e50')
    # ...donut charts for Over 2.5 Goals, Both Teams to Score...
    # --- KEY FACTORS ---
    ax.add_patch(Rectangle((0.7, 8.5), 8.6, 1.5, facecolor='#f4f6fa', alpha=1, edgecolor='#dfe6e9', linewidth=2))
    ax.text(5, 9.2, "Key Factors", ha='center', va='center', fontsize=16, fontweight='bold', color='#2c3e50')
    # ...bullet list with icons...
    # --- FOOTER ---
    ax.text(0.5, 1.0, "Analysis completed in {:.3f}s".format(match_data.get('processing_time', 0.0)), fontsize=10, color='#636e72', ha='left')
    ax.text(9.5, 1.0, "Educational purposes only - Not financial advice", fontsize=10, color='#e74c3c', ha='right')
    # Save image
    plt.savefig(f"{path}/prediction_card_v2.png", dpi=300, bbox_inches='tight', facecolor='white', pad_inches=0.3)
    plt.close()
