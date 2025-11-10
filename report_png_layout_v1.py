"""
Backup of original save_image method from generate_fast_reports.py
Safest rollback point for PNG report layout.
"""
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle, Wedge
from matplotlib.colors import LinearSegmentedColormap

def save_image(match_data, path):
    """Original visually stunning match prediction card with gauges and centered results (backup)"""
    reliability_metrics = match_data.get('reliability_metrics', {}) or {}
    reliability_score = reliability_metrics.get('score')
    fig, ax = plt.subplots(figsize=(14, 18))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 20)
    ax.axis('off')
    # --- HEADER SECTION IMPROVEMENT ---
    # Modern gradient header background
    header_cmap = LinearSegmentedColormap.from_list("header_grad", ["#eaf6fb", "#dbeafe", "#f8fafc"])
    ax.imshow([[0,1],[0,1]], extent=(0.2, 9.8, 17.5, 19.7), cmap=header_cmap, aspect='auto', alpha=0.7)
    # Branding/logo placeholder (top left)
    ax.text(0.4, 19.4, "AI Sports Prediction System", fontsize=13, fontweight='bold', color='#34495e', ha='left', va='center')
    # Team names (centered, modern font)
    ax.text(5, 19.0, f"{match_data['home_team']}", ha='center', va='center', fontsize=26, fontweight='bold', color='#3498db', fontname='DejaVu Sans')
    ax.text(5, 18.5, "VS", ha='center', va='center', fontsize=18, fontweight='bold', color='#636e72', alpha=0.7, fontname='DejaVu Sans')
    ax.text(5, 18.0, f"{match_data['away_team']}", ha='center', va='center', fontsize=26, fontweight='bold', color='#e74c3c', fontname='DejaVu Sans')
    # League/date/time (below, lighter color)
    ax.text(5, 17.7, f"{match_data.get('league', 'League')} • {match_data['date']} at {match_data['time']}", ha='center', va='center', fontsize=14, fontweight='bold', color='#7f8c8d', fontname='DejaVu Sans')
    # --- END HEADER IMPROVEMENT ---
    # Removed Rectangle patch for results box to eliminate visible box artifact
    ax.text(5, 16.8, "🏆 PREDICTED FINAL SCORE", ha='center', va='center', fontsize=18, fontweight='bold', color='#8e44ad')
    score_parts = match_data['expected_final_score'].split('-')
    home_score = score_parts[0].strip()
    away_score = score_parts[1].strip()
    home_team_short = match_data['home_team'][:15] + "..." if len(match_data['home_team']) > 15 else match_data['home_team']
    away_team_short = match_data['away_team'][:15] + "..." if len(match_data['away_team']) > 15 else match_data['away_team']
    ax.text(5, 16.3, f"{home_team_short} {home_score} - {away_score} {away_team_short}", ha='center', va='center', fontsize=22, fontweight='bold', color='#2c3e50')
    ax.text(5, 15.8, f"Expected Goals: {home_team_short} {match_data['expected_home_goals']:.1f} - {match_data['expected_away_goals']:.1f} {away_team_short}", ha='center', va='center', fontsize=14, fontweight='bold', color='#34495e')
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
    # --- WINNING CHANCES SECTION MODERNIZATION (NO BOX/BORDER) ---
    # Use normalized coordinates for layout, gradient only, no Rectangle/box
    win_cmap = LinearSegmentedColormap.from_list("win_grad", ["#f8fafc", "#eaf6fb", "#f0f4f8"])
    ax.imshow([[0,1],[0,1]], extent=(0, 10, 0.45, 0.62), cmap=win_cmap, aspect='auto', alpha=0.85, zorder=1, transform=ax.transAxes)
    # Section title
    ax.text(0.5, 0.60, "WINNING CHANCES", ha='center', va='center', fontsize=17, fontweight='bold', color='#34495e', zorder=2, transform=ax.transAxes)
    # Reliability indicator
    reliability_score = match_data.get('reliability_metrics', {}).get('score', 0)
    reliability_text = f"High {reliability_score:.1f}" if reliability_score else "Limited"
    ax.text(0.5, 0.575, reliability_text, ha='center', va='center', fontsize=11, color='#3498db', fontweight='bold', alpha=0.85, zorder=2, transform=ax.transAxes)
    ax.text(0.5, 0.56, "Reliable outlook with minor variance expected.", ha='center', va='center', fontsize=9, color='#636e72', alpha=0.7, zorder=2, transform=ax.transAxes)
    # Win/Draw/Away probabilities - aligned layout
    home_win = match_data.get('home_win_probability', 0)
    draw = match_data.get('draw_probability', 0)
    away_win = match_data.get('away_win_probability', 0)
    home_team = match_data.get('home_team', 'Home')
    away_team = match_data.get('away_team', 'Away')
    # Home
    ax.text(0.22, 0.53, f"{int(round(home_win))}%", ha='center', va='center', fontsize=21, fontweight='bold', color='#3498db', zorder=3, transform=ax.transAxes)
    ax.text(0.22, 0.50, home_team[:10], ha='center', va='center', fontsize=12, color='#34495e', zorder=3, transform=ax.transAxes)
    # Draw
    ax.text(0.5, 0.53, f"{int(round(draw))}%", ha='center', va='center', fontsize=21, fontweight='bold', color='#636e72', zorder=3, transform=ax.transAxes)
    ax.text(0.5, 0.50, "Draw", ha='center', va='center', fontsize=12, color='#34495e', zorder=3, transform=ax.transAxes)
    # Away
    ax.text(0.78, 0.53, f"{int(round(away_win))}%", ha='center', va='center', fontsize=21, fontweight='bold', color='#e74c3c', zorder=3, transform=ax.transAxes)
    ax.text(0.78, 0.50, away_team[:10], ha='center', va='center', fontsize=12, color='#34495e', zorder=3, transform=ax.transAxes)
    # Most likely outcome highlight - aligned below, NO border/box
    likely = max([(home_win, 'home'), (draw, 'draw'), (away_win, 'away')], key=lambda x: x[0])[1]
    likely_text = "MOST LIKELY HOME WIN" if likely == 'home' else "MOST LIKELY DRAW" if likely == 'draw' else "MOST LIKELY AWAY WIN"
    likely_color = '#3498db' if likely == 'home' else '#636e72' if likely == 'draw' else '#e74c3c'
    ax.text(0.5, 0.47, likely_text, ha='center', va='center', fontsize=13, fontweight='bold', color=likely_color, bbox=dict(facecolor='#f8fafc', edgecolor='none', boxstyle='round,pad=0.3', alpha=0.10), zorder=4, transform=ax.transAxes)
    plt.savefig(path, bbox_inches="tight")
    plt.close(fig)
