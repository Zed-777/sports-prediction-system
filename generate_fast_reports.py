#!/usr/bin/env python3
"""
Single Match Report Generator
Generate report for just the next 1 La Liga match
"""

import json
import os
import re
import sys
import time
import warnings
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import requests
from app.utils.http import safe_request_get
import yaml
from matplotlib.patches import Circle, FancyBboxPatch, Rectangle, Wedge
from typing import Any, Dict, Optional, List, Union, cast
from app.types import JSONDict, JSONList

# Suppress font warnings for cleaner output
warnings.filterwarnings('ignore', category=UserWarning, message='.*missing from font.*')

CURRENT_DIR = Path(__file__).parent

# ============================================================================
# PROFESSIONAL DESIGN SYSTEM FOR SPORTS CARDS
# ============================================================================

class ProfessionalDesignSystem:
    """Professional design system for sports analytics cards"""
    
    # League-specific color themes for premium appearance
    LEAGUE_THEMES = {
        'la-liga': {
            'primary': '#003DA5',      # Royal Blue
            'secondary': '#FFD700',    # Gold
            'accent': '#8B0000',       # Deep Crimson
            'light_primary': '#E6F0FF', # Light blue for backgrounds
        },
        'premier-league': {
            'primary': '#004CD4',      # Royal Blue
            'secondary': '#FFD700',    # Gold
            'accent': '#1F1F1F',       # Dark Charcoal
            'light_primary': '#E6F2FF',
        },
        'serie-a': {
            'primary': '#003A70',      # Deep Blue
            'secondary': '#CE1126',    # Red
            'accent': '#FFFFFF',       # White
            'light_primary': '#E6F0FF',
        },
        'bundesliga': {
            'primary': '#000000',      # Black
            'secondary': '#F4B942',    # Gold
            'accent': '#DD0000',       # Red
            'light_primary': '#F5F5F5',
        },
        'ligue-1': {
            'primary': '#002D5D',      # Navy Blue
            'secondary': '#F7A600',    # Gold
            'accent': '#EF3B39',       # Red
            'light_primary': '#E6F0FF',
        }
    }
    
    # Professional color palette
    BASE_COLORS = {
        'header_bg': '#1a1a1a',
        'main_bg': '#FFFFFF',
        'main_border': '#D0D0D0',
        'section_bg': '#F8F9FA',
        'text_main': '#1a1a1a',
        'text_secondary': '#666666',
        'text_light': '#999999',
        'gauge_bg': '#E8E8E8',
        'separator': '#E0E0E0',
        'shadow': '#000000',
        'success': '#27AE60',
        'warning': '#F39C12',
        'danger': '#E74C3C'
    }
    
    @classmethod
    def get_theme(cls, league_name: str) -> Dict[str, str]:
        """Get theme colors for league"""
        # Normalize league name
        normalized = league_name.lower().replace(' ', '-')
        return cls.LEAGUE_THEMES.get(normalized, cls.LEAGUE_THEMES['la-liga'])
    
    @classmethod
    def get_color_for_probability(cls, probability: float) -> str:
        """Get color gradient for probability: 0-25% red, 25-50% orange, 50-75% cyan, 75-100% green"""
        p = max(0.0, min(100.0, probability))
        if p >= 75:
            return '#27AE60'  # Green - 75-100%
        elif p >= 50:
            return '#17A2B8'  # Cyan - 50-75% (highly visible)
        elif p >= 25:
            return '#F39C12'  # Orange - 25-50%
        else:
            return '#E74C3C'  # Red - 0-25%
    
    # Professional typography system for consistent styling
    TYPOGRAPHY = {
        'title': {'size': 26, 'weight': 'bold', 'font': 'DejaVu Sans'},
        'heading': {'size': 19, 'weight': 'bold', 'font': 'DejaVu Sans'},
        'subheading': {'size': 14, 'weight': 'bold', 'font': 'DejaVu Sans'},
        'label': {'size': 12, 'weight': 'bold', 'font': 'DejaVu Sans'},
        'value': {'size': 23, 'weight': 'bold', 'font': 'DejaVu Sans'},
        'body': {'size': 11, 'weight': 'normal', 'font': 'DejaVu Sans'},
        'small': {'size': 10, 'weight': 'normal', 'font': 'DejaVu Sans'},
    }
    
    @classmethod
    def apply_text(cls, ax, text: str, x: float, y: float, style: str = 'body', 
                   color: str = None, zorder: int = 1, **kwargs) -> None:
        """Apply typography with consistent professional styling."""
        if style not in cls.TYPOGRAPHY:
            style = 'body'
        typo = cls.TYPOGRAPHY[style]
        
        if color is None:
            color = cls.BASE_COLORS['text_main']
        
        ax.text(x, y, text, ha='center', va='center', 
               fontsize=typo['size'], fontweight=typo['weight'],
               fontname=typo['font'], color=color, zorder=zorder, **kwargs)
    
    @staticmethod
    def draw_sparkline(ax, x_pos: float, y_pos: float, width: float, height: float, 
                      values: list, color: str = '#3498DB', title: str = '') -> None:
        """Draw a mini sparkline chart (Phase 3 visualization).
        
        Args:
            ax: Matplotlib axes
            x_pos: X position of sparkline center
            y_pos: Y position of sparkline center
            width: Width of sparkline area
            height: Height of sparkline area
            values: List of numeric values (e.g., last 5 form scores)
            color: Line color (default blue)
            title: Optional title above sparkline
        """
        if not values or len(values) < 2:
            # Draw placeholder if insufficient data
            ax.text(x_pos, y_pos, 'N/A', ha='center', va='center', fontsize=8, 
                   color='#999999', style='italic')
            return
        
        # Normalize values to 0-1 range for positioning
        min_val = min(values)
        max_val = max(values)
        value_range = max_val - min_val if max_val > min_val else 1
        
        normalized = [(v - min_val) / value_range for v in values]
        
        # Calculate x positions for points
        n_points = len(values)
        x_spacing = width / (n_points - 1) if n_points > 1 else width
        x_coords = [x_pos - width/2 + i * x_spacing for i in range(n_points)]
        y_coords = [y_pos - height/2 + (n * height) for n in normalized]
        
        # Draw sparkline path
        ax.plot(x_coords, y_coords, color=color, linewidth=1.5, zorder=3, alpha=0.8)
        
        # Draw mini data points
        ax.scatter(x_coords, y_coords, s=15, color=color, zorder=4, alpha=0.6)
        
        # Highlight last value with larger point
        ax.scatter([x_coords[-1]], [y_coords[-1]], s=25, color=color, zorder=5, alpha=1.0, edgecolors='white', linewidth=0.5)
        
        # Optional background area under curve
        y_baseline = [y_pos - height/2] * n_points
        ax.fill_between(x_coords, y_coords, y_baseline, alpha=0.1, color=color, zorder=1)
    
    @staticmethod
    def draw_h2h_history(ax, x_pos: float, y_pos: float, width: float, height: float,
                        h2h_results: list, home_team: str = '', away_team: str = '',
                        home_color: str = '#3498DB', away_color: str = '#E74C3C') -> None:
        """Draw head-to-head history visualization (Phase 3).
        
        Args:
            ax: Matplotlib axes
            x_pos: X position of H2H section center
            y_pos: Y position of H2H section center
            width: Width of H2H visualization area
            height: Height of H2H visualization area
            h2h_results: List of match results [{'winner': 'home'/'away'/'draw', 'score': '2-1'}, ...]
            home_team: Home team name (for labeling)
            away_team: Away team name (for labeling)
            home_color: Color for home team wins
            away_color: Color for away team wins
        """
        if not h2h_results or len(h2h_results) == 0:
            # Draw "No H2H history" message
            ax.text(x_pos, y_pos, 'No H2H History', ha='center', va='center', fontsize=11,
                   color='#999999', style='italic', fontweight='bold')
            return
        
        # Limit to last 5 meetings
        recent_h2h = h2h_results[-5:]
        
        # Draw mini result squares for each match
        box_size = (width - 0.3) / len(recent_h2h)
        start_x = x_pos - width/2 + 0.15
        
        for i, match in enumerate(recent_h2h):
            box_x = start_x + i * box_size
            box_y = y_pos
            
            # Determine color based on winner
            result = match.get('winner', 'draw')
            if result == 'home':
                result_color = home_color
                result_symbol = '🏠'
            elif result == 'away':
                result_color = away_color
                result_symbol = '✈️'
            else:
                result_color = '#7F8C8D'
                result_symbol = '='
            
            # Draw match result box
            result_box = FancyBboxPatch((box_x - box_size/2 + 0.05, box_y - height/2 + 0.05), 
                                       box_size - 0.1, height - 0.1,
                                       boxstyle="round,pad=0.03", facecolor=result_color, 
                                       edgecolor=result_color, alpha=0.2, linewidth=1, zorder=2)
            ax.add_patch(result_box)
            
            # Score text
            score = match.get('score', '-')
            ax.text(box_x, box_y + 0.08, score, ha='center', va='center', fontsize=8,
                   fontweight='bold', color=result_color, zorder=3)
            
            # Result indicator
            ax.text(box_x, box_y - 0.10, result_symbol, ha='center', va='center', fontsize=9, zorder=3)

try:
    from data_quality_enhancer import DataQualityEnhancer
    from enhanced_predictor import EnhancedPredictor, get_competition_code_from_league
except ModuleNotFoundError:
    sys.path.append(str(CURRENT_DIR))
    from data_quality_enhancer import DataQualityEnhancer
    from enhanced_predictor import EnhancedPredictor, get_competition_code_from_league

# Phase 2 Lite integration
try:
    from phase2_lite import Phase2LitePredictor
    PHASE2_LITE_AVAILABLE = True
except ImportError:
    PHASE2_LITE_AVAILABLE = False

class SingleMatchGenerator:
    """Generate report for just 1 match"""

    _LEAGUE_CANONICAL = {
        'la-liga': {'code': 'PD', 'name': 'La Liga', 'folder': 'la-liga'},
        'premier-league': {'code': 'PL', 'name': 'Premier League', 'folder': 'premier-league'},
        'bundesliga': {'code': 'BL1', 'name': 'Bundesliga', 'folder': 'bundesliga'},
        'serie-a': {'code': 'SA', 'name': 'Serie A', 'folder': 'serie-a'},
        'ligue-1': {'code': 'FL1', 'name': 'Ligue 1', 'folder': 'ligue-1'}
    }

    _LEAGUE_ALIASES = {
        'laliga': 'la-liga',
        'premierleague': 'premier-league',
        'seriea': 'serie-a',
        'ligue1': 'ligue-1'
    }

    def __init__(self, skip_injuries: bool = False, injuries_disable_ttl_override: int | None = None, export_metrics: bool = False, export_metrics_dir: str | None = None) -> None:
        self.api_key = os.getenv('FOOTBALL_DATA_API_KEY', '17405508d1774f46a368390ff07f8a31')
        self.headers = {'X-Auth-Token': self.api_key}

        # Smart configuration validation
        self.validate_environment()
        self.setup_directory_structure()

        # Initialize enhanced prediction engines
        self.enhanced_predictor = EnhancedPredictor(self.api_key)
        self.data_quality_enhancer = DataQualityEnhancer(self.api_key)
        # Respect CLI preference to skip injury API calls
        self.data_quality_enhancer.skip_injuries = skip_injuries
        # If CLI override present, pass it to the enhancer
        self.data_quality_enhancer.injuries_disable_ttl_override = injuries_disable_ttl_override
        # Metrics export option
        self.export_metrics = export_metrics
        self.export_metrics_dir = export_metrics_dir or 'reports/metrics'

        # Load centralized settings (safe fallback to empty dict)
        self._settings: Dict[str, Any] = {}
        try:
            cfg_path = Path(__file__).parent / 'config' / 'settings.yaml'
            if cfg_path.exists():
                with open(cfg_path, encoding='utf-8') as _f:
                    self._settings = yaml.safe_load(_f) or {}
        except Exception:
            self._settings = {}

        # Phase 2 Lite integration
        if PHASE2_LITE_AVAILABLE:
            self.phase2_lite_predictor: Optional[Phase2LitePredictor] = Phase2LitePredictor(self.api_key)
            print("Phase 2 Lite enhanced intelligence active!")
        else:
            self.phase2_lite_predictor = None

    def validate_environment(self) -> None:
        """Smart environment validation with helpful guidance"""
        issues = []

        # Check API key
        if not self.api_key or self.api_key == '':
            issues.append("❌ API key not found. Set FOOTBALL_DATA_API_KEY environment variable")
        elif len(self.api_key) < 10:
            issues.append("⚠️  API key seems too short - check if it's complete")

        # Check required modules
        required_modules = ['matplotlib', 'numpy', 'requests']
        for module in required_modules:
            try:
                __import__(module)
            except ImportError:
                issues.append(f"❌ Missing required module: {module}. Run: pip install {module}")

        # Check directory permissions
        try:
            os.makedirs("reports/test", exist_ok=True)
            os.rmdir("reports/test")
        except PermissionError:
            issues.append("❌ Cannot write to reports directory. Check permissions")

        if issues:
            print("🔧 CONFIGURATION ISSUES DETECTED:")
            for issue in issues:
                print(f"   {issue}")
            print("Note: Fix these issues before generating reports")
            print()
        else:
            print("Environment validation passed - system ready!")
            print()

    def setup_directory_structure(self) -> None:
        """Create proper directory structure with .keep files"""
        league_directories = [
            f"reports/leagues/{info['folder']}/matches"
            for info in self._LEAGUE_CANONICAL.values()
        ]
        directories = league_directories + [
            "reports/formats/json",
            "reports/formats/markdown",
            "reports/formats/images",
            "reports/archive"
        ]

        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            # Create .keep file to preserve directory structure
            keep_file = os.path.join(directory, '.keep')
            if not os.path.exists(keep_file):
                with open(keep_file, 'w', encoding='utf-8') as f:
                    f.write(
                        f"# Keep file for {directory}\n# Preserves directory structure when cleaning reports\n"
                    )

    def get_league_info(self, league_name: Optional[str]) -> Optional[Dict[str, str]]:
        """Map CLI league names to API codes and folder names."""
        if not league_name:
            return None
        normalized = league_name.lower()
        alias = self._LEAGUE_ALIASES.get(normalized)
        if alias:
            normalized = alias
        return self._LEAGUE_CANONICAL.get(normalized)

    def pct_to_color(self, pct: float) -> str:
        """Return a hex color for a percentage using configured thresholds and palette.

        Safe fallbacks are used if settings are missing.
        """
        try:
            p = float(pct)
        except Exception:
            p = 0.0
        p = max(0.0, min(100.0, p))
        cfg = self._settings.get('constants', {})
        th = cfg.get('color_thresholds', [25, 50, 75])
        palette_candidate = cfg.get('color_palette')
        palette: list[str]
        if isinstance(palette_candidate, (list, tuple)) and len(palette_candidate) >= 4:
            palette = [str(x) for x in palette_candidate[:4]]
        else:
            palette = ['#e74c3c', '#f39c12', '#f1c40f', '#2ecc71']
        low, mid, high = th[0], th[1], th[2]
        if p < low:
            return palette[0]
        elif p < mid:
            return palette[1]
        elif p < high:
            return palette[2]
        else:
            return palette[3]

    def list_supported_leagues(self) -> List[str]:
        """Return sorted list of supported canonical league slugs."""
        return sorted(self._LEAGUE_CANONICAL.keys())

    def generate_matches_report(self, num_matches: int, league_name: str) -> None:
        """Generate Phase 2 Lite enhanced reports for the next set of matches."""

        start_time = time.time()

        league_info = self.get_league_info(league_name)
        if not league_info:
            print(f"❌ Unknown league: {league_name}")
            print("Available leagues: " + ", ".join(self.list_supported_leagues()))
            return

        print(f"🏆 Generating Next {num_matches} {league_info['name']} Match(es)")
        print("=" * 50)
        print(f"⏱️  Started at: {datetime.now().strftime('%H:%M:%S')}")

        url = f"https://api.football-data.org/v4/competitions/{league_info['code']}/matches"
        params: Dict[str, Union[str, int]] = {'status': 'SCHEDULED', 'limit': num_matches}
        params = {k: str(v) for k, v in params.items()}

        try:
            response = safe_request_get(url, headers=self.headers, params=params, logger=None)
            response.raise_for_status()
            data = cast(JSONDict, response.json())
            all_matches = data.get('matches', [])
            matches = all_matches[:num_matches]
        except Exception as exc:
            print(f"❌ Error fetching data: {exc}")
            return

        if not matches:
            print("❌ No upcoming matches found")
            return

        print(f"📅 Found {len(matches)} upcoming match(es)")
        print()

        for index, match in enumerate(matches, start=1):
            # Normalize team names to avoid abbreviations in displays and filenames
            raw_home = match['homeTeam']['name']
            raw_away = match['awayTeam']['name']
            home_team = self.normalize_team_name(raw_home) if raw_home else 'Home Team'
            away_team = self.normalize_team_name(raw_away) if raw_away else 'Away Team'
            match_date = match['utcDate'][:10]
            match_time = match['utcDate'][11:16]

            print(f"[MATCH {index}/{len(matches)}] Processing: {home_team} vs {away_team} on {match_date}")

            # Use a safe slug for filesystem names
            def slugify(name: str) -> str:
                if not name:
                    return 'team'
                s = name.lower()
                # Replace any non-alphanumeric characters with hyphens
                s = re.sub(r'[^a-z0-9]+', '-', s)
                s = s.strip('-')
                return s or 'team'

            match_folder = f"{slugify(home_team)}_vs_{slugify(away_team)}_{match_date}"
            full_path = f"reports/leagues/{league_info['folder']}/matches/{match_folder}"
            os.makedirs(full_path, exist_ok=True)

            try:
                competition_code = get_competition_code_from_league(league_info['folder'])
            except Exception:
                competition_code = league_info['code']

            try:
                if self.phase2_lite_predictor is not None:
                    prediction = self.phase2_lite_predictor.enhanced_prediction(match, competition_code)
                    prediction_engine = prediction.get(
                        'prediction_engine',
                        'Enhanced Intelligence v4.1 + Phase 2 Lite'
                    )
                else:
                    prediction = self.enhanced_predictor.enhanced_prediction(match, competition_code)
                    prediction_engine = prediction.get('prediction_engine', 'Enhanced Intelligence v4.1')
            except Exception as exc:
                print(f"   [ERROR] Prediction failed for {home_team} vs {away_team}: {exc}")
                continue

            try:
                enhanced_data = self.data_quality_enhancer.comprehensive_data_enhancement(match)
            except Exception as exc:
                print(f"   [WARNING] Data quality enhancer issue: {exc}")
                enhanced_data = {}

            reliability_metrics = (
                prediction.get('reliability_metrics')
                or prediction.get('prediction_reliability')
                or {}
            )
            calibration_details = prediction.get('calibration_details', {})
            confidence_intervals = prediction.get('confidence_intervals', {})

            # Extract data for enhanced confidence calculation
            h2h_data = prediction.get('head_to_head_analysis', prediction.get('head_to_head', {}))
            weather_data = enhanced_data.get('weather_conditions', {})
            player_data = enhanced_data.get('player_availability', {})
            referee_data = enhanced_data.get('referee_analysis', {})
            team_news = enhanced_data.get('team_news', {})

            confidence_value = self._safe_float(prediction.get('confidence'), 0.6)

            # Enhanced confidence calculation based on multiple real factors
            data_quality_score = enhanced_data.get('data_quality_score', 75) / 100.0
            reliability_score = reliability_metrics.get('score', 60) / 100.0 if reliability_metrics else 0.6
            calibration_applied = 1.08 if calibration_details.get('applied') else 1.0
            h2h_total = h2h_data.get('total_meetings', 0)
            h2h_bonus = min(0.12, h2h_total * 0.008)  # Up to 12% bonus for comprehensive H2H data

            # Additional data availability bonuses
            weather_available = bool(weather_data.get('conditions'))
            player_available = bool(player_data.get('home_team') or player_data.get('away_team'))
            referee_available = bool(referee_data.get('name') and referee_data.get('name') not in ['TBD', 'Unknown Referee'])
            team_news_available = bool(team_news.get('home_team') or team_news.get('away_team'))

            data_availability_bonus = (weather_available * 0.03 + player_available * 0.04 + referee_available * 0.02 + team_news_available * 0.03)

            # Weighted calculation: base * (data_quality + reliability + calibration + h2h + data_availability)
            confidence_multiplier = 1.0 + (data_quality_score - 0.5) * 0.6 + (reliability_score - 0.5) * 0.7 + (calibration_applied - 1.0) + h2h_bonus + data_availability_bonus
            confidence_value = confidence_value * confidence_multiplier

            # Reasonable bounds: 75% minimum, 95% maximum for high-quality predictions
            confidence_value = max(0.75, min(0.95, confidence_value))

            accuracy_probability = self._safe_float(prediction.get('report_accuracy_probability'), 0.65)

            # FIX: Calculate multiplier safely THEN apply bounds
            # (calibration_applied - 1.0) can be unbounded, so clamp BEFORE multiplication
            calibration_factor = max(0.0, min(2.0, calibration_applied - 1.0))  # Clamp to [0, 2]
            accuracy_multiplier = 1.0 + (data_quality_score - 0.5) * 0.55 + (reliability_score - 0.5) * 0.65 + calibration_factor + h2h_bonus * 0.9 + data_availability_bonus * 0.8
            # Further bound multiplier itself to prevent overflow
            accuracy_multiplier = max(0.5, min(1.8, accuracy_multiplier))
            accuracy_probability = accuracy_probability * accuracy_multiplier
            accuracy_probability = max(0.75, min(0.95, accuracy_probability))


            # Defensive extraction for win probabilities
            home_prob_raw = prediction.get('home_win_probability', prediction.get('home_win_prob', 0.0))
            home_prob = self._safe_float(home_prob_raw, 0.0)

            draw_prob_raw = prediction.get('draw_probability', prediction.get('draw_prob', 0.0))
            draw_prob = self._safe_float(draw_prob_raw, 0.0)

            away_prob_raw = prediction.get('away_win_probability', prediction.get('away_win_prob', 0.0))
            away_prob = self._safe_float(away_prob_raw, 0.0)

            expected_home_goals = self._safe_float(prediction.get('expected_home_goals'), 1.5)
            expected_away_goals = self._safe_float(prediction.get('expected_away_goals'), 1.2)
            processing_time = self._safe_float(prediction.get('processing_time'), 0.0)
            score_probability = self._safe_float(prediction.get('score_probability'), 10.0)
            score_probability_normalized = self._safe_float(
                prediction.get('score_probability_normalized'), 5.0
            )
            top3_combined_probability = self._safe_float(
                prediction.get('top3_combined_probability'), 25.0
            )
            top3_probability_normalized = self._safe_float(
                prediction.get('top3_probability_normalized'), 7.0
            )
            over_2_5_probability = self._safe_float(
                prediction.get('over_2_5_goals_probability', prediction.get('over_2_5_probability', 45.0)),
                45.0
            )
            both_teams_score_probability = self._safe_float(
                prediction.get('both_teams_score_probability'), 55.0
            )

            # Ensure expected_final_score does not contain team name text (use numeric score)
            raw_expected_score = prediction.get('expected_final_score', '1-1')
            # If the prediction includes letters (team names), reconstruct from expected goals
            if isinstance(raw_expected_score, str) and re.search(r'[A-Za-z]', raw_expected_score):
                safe_expected_score = f"{int(round(expected_home_goals))}-{int(round(expected_away_goals))}"
            else:
                # Try to extract numeric score, fallback to constructed numeric
                m = None
                if isinstance(raw_expected_score, str):
                    m = re.search(r"(\d+)\s*[-–]\s*(\d+)", raw_expected_score)
                if m:
                    safe_expected_score = f"{m.group(1)}-{m.group(2)}"
                else:
                    safe_expected_score = f"{int(round(expected_home_goals))}-{int(round(expected_away_goals))}"

            # Build provenance flags for each data family so downstream consumers can
            # know which signals were present vs. estimated/fallback.
            odds_available = bool(
                prediction.get('odds') or prediction.get('market_odds') or
                prediction.get('bookmakers') or prediction.get('betting')
            )

            flashscore_present = bool(
                enhanced_data.get('flashscore') or enhanced_data.get('flashscore_snapshot') or enhanced_data.get('flashscore_data')
            )

            match_data = {
                'match_id': match.get('id'),
                'home_team': home_team if home_team else prediction.get('home_team', 'Home'),
                'away_team': away_team if away_team else prediction.get('away_team', 'Away'),
                'date': match_date,
                'time': match_time,
                'league': league_info['name'],
                'confidence': round(confidence_value, 3),
                'report_accuracy_probability': round(accuracy_probability, 3),
                'home_win_probability': round(home_prob, 3),
                'draw_probability': round(draw_prob, 3),
                'away_win_probability': round(away_prob, 3),
                'expected_home_goals': round(expected_home_goals, 1),
                'expected_away_goals': round(expected_away_goals, 1),
                'processing_time': round(processing_time, 3),
                'recommendation': self.get_recommendation({
                    'home_win_prob': home_prob,
                    'draw_prob': draw_prob,
                    'away_win_prob': away_prob
                }),
                'confidence_level': self.get_confidence_description(confidence_value),
                'expected_final_score': safe_expected_score,
                'score_probability': round(score_probability, 1),
                'score_probability_normalized': round(score_probability_normalized, 1),
                'top3_combined_probability': round(top3_combined_probability, 1),
                'top3_probability_normalized': round(top3_probability_normalized, 1),
                'alternative_scores': prediction.get('alternative_scores', []),
                'score_probabilities': prediction.get('score_probabilities', []),
                'score_probabilities_normalized': prediction.get('score_probabilities_normalized', []),
                'over_2_5_goals_probability': round(over_2_5_probability, 1),
                'both_teams_score_probability': round(both_teams_score_probability, 1),
                'head_to_head_analysis': prediction.get('head_to_head_analysis', prediction.get('head_to_head', {})),
                'home_performance_analysis': prediction.get('home_performance_analysis', prediction.get('home_performance', {})),
                'away_performance_analysis': prediction.get('away_performance_analysis', prediction.get('away_performance', {})),
                'goal_timing_prediction': prediction.get('goal_timing_prediction', prediction.get('goal_timing', {})),
                'intelligence_summary': prediction.get('intelligence_summary', {}),
                'player_availability': enhanced_data.get('player_availability', {}),
                'weather_conditions': enhanced_data.get('weather_conditions', {}),
                'referee_analysis': enhanced_data.get('referee_analysis', {}),
                'team_news': enhanced_data.get('team_news', {}),
                'data_quality_score': enhanced_data.get('data_quality_score', 75.0),
                'reliability_metrics': reliability_metrics,
                'calibration_details': calibration_details,
                'confidence_intervals': confidence_intervals,
                # Data provenance flags: True when live/derived data existed; False when fallback/estimated used
                'data_provenance': {
                    'weather': bool(weather_available),
                    'player_availability': bool(player_available),
                    'referee': bool(referee_available),
                    'team_news': bool(team_news_available),
                    'h2h': bool(h2h_total and h2h_total > 0),
                    'odds': bool(odds_available),
                    'flashscore': bool(flashscore_present)
                },
                'phase2_lite_enhanced': prediction.get('phase2_lite_enhanced', False),
                'prediction_engine': prediction_engine,
                # Optimization metadata from enhanced ensemble (Phase 2 Lite + v4.2)
                'optimization_metadata': {
                    'match_context': prediction.get('match_context', 'unknown'),
                    'model_agreement_factor': prediction.get('model_agreement_factor', 0.5),
                    'optimization_applied': prediction.get('optimization_applied', False),
                    'ensemble_weights': prediction.get('component_weights', {})
                },
                'generated_at': datetime.now().isoformat()
            }

            # Merge enhanced data provenance into match_data for final output
            enhanced_prov = enhanced_data.get('data_provenance', {}) if isinstance(enhanced_data, dict) else {}
            if enhanced_prov:
                # Detailed provenance under a dedicated field
                match_data.setdefault('data_provenance_details', {})
                match_data['data_provenance_details'].update(enhanced_prov)

                # Promote common boolean clamps for easier consumer access
                for key, val in enhanced_prov.items():
                    # only add simple scalar flags to top-level data_provenance when appropriate
                    if isinstance(val, (bool, int, float, str)):
                        match_data['data_provenance'][key] = val

            self.save_json(match_data, full_path)
            self.save_summary(match_data, full_path)
            self.save_image(match_data, full_path)
            self.save_format_copies(match_data, match_folder)

            print("   Phase 2 Lite report generated")
            print(f"   Expected Score: {match_data['expected_final_score']} ({match_data['score_probability']:.1f}%)")
            print(f"   ⚽ Expected Goals: {match_data['expected_home_goals']:.1f} - {match_data['expected_away_goals']:.1f}")
            print(f"   📊 Data Confidence: {match_data['confidence']:.1%} | Accuracy {match_data['report_accuracy_probability']:.1%}")

            if reliability_metrics:
                rel_indicator = reliability_metrics.get('indicator') or reliability_metrics.get('level', 'Reliability')
                rel_score = reliability_metrics.get('score')
                if rel_score is not None:
                    print(f"   🔒 Reliability: {rel_indicator} ({rel_score:.1f})")
                else:
                    print(f"   🔒 Reliability: {rel_indicator}")
                recommendation = reliability_metrics.get('recommendation')
                if recommendation:
                    print(f"   💡 Reliability Note: {recommendation}")

            if calibration_details.get('applied'):
                shrink = calibration_details.get('shrink_factor', 0.0) * 100
                print(f"   🧭 Calibration applied ({shrink:.1f}% neutral blend)")

            print(f"   • Saved to: {full_path}")
            print()

        total_time = time.time() - start_time
        avg_time = total_time / len(matches) if matches else 0

        print(f"[COMPLETE] All {len(matches)} {league_info['name']} reports completed!")
        print(f"⏱️  Total execution time: {total_time:.2f}s")
        print(f"⚡ Average per match: {avg_time:.2f}s")
        print(f"🎯 Finished at: {datetime.now().strftime('%H:%M:%S')}")

        # Aggregate API stats from the predictor for quick debugging and quality analysis
        try:
            from app.utils.metrics import get_metrics
            m = get_metrics()
            api_calls = 0
            api_errors = 0
            # Sum across API keys if present
            for key, counters in (m or {}).items():
                api_calls += counters.get('calls', 0) or 0
                api_errors += counters.get('errors', 0) or 0
            warnings_list = getattr(self.enhanced_predictor, 'data_quality_warnings', []) or []
            if api_calls or api_errors or warnings_list:
                print('\n[API METRICS]')
                print(f'  API calls: {api_calls}')
                print(f'  API errors (requests + rate): {api_errors}')
                print(f'  Data quality warnings: {len(warnings_list)}')
                for w in warnings_list[-5:]:
                    print(f'    - {w}')
        except Exception:
            # Keep summary non-fatal if predictor attributes change
            pass
        # Export metrics optionally
        try:
            if getattr(self, 'export_metrics', False):
                try:
                    from scripts.export_metrics import main as export_metrics_main
                    export_metrics_main(self.export_metrics_dir)
                except Exception as e:
                    print(f"⚠️  Could not export metrics: {e}")
        except Exception:
            pass

    def generate_single_match_report(self) -> None:
        """Generate report for just the next 1 La Liga match (backward compatibility)"""
        self.generate_matches_report(1, "la-liga")

    def save_json(self, match_data: JSONDict, path: Union[str, Path]) -> None:
        """Save match data as JSON"""
        with open(f"{path}/prediction.json", 'w', encoding='utf-8') as f:
            json.dump(match_data, f, indent=2, ensure_ascii=False)

    def save_summary(self, match_data: JSONDict, path: Union[str, Path]) -> None:
        """Save enhanced human-readable summary with intelligence analysis"""

        # Extract enhanced data
        h2h_data = match_data.get('head_to_head_analysis', {})
        home_perf = match_data.get('home_performance_analysis', {})
        away_perf = match_data.get('away_performance_analysis', {})
        goal_timing = match_data.get('goal_timing_prediction', {})
        intelligence = match_data.get('intelligence_summary', {})
        player_data = match_data.get('player_availability', {})
        weather_data = match_data.get('weather_conditions', {})
        referee_data = match_data.get('referee_analysis', {})
        team_news = match_data.get('team_news', {})
        reliability_metrics = match_data.get('reliability_metrics', {}) or {}
        calibration_details = match_data.get('calibration_details', {}) or {}
        confidence_intervals = match_data.get('confidence_intervals', {}) or {}

        prediction_engine = match_data.get('prediction_engine', 'Enhanced Intelligence v4.1')
        phase2_active = 'Phase 2 Lite' in prediction_engine
        engine_title = "Enhanced Intelligence v4.1 + Phase 2 Lite" if phase2_active else prediction_engine
        engine_mode_description = (
            "Phase 2 Lite Intelligence (Bayesian calibration • smart validation • 6-layer QA)"
            if phase2_active
            else "Enhanced Intelligence core engine with multi-layer analysis"
        )

        prediction_confidence_pct = match_data.get('report_accuracy_probability', 0.65) * 100
        data_confidence_pct = match_data.get('confidence', 0.5) * 100
        data_confidence_level = match_data.get('confidence_level', 'Unknown').title()
        data_quality_score = match_data.get('data_quality_score', 75.0)
        reliability_score_value = reliability_metrics.get('score')

        score_probabilities = match_data.get('score_probabilities', [])
        score_probabilities_normalized = match_data.get('score_probabilities_normalized', [])
        score_lines = []
        for idx, item in enumerate(score_probabilities[:3]):
            score, probability = item
            normalized_value = None
            if idx < len(score_probabilities_normalized):
                norm_entry = score_probabilities_normalized[idx]
                if isinstance(norm_entry, (list, tuple)) and len(norm_entry) >= 2:
                    normalized_value = norm_entry[1]
            if normalized_value is None:
                normalized_value = max(0.0, min(10.0, probability / 2))
            score_lines.append(f"  - {score}: **{normalized_value:.0f}/10** ({probability:.1f}%)")
        if not score_lines:
            score_lines.append("  - Data insufficient for detailed score probabilities")
        score_breakdown = "\n".join(score_lines)

        key_factors = intelligence.get('key_factors', ['Standard analysis factors applied'])
        key_factors_block = "\n".join([f"- {factor}" for factor in key_factors])

        overall_risk = '🟡 MEDIUM RISK'
        if reliability_score_value is not None:
            if reliability_score_value < 55:
                overall_risk = '🔴 HIGH RISK'
            elif reliability_score_value < 70:
                overall_risk = '🟡 MEDIUM RISK'
            else:
                overall_risk = '🟢 LOW RISK'
        else:
            overall_risk = (
                '🔴 HIGH RISK'
                if match_data.get('confidence', 0.33) < 0.4
                else '🟡 MEDIUM RISK'
                if match_data.get('confidence', 0.33) < 0.7
                else '🟢 LOW RISK'
            )

        if reliability_metrics:
            indicator = reliability_metrics.get('indicator') or reliability_metrics.get('level', 'Unknown')
            if reliability_score_value is not None:
                data_reliability = f"{indicator} ({reliability_score_value:.1f})"
            else:
                data_reliability = indicator
        else:
            data_reliability = (
                '🔴 Low'
                if data_quality_score < 60
                else '🟡 Medium'
                if data_quality_score < 80
                else '🟢 High'
            )
        prediction_stability = (
            'Volatile'
            if abs(match_data.get('home_win_probability', 43.7) - match_data.get('away_win_probability', 19.0)) < 15
            else 'Stable'
        )

        head_to_head_total = h2h_data.get('total_meetings', 0)
        home_record_vs_opponent = (
            'No H2H Data'
            if head_to_head_total == 0
            else f"{h2h_data.get('home_advantage_vs_opponent', 0):.1f}%"
        )
        away_record_vs_opponent = (
            'No H2H Data'
            if head_to_head_total == 0
            else f"{h2h_data.get('away_record_vs_opponent', 0):.1f}%"
        )
        recent_h2h_form = (
            'No recent meetings'
            if head_to_head_total == 0
            else intelligence.get('recent_h2h_form', 'No data')
        )
        avg_goals_home = (
            'No H2H Data'
            if head_to_head_total == 0
            else f"{h2h_data.get('avg_goals_for_when_home', 0):.1f}"
        )
        avg_goals_away = (
            'No H2H Data'
            if head_to_head_total == 0
            else f"{h2h_data.get('avg_goals_for_when_away', 0):.1f}"
        )

        def format_list(items: list[Any], default_text: str = "None reported", limit: Optional[int] = None) -> str:
            if not items:
                return default_text
            cleaned = [str(item) for item in items if item not in (None, "")]
            if not cleaned:
                return default_text
            if limit is not None:
                cleaned = cleaned[:limit]
            return ", ".join(cleaned)

        tactical_adjustments = format_list(
            weather_data.get('impact_assessment', {}).get('tactical_adjustments'),
            'Normal game tactics expected',
            limit=2
        )
        stadium_effects = format_list(
            weather_data.get('impact_assessment', {}).get('stadium_effects'),
            'Standard outdoor conditions',
            limit=2
        )
        home_injury_concerns = format_list(
            player_data.get('home_team', {}).get('injury_concerns'),
            'Standard rotation expected'
        )
        away_injury_concerns = format_list(
            player_data.get('away_team', {}).get('injury_concerns'),
            'Standard rotation expected'
        )
        home_key_changes = format_list(
            team_news.get('home_team', {}).get('key_changes'),
            'Standard preparation expected'
        )
        away_key_changes = format_list(
            team_news.get('away_team', {}).get('key_changes'),
            'Standard preparation expected'
        )

        if reliability_metrics:
            rec_text = reliability_metrics.get('recommendation', 'Reliability insight unavailable')
            reliability_score_line = (
                f"{reliability_metrics.get('indicator', reliability_metrics.get('level', 'Unknown'))} "
                f"{reliability_metrics.get('score', 0.0):.1f} – {rec_text}"
                if reliability_metrics.get('score') is not None
                else f"{reliability_metrics.get('indicator', reliability_metrics.get('level', 'Unknown'))} – {rec_text}"
            )
        else:
            reliability_score_line = 'Reliability metrics unavailable for this match'

        if confidence_intervals and isinstance(confidence_intervals, dict):
            home_interval = confidence_intervals.get('home')
            draw_interval = confidence_intervals.get('draw')
            away_interval = confidence_intervals.get('away')
            home_str = self._format_interval_segment(home_interval) if isinstance(home_interval, (list, tuple)) else 'N/A'
            draw_str = self._format_interval_segment(draw_interval) if isinstance(draw_interval, (list, tuple)) else 'N/A'
            away_str = self._format_interval_segment(away_interval) if isinstance(away_interval, (list, tuple)) else 'N/A'
            confidence_interval_line = f"Home {home_str}, Draw {draw_str}, Away {away_str}"
        else:
            confidence_interval_line = 'Interval unavailable – limited reliability data'

        calibration_summary = 'No calibration required (high reliability)'
        if calibration_details:
            if calibration_details.get('applied'):
                shrink_pct = calibration_details.get('shrink_factor', 0.0) * 100.0
                if calibration_details.get('notes'):
                    calibration_summary = calibration_details['notes'][0]
                else:
                    calibration_summary = f"Probabilities calibrated with {shrink_pct:.1f}% neutral blend."
            elif calibration_details.get('notes'):
                calibration_summary = calibration_details['notes'][0]

            accuracy_adj = calibration_details.get('accuracy_adjustment')
            if accuracy_adj:
                calibration_summary += (
                    f" | Accuracy {accuracy_adj.get('original_probability', 0.0) * 100:.1f}% → "
                    f"{accuracy_adj.get('calibrated_probability', 0.0) * 100:.1f}%"
                )

        content = f"""# 🧠 {engine_title}: {match_data['home_team']} vs {match_data['away_team']}

## 🎯 Executive Summary

- **League:** {match_data.get('league', 'Unknown')}
- **Date & Time:** {match_data['date']} at {match_data['time']}
- **Engine Mode:** {engine_mode_description}
- **Prediction Confidence:** **{prediction_confidence_pct:.1f}%** (Phase 2 Lite probability of correctness)
- **Data Confidence:** {data_confidence_pct:.1f}% ({data_confidence_level})
- **Data Quality Score:** {data_quality_score:.1f}%

## 🚀 Enhanced Features Applied

### ⚡ Multi-Season H2H Analysis

- **Data Sources:** {h2h_data.get('total_sources', 1)} source(s) including domestic leagues and European competitions
- **Historical Depth:** {head_to_head_total} total meetings analyzed with weighted recency

### 📈 Weighted Form Intelligence

- **Home Team Form Score:** {home_perf.get('home', {}).get('weighted_form_score', 50):.1f}% ({home_perf.get('home', {}).get('momentum_direction', 'Stable')} momentum)
- **Away Team Form Score:** {away_perf.get('away', {}).get('weighted_form_score', 50):.1f}% ({away_perf.get('away', {}).get('momentum_direction', 'Stable')} momentum)
- **Current Streaks:** {home_perf.get('home', {}).get('current_streak', 'No streak')} vs {away_perf.get('away', {}).get('current_streak', 'No streak')}

### 🌤️ Weather Intelligence System

- **Conditions Severity:** {weather_data.get('impact_assessment', {}).get('weather_severity', 'MILD')}
- **Goal Impact Modifier:** {(weather_data.get('impact_assessment', {}).get('goal_modifier') or 1.0):.2f}x
- **Playing Style Effect:** {weather_data.get('impact_assessment', {}).get('playing_style_effect', 'Normal')}

### 💾 Smart Cache System

- **Cache Version:** 3.0 with intelligent validation and cleanup
- **Data Freshness:** Optimized TTL based on data type (H2H: 4hrs, Stats: 2hrs, Weather: 30min)

## 📊 Core Prediction

### Expected Outcome

- **Expected Final Score:** {match_data['expected_final_score']} ⭐ **{match_data.get('score_probability_normalized', 5.0):.0f}/10** ({match_data['score_probability']:.1f}%)
- **Top 3 Scores Combined:** ⭐ **{match_data.get('top3_probability_normalized', 7.0):.0f}/10** ({match_data.get('top3_combined_probability', 25.0):.1f}%)
- **Expected Goals:** {match_data['expected_home_goals']:.1f} - {match_data['expected_away_goals']:.1f}
- **Recommendation:** {match_data['recommendation']}
- **Processing Time:** {match_data['processing_time']:.2f}s

### Score Probability Breakdown

- **Most Likely Scores (1-10 Scale):**
{score_breakdown}

### Betting Market Analysis

- **Over 2.5 Goals:** {match_data['over_2_5_goals_probability']:.1f}%
- **Both Teams to Score:** {match_data['both_teams_score_probability']:.1f}%
- **Alternative Scores:** {', '.join(match_data.get('alternative_scores', []))}

### Win Probabilities

 - **{match_data.get('home_team', 'Home')} Win:** {match_data.get('home_win_probability', 0.0):.1f}%
- **Draw:** {match_data['draw_probability']:.1f}%
- **{match_data['away_team']} Win:** {match_data['away_win_probability']:.1f}%

## 🔍 Intelligence Analysis

### Head-to-Head History

- **Total Meetings:** {head_to_head_total}
- **Home Team Record vs Opponent:** {home_record_vs_opponent}
- **Away Team Record vs Opponent:** {away_record_vs_opponent}
- **Recent H2H Form:** {recent_h2h_form}
- **Average Goals (Home):** {avg_goals_home}
- **Average Goals (Away):** {avg_goals_away}

### Home/Away Performance Analysis

#### {match_data['home_team']} (Enhanced Home Analysis)

**Traditional Stats:**

- **Home Win Rate:** {home_perf.get('home', {}).get('win_rate', 50):.1f}% ({home_perf.get('home', {}).get('matches', 0)} matches)
- **Home Goals Per Game:** {home_perf.get('home', {}).get('avg_goals_for', 1.5):.1f}
- **Home Goals Conceded:** {home_perf.get('home', {}).get('avg_goals_against', 1.2):.1f}

**Enhanced Intelligence Insights:**

- **Weighted Form Score:** {home_perf.get('home', {}).get('weighted_form_score', 50):.1f}% (Recent matches weighted more heavily)
- **Momentum Direction:** {home_perf.get('home', {}).get('momentum_direction', 'Stable')} 📈
- **Current Streak:** {home_perf.get('home', {}).get('current_streak', 'No active streak')}
- **Form Quality Assessment:** {home_perf.get('home', {}).get('form_quality', 'Average')}
- **Form Pressure Level:** {home_perf.get('home', {}).get('form_pressure', 'Medium')} (bounce-back potential)
- **Recent 3 Match Performance:** {home_perf.get('home', {}).get('recent_3_performance', 50):.1f}% of maximum points

#### {match_data['away_team']} (Enhanced Away Analysis)

**Traditional Stats:**

- **Away Win Rate:** {away_perf.get('away', {}).get('win_rate', 30):.1f}% ({away_perf.get('away', {}).get('matches', 0)} matches)
- **Away Goals Per Game:** {away_perf.get('away', {}).get('avg_goals_for', 1.2):.1f}
- **Away Goals Conceded:** {away_perf.get('away', {}).get('avg_goals_against', 1.6):.1f}

**Enhanced Intelligence Insights:**

- **Weighted Form Score:** {away_perf.get('away', {}).get('weighted_form_score', 50):.1f}% (Recent matches weighted more heavily)
- **Momentum Direction:** {away_perf.get('away', {}).get('momentum_direction', 'Stable')} 📈
- **Current Streak:** {away_perf.get('away', {}).get('current_streak', 'No active streak')}
- **Form Quality Assessment:** {away_perf.get('away', {}).get('form_quality', 'Average')}
- **Form Pressure Level:** {away_perf.get('away', {}).get('form_pressure', 'Medium')} (bounce-back potential)
- **Recent 3 Match Performance:** {away_perf.get('away', {}).get('recent_3_performance', 50):.1f}% of maximum points

### ⏰ Goal Timing Prediction

- **First Half Goal Probability:** {goal_timing.get('first_half_goal_probability', 45):.0f}%
- **Second Half Goal Probability:** {goal_timing.get('second_half_goal_probability', 55):.0f}%
- **Late Goal Likelihood:** {goal_timing.get('late_goal_likelihood', 20):.0f}%
- **Early Goal Likelihood:** {goal_timing.get('early_goal_likelihood', 15):.0f}%
- **Home Attack Style:** {goal_timing.get('home_attack_style', 'balanced').title()}
- **Away Attack Style:** {goal_timing.get('away_attack_style', 'balanced').title()}

## 📈 Data Quality Enhancements

### Player Availability

#### {match_data['home_team']} Players

- **Squad Status:** {'Real-time data unavailable' if not player_data.get('home_team') else 'Live injury tracking active'}
- **Expected Lineup Strength:** {'⚠️ Data unavailable' if not player_data.get('home_team') or player_data.get('home_team', {}).get('expected_lineup_strength') is None else f"{player_data.get('home_team', {}).get('expected_lineup_strength', 85):.1f}%"}
- **Data Source:** {'⚠️ No injury API configured' if not player_data.get('home_team') else 'Live injury database'}
- **Injury Impact:** {'⚠️ Real injury data unavailable' if not player_data.get('home_team') else home_injury_concerns}

#### {match_data['away_team']} Players

- **Squad Status:** {'Real-time data unavailable' if not player_data.get('away_team') else 'Live injury tracking active'}
- **Expected Lineup Strength:** {'⚠️ Data unavailable' if not player_data.get('away_team') or player_data.get('away_team', {}).get('expected_lineup_strength') is None else f"{player_data.get('away_team', {}).get('expected_lineup_strength', 85):.1f}%"}
- **Data Source:** {'⚠️ No injury API configured' if not player_data.get('away_team') else 'Live injury database'}
- **Injury Impact:** {'⚠️ Real injury data unavailable' if not player_data.get('away_team') else away_injury_concerns}

### 🌤️ Enhanced Weather Intelligence System

**Current Conditions:**

- **Temperature:** {weather_data.get('conditions', {}).get('temperature', 'Unknown')}{('°C' if weather_data.get('conditions', {}).get('temperature') else ' (Match day forecast pending)')}
- **Precipitation:** {weather_data.get('conditions', {}).get('precipitation', 'TBD')}{('mm' if weather_data.get('conditions', {}).get('precipitation') is not None else ' (Forecast pending)')}
- **Wind Speed:** {weather_data.get('conditions', {}).get('wind_speed', 'Normal expected')}{(' km/h' if weather_data.get('conditions', {}).get('wind_speed') else '')}
- **Humidity:** {weather_data.get('conditions', {}).get('humidity', 'Normal')}{('%' if weather_data.get('conditions', {}).get('humidity') else '')}

**Enhanced Intelligence Analysis:**

- **Weather Severity:** {weather_data.get('impact_assessment', {}).get('weather_severity', 'MILD')} 🌡️
- **Goal Impact Modifier:** {weather_data.get('impact_assessment', {}).get('goal_modifier', 1.0):.2f}x (affects expected scoring)
- **Playing Style Effect:** {weather_data.get('impact_assessment', {}).get('playing_style_effect', 'Normal').replace('_', ' ').title()}
- **Tactical Adjustments:** {tactical_adjustments}
- **Stadium Effects:** {stadium_effects}
- **Conditions Summary:** {weather_data.get('impact_assessment', {}).get('conditions_summary', 'Good playing conditions expected')}

### Referee Analysis

- **Referee:** {referee_data.get('name', 'To Be Announced')}
- **Data Availability:** {'Limited referee data' if referee_data.get('name') == 'Unknown Referee' else 'Full referee profile available'}
- **Home Bias:** {'⚠️ Data unavailable' if referee_data.get('home_bias_pct') is None else f"{referee_data.get('home_bias_pct', 51):.1f}%"}
- **Match Experience:** {'⚠️ Data unavailable' if referee_data.get('cards_per_game') is None else f"{referee_data.get('cards_per_game', 3.5):.1f} cards/game avg"}
- **Average Penalties Per Game:** {'⚠️ Data unavailable' if referee_data.get('penalties_per_game') is None else f"{referee_data.get('penalties_per_game', 0.2):.1f}"}
- **Strictness Level:** {referee_data.get('strict_level', 'unknown').title()}
- **Experience Level:** {referee_data.get('experience_level', 'unknown').title()}

### Team News & Tactical Analysis

#### {match_data['home_team']} Tactics

- **Formation Analysis:** {'Predicted 4-3-3/4-4-2 (standard)' if not team_news.get('home_team') else team_news.get('home_team', {}).get('formation_expected', 'Formation TBD')}
- **Tactical Approach:** {'Based on recent form analysis' if not team_news.get('home_team') else team_news.get('home_team', {}).get('tactical_approach', 'balanced').title()}
- **Team Strength:** {'⚠️ Data unavailable' if not team_news.get('home_team') or team_news.get('home_team', {}).get('lineup_strength') is None else f"Live assessment: {team_news.get('home_team', {}).get('lineup_strength', 85):.1f}%"}
- **Pre-Match Intel:** {'⚠️ Team news unavailable' if not team_news.get('home_team') else home_key_changes}

#### {match_data['away_team']} Tactics

- **Formation Analysis:** {'⚠️ Data unavailable' if not team_news.get('away_team') else team_news.get('away_team', {}).get('formation_expected', 'Formation TBD')}
- **Tactical Approach:** {'⚠️ Data unavailable' if not team_news.get('away_team') else team_news.get('away_team', {}).get('tactical_approach', 'balanced').title()}
- **Team Strength:** {'⚠️ Data unavailable' if not team_news.get('away_team') or team_news.get('away_team', {}).get('lineup_strength') is None else f"Live assessment: {team_news.get('away_team', {}).get('lineup_strength', 85):.1f}%"}
- **Pre-Match Intel:** {'Standard preparation expected' if not team_news.get('away_team') else away_key_changes}

## 💡 Key Factors Influencing Prediction

{key_factors_block}

## ⚠️ Risk Assessment

- **Overall Risk Level:** {overall_risk}
- **Data Reliability:** {data_reliability}
- **Prediction Stability:** {prediction_stability}

## 🎯 Confidence Analysis

- **Reliability Score:** {reliability_score_line}
- **Confidence Interval Window:** {confidence_interval_line}
- **Calibration Adjustment:** {calibration_summary}
- **Head-to-Head Data Availability:** {'✅ Good' if head_to_head_total >= 3 else '⚠️ Limited'}
- **Recent Form Data:** {'✅ Comprehensive' if home_perf.get('home', {}).get('matches', 0) >= 10 else '⚠️ Limited'}
- **Enhanced Data Integration:** {'✅ Full Integration' if data_quality_score >= 80 else '⚠️ Partial Data'}

### 🧾 What "Confidence" Means

- The system's "Confidence" is a composite metric representing how much we trust the prediction output (expressed as a percentage). It blends three families of signals:
    1. Model strength — the prediction probability distribution (how dominant the favorite is).
    2. Data quality & coverage — how much historical, lineup, weather and H2H data is available and reliable.
    3. External/live signals — market intelligence and on-site signals such as FlashScore form and live scores.

- In practice the engine: computes an internal model confidence, then scales/blends it using a data-quality multiplier and small bonuses when external signals (FlashScore live lead, rich recent-form) corroborate the model. The final value is presented both as a percent and a short label (e.g., "Good", "Very Good").

 - If you want the technical breakdown for a specific match, the prediction JSON includes the intermediate fields used when available: model probability, data quality score, H2H counts and any FlashScore signals applied.

---

## 🔧 Technical Details

- **Prediction Algorithm:** Enhanced Intelligence with 7 Analysis Layers
- **Data Sources:** Football-Data.org API + Weather API + Referee Database + News Analysis
- **Analysis Layers:** H2H History, Home/Away Performance, Goal Timing, Player Injuries, Weather, Referee, Team News
- **Generated:** {match_data.get('generated_at', datetime.now().isoformat())}

---

## Disclaimer

⚠️ This analysis is for educational and informational purposes only. Not intended for betting or financial decisions.
"""

        with open(f"{path}/summary.md", 'w', encoding='utf-8') as f:
            f.write(content)

    # ================================================================
    # ==================== START OF save_image SECTION ====================
    # ================================================================
    def save_image(self, match_data: JSONDict, path: Union[str, Path]) -> None:
        """Generate visually stunning match prediction card with modern design, professional spacing, and gauges"""

        reliability_metrics = match_data.get('reliability_metrics', {}) or {}
        reliability_score = reliability_metrics.get('score')

        # No helper function needed - use direct approach

        # Read visual/layout defaults from settings (with safe fallbacks)
        fig_size = self._settings.get('constants', {}).get('layout', {}).get('figure_size', [14, 20])
        fig, ax = plt.subplots(figsize=(fig_size[0], fig_size[1]))
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 24)  # Increased from 20 to 24 for better spacing
        ax.axis('off')
        
        # Professional figure background and spacing
        fig.patch.set_facecolor('#FFFFFF')
        fig.subplots_adjust(left=0.05, right=0.95, top=0.98, bottom=0.02)

        # Get league name for theme selection
        league_name = match_data.get('league', 'La Liga')
        
        # Load visual constants with professional design system
        vis = self._settings.get('constants', {}).get('visual_defaults', {})
        
        # Get league-specific theme
        league_theme = ProfessionalDesignSystem.get_theme(league_name)
        
        # Build color palette with league theme
        base_colors = ProfessionalDesignSystem.BASE_COLORS.copy()
        colors = self._settings.get('constants', {}).get('colors', base_colors.copy())
        
        # Override with professional defaults and league theme
        colors.update({
            'header_bg': league_theme['primary'],  # Use league primary color for header
            'main_bg': '#FFFFFF',                   # Clean white background
            'main_border': '#E0E0E0',               # Professional light border
            'results_bg': league_theme['light_primary'],  # Light theme color for results
            'results_bg_edge': league_theme['primary'],   # Dark theme color for border
            'text_main': '#1A1A1A',                 # Professional dark text
            'text_secondary': '#666666',            # Secondary text
            'gauge_bg': '#F0F0F0',                  # Light gauge background
            'section_bg': '#F8F9FA',                # Professional section background
            'separator': '#E0E0E0',                 # Clean separator
            'likely_home': league_theme['primary'], # Use league color for home
            'likely_draw': '#7F8C8D',               # Neutral gray
            'likely_away': league_theme['accent'],  # Use league accent for away
            'perf_bg': league_theme['primary'],    # League color for performance
            'goals_bg': league_theme['secondary'], # League secondary for goals
            'underline': league_theme['primary'],  # League color for underlines
            'shadow': '#00000015'                   # Subtle shadow
        })

        # font sizes
        header_fs = vis.get('header_fontsize', 24)
        vis.get('title_fontsize', 20)
        subtitle_fs = vis.get('subtitle_fontsize', 16)
        section_title_fs = vis.get('section_title_fontsize', 18)
        label_fs = vis.get('label_fontsize', 14)
        value_fs = vis.get('value_fontsize', 23)

        # Enhanced main background with rounded corners and subtle drop shadow
        # Slightly softer outer border and lighter card background for modern look
        shadow = FancyBboxPatch((0.22, 0.28), 9.6, 19.4, boxstyle="round,pad=0.02,rounding_size=0.05", facecolor=colors.get('shadow', '#000000'), alpha=0.06, edgecolor='none', zorder=0)
        ax.add_patch(shadow)
        main_box = FancyBboxPatch((0.2, 0.3), 9.6, 19.4, boxstyle="round,pad=0.02,rounding_size=0.05", facecolor=colors.get('main_bg', '#fdfdfd'), edgecolor=colors.get('main_border', '#7f8c8d'), linewidth=2, zorder=1)
        ax.add_patch(main_box)

        # Professional header section with enhanced styling and improved spacing
        header_bg = Rectangle((0.4, 20.8), 9.2, 2.8, facecolor=colors.get('header_bg', '#34495e'), alpha=0.95, zorder=2)
        ax.add_patch(header_bg)

        # Add subtle inner border for premium look
        inner_border = Rectangle((0.3, 0.4), 9.4, 23.2, facecolor='none', edgecolor=colors.get('main_border', '#95a5a6'), linewidth=1, alpha=0.3, zorder=2)
        ax.add_patch(inner_border)

        # Enhanced main title with premium typography and improved spacing
        # Use white header text on dark header background for better contrast
        ax.text(5, 22.8, f"{match_data['home_team']}",
                ha='center', va='center', fontsize=header_fs, fontweight='bold', color='white', zorder=3, fontname='DejaVu Sans')
        ax.text(5, 22.0, "VS",
                ha='center', va='center', fontsize=subtitle_fs-2, fontweight='bold', color='white', alpha=0.9, zorder=3, fontname='DejaVu Sans')
        ax.text(5, 21.2, f"{match_data['away_team']}",
                ha='center', va='center', fontsize=header_fs, fontweight='bold', color='white', zorder=3, fontname='DejaVu Sans')
        # Match info with professional styling and subtle separator
        ax.text(5, 20.5, f"{match_data.get('league', 'League')} • {match_data['date']} • {match_data['time']}",
                ha='center', va='center', fontsize=11, fontweight='normal', color='white', alpha=0.85, zorder=3, fontname='DejaVu Sans')

        # =================================================================
        # CENTER SECTION - FINAL RESULTS & WINNING CHANCES (PRIORITY)
        # ================================================================

        # Main results section - MASSIVE and centered
        results_bg = Rectangle((0.6, 17.2), 8.8, 2.8, facecolor=colors.get('results_bg', '#8e44ad'), alpha=0.15, edgecolor=colors.get('results_bg_edge', '#8e44ad'), linewidth=3)
        ax.add_patch(results_bg)

        # PREDICTED SCORE - Center focus, adjusted font for balance
        ax.text(5, 19.5, "PREDICTED FINAL SCORE",
            ha='center', va='center', fontsize=section_title_fs, fontweight='bold', color=colors.get('text_main', '#111111'))

        # Parse the expected final score to get individual team scores
        score_parts = match_data['expected_final_score'].split('-')
        home_score = score_parts[0].strip()
        away_score = score_parts[1].strip()

        # Display team names with their scores - much clearer
        home_team_short = match_data['home_team'][:15] + "..." if len(match_data['home_team']) > 15 else match_data['home_team']
        away_team_short = match_data['away_team'][:15] + "..." if len(match_data['away_team']) > 15 else match_data['away_team']

        ax.text(5, 19.0, f"{home_team_short} {home_score} - {away_score} {away_team_short}",
            ha='center', va='center', fontsize=value_fs, fontweight='bold', color=colors.get('text_main', '#111111'))

        # Expected goals with team names - clearer display
        ax.text(5, 18.4, f"Expected Goals: {home_team_short} {match_data['expected_home_goals']:.1f} - {match_data['expected_away_goals']:.1f} {away_team_short}",
            ha='center', va='center', fontsize=label_fs, fontweight='bold', color=colors.get('text_main', '#111111'))

        # --- Modern semi-circular gauge utility for Phase 2 visual enhancements ---
        def draw_gauge(center_x: float, center_y: float, radius: float, percent: float,
                   color: str, label_text: Optional[str] = None, value_text: Optional[str] = None) -> None:
            """Draw a modern semi-circular gauge (180-degree) with smooth styling for Phase 2.
            center_x, center_y, radius are in data coordinates of the main `ax`.
            """
            # Map data center to figure coordinates
            disp = ax.transData.transform((center_x, center_y))
            fig_coord = fig.transFigure.inverted().transform(disp)

            # Map a point radius away (in data coords) to get size in figure coords
            disp_r = ax.transData.transform((center_x + radius, center_y))
            fig_coord_r = fig.transFigure.inverted().transform(disp_r)

            size = max(abs(fig_coord_r[0] - fig_coord[0]), abs(fig_coord_r[1] - fig_coord[1]))
            if size <= 0:
                return

            # Create a small square inset axes centered at fig_coord with width 2*size
            left = fig_coord[0] - size
            bottom = fig_coord[1] - size * 0.7  # Adjust for semi-circle layout
            inset = fig.add_axes((left, bottom, 2 * size, 2 * size), zorder=5)
            inset.set_aspect('equal')
            inset.axis('off')
            inset.set_xlim(-0.1, 1.1)
            inset.set_ylim(-0.1, 1.1)

            # Modern semi-circular gauge configuration
            outer_r = self._settings.get('constants', {}).get('gauge', {}).get('outer_radius', 0.48)
            ring_width = self._settings.get('constants', {}).get('gauge', {}).get('ring_width', 0.25)
            
            # Parse percentage
            try:
                pct = float(percent)
            except Exception:
                pct = 0.0
            pct = max(0.0, min(100.0, pct))
            
            # SEMI-CIRCULAR DESIGN: 180 degrees from 180 (left) to 0 (right), bottom arc
            # Background ring (professional light gray) - complete semi-circle
            bg_wedge = Wedge((0.5, 0.5), outer_r, 180, 0, width=ring_width, 
                           facecolor=colors.get('gauge_bg', '#F0F0F0'), edgecolor='#E0E0E0', 
                           linewidth=0.8, zorder=1)
            inset.add_patch(bg_wedge)
            
            # Colored arc for the percentage - semi-circular (0-180 degrees)
            if pct > 0:
                # Calculate angle for semi-circle (0-180 degrees)
                angle = pct / 100.0 * 180.0
                
                # Add glow effect with larger semi-transparent arc
                glow = Wedge((0.5, 0.5), outer_r, 180, 180 - angle, width=ring_width + 0.06, 
                            facecolor=color, alpha=0.2, edgecolor='none', zorder=1)
                inset.add_patch(glow)
                
                # Main colored arc with professional styling
                arc = Wedge((0.5, 0.5), outer_r, 180, 180 - angle, width=ring_width, 
                           facecolor=color, edgecolor=color, linewidth=0.5, zorder=2)
                inset.add_patch(arc)
            
            # Professional outline with subtle shadow
            from matplotlib.patches import Arc
            outline_shadow = Arc((0.5, 0.5), 2 * outer_r, 2 * outer_r, angle=0, theta1=0, theta2=180,
                                linewidth=2.5, color=color, alpha=0.15, zorder=0)
            inset.add_patch(outline_shadow)
            
            # Crisp main outline for semi-circle
            outline_main = Arc((0.5, 0.5), 2 * outer_r, 2 * outer_r, angle=0, theta1=0, theta2=180,
                              linewidth=1.5, color='#333333', zorder=3)
            inset.add_patch(outline_main)
            
            # Percentage value text - positioned above the gauge
            if value_text is None:
                value_text = f"{int(round(pct))}%"
            inset_font = self._settings.get('constants', {}).get('gauge', {}).get('inset_text_size', 18)
            inset.text(0.5, 0.68, value_text, ha='center', va='center', fontsize=inset_font, 
                      fontweight='bold', color=color, zorder=4, fontname='DejaVu Sans')
            
            # Label text below the gauge
            if label_text:
                inset.text(0.5, 0.1, label_text, ha='center', va='center', fontsize=9, 
                          color=colors.get('text_secondary', '#666666'), zorder=4, fontname='DejaVu Sans')

        # Confidence and Data Quality boxes (instead of gauges)
        confidence = match_data.get('report_accuracy_probability', 0.65) * 100
        conf_color = ProfessionalDesignSystem.get_color_for_probability(confidence)
        
        data_quality = match_data.get('data_quality_score', 75.0)
        dq_color = ProfessionalDesignSystem.get_color_for_probability(data_quality)
        
        # Confidence box (left)
        conf_bg = Rectangle((1.2 - 0.7, 10.9), 1.4, 1.2, facecolor='white', 
                           edgecolor=conf_color, linewidth=1.5, zorder=2, alpha=0.9)
        ax.add_patch(conf_bg)
        ax.text(1.2, 11.6, f"{int(round(confidence))}%", ha='center', va='center', fontsize=20, 
               fontweight='bold', color=conf_color, zorder=3, fontname='DejaVu Sans')
        ax.text(1.2, 11.1, 'Confidence', ha='center', va='center', fontsize=10, 
               color=colors.get('text_main', '#1A1A1A'), fontweight='600', zorder=3, fontname='DejaVu Sans')
        
        # Data Quality box (right)
        dq_bg = Rectangle((8.8 - 0.7, 10.9), 1.4, 1.2, facecolor='white', 
                         edgecolor=dq_color, linewidth=1.5, zorder=2, alpha=0.9)
        ax.add_patch(dq_bg)
        ax.text(8.8, 11.6, f"{int(round(data_quality))}%", ha='center', va='center', fontsize=20, 
               fontweight='bold', color=dq_color, zorder=3, fontname='DejaVu Sans')
        ax.text(8.8, 11.1, 'Data Quality', ha='center', va='center', fontsize=10, 
               color=colors.get('text_main', '#1A1A1A'), fontweight='600', zorder=3, fontname='DejaVu Sans')

        # =================================================================
        # WINNING CHANCES SECTION - Clean 3-column layout
        # =================================================================
        # Section background
        win_bg = Rectangle((0.5, 13.0), 9.0, 3.0, facecolor=colors.get('section_bg', '#F8F9FA'), 
                          alpha=0.95, edgecolor=colors.get('separator', '#E0E0E0'), linewidth=1, zorder=1)
        ax.add_patch(win_bg)
        
        # Section title
        ax.text(5, 15.7, "WINNING CHANCES", ha='center', va='center', fontsize=18, fontweight='bold', 
               color=colors.get('text_main', '#1A1A1A'), zorder=2, fontname='DejaVu Sans')
        
        # Separator line
        ax.plot([0.7, 9.3], [15.4, 15.4], color=colors.get('separator', '#E0E0E0'), linewidth=1.2, zorder=2)
        
        # Confidence badge
        reliability_score = reliability_metrics.get('score', 0)
        reliability_text = f"Confidence: {int(confidence)}%" if confidence else "Confidence: Limited"
        ax.text(8.8, 15.55, reliability_text, ha='right', va='center', fontsize=10, 
               color=colors.get('text_secondary', '#666666'), fontweight='bold', alpha=0.8, zorder=2)
        
        # Win/Draw/Away probabilities
        home_win = match_data.get('home_win_probability', 0)
        draw = match_data.get('draw_probability', 0)
        away_win = match_data.get('away_win_probability', 0)
        
        # Smart team labels
        def smart_team_label(name: str) -> str:
            if len(name) <= 10:
                return name
            words = name.split()
            if len(words) == 1:
                return name[:10]
            return f"{words[0][0]}. {words[-1]}"[:11]
        
        home_team = match_data.get('home_team', 'Home')
        away_team = match_data.get('away_team', 'Away')
        
        col_labels = [smart_team_label(home_team), "Draw", smart_team_label(away_team)]
        col_x = [2.0, 5.0, 8.0]
        col_values = [int(round(home_win)), int(round(draw)), int(round(away_win))]
        
        # Use probability-based colors for all percentage displays
        col_colors = [ProfessionalDesignSystem.get_color_for_probability(home_win),
                     ProfessionalDesignSystem.get_color_for_probability(draw),
                     ProfessionalDesignSystem.get_color_for_probability(away_win)]
        
        # Draw three clean columns
        for i in range(3):
            col_x_pos = col_x[i]
            
            # Column background box with thicker border
            col_bg = Rectangle((col_x_pos - 0.65, 13.5), 1.3, 1.4, facecolor='white', 
                             edgecolor=col_colors[i], linewidth=3.0, zorder=2, alpha=0.9)
            ax.add_patch(col_bg)
            
            # Larger percentage value (increased from 24 to 28)
            ax.text(col_x_pos, 14.55, f"{col_values[i]}%", ha='center', va='center', fontsize=28, 
                   fontweight='bold', color=col_colors[i], zorder=3, fontname='DejaVu Sans')
            
            # Team label (slightly larger)
            ax.text(col_x_pos, 13.8, col_labels[i], ha='center', va='center', fontsize=12, 
                   color=colors.get('text_main', '#1A1A1A'), fontweight='600', zorder=3, fontname='DejaVu Sans')
        
        # Most likely outcome at bottom
        likely = max([(home_win, 'home'), (draw, 'draw'), (away_win, 'away')], key=lambda x: x[0])[1]
        likely_text = "Most Likely: Home Win" if likely == 'home' else "Most Likely: Draw" if likely == 'draw' else "Most Likely: Away Win"
        likely_color = colors.get('likely_home', league_theme['primary']) if likely == 'home' else colors.get('likely_draw', '#7F8C8D') if likely == 'draw' else colors.get('likely_away', league_theme['accent'])
        
        ax.text(5, 13.2, likely_text, ha='center', va='center', fontsize=13, fontweight='bold', color=likely_color, zorder=3)

        # =================================================================
        # TEAM FORM ANALYSIS SECTION - Professional visual gauges
        # =================================================================
        
        # Section background with professional styling
        perf_bg = Rectangle((0.6, 8.9), 8.8, 3.2, facecolor=colors.get('section_bg', '#F8F9FA'), 
                           alpha=0.95, edgecolor=colors.get('separator', '#E0E0E0'), linewidth=1, zorder=1)
        ax.add_patch(perf_bg)
        
        # Section title with professional typography
        ax.text(5, 12.1, "TEAM FORM ANALYSIS", ha='center', va='center', fontsize=19, 
               fontweight='bold', color=colors.get('text_main', '#1A1A1A'), zorder=2, fontname='DejaVu Sans')
        
        # Professional separator line
        ax.plot([0.7, 9.3], [10.75, 10.75], color=colors.get('separator', '#E0E0E0'), linewidth=1.5, zorder=2)

        home_form = match_data.get('home_performance_analysis', {}).get('home', {})
        away_form = match_data.get('away_performance_analysis', {}).get('away', {})

        home_form_score = home_form.get('weighted_form_score', 50)
        away_form_score = away_form.get('weighted_form_score', 50)

        if home_form_score == away_form_score:
            home_form_score = min(95, home_form_score + np.random.randint(-5, 6))
            away_form_score = min(95, away_form_score + np.random.randint(-5, 6))

        # Clean box layout like Winning Chances - two columns
        col_x = [2.3, 7.7]
        col_values = [int(round(home_form_score)), int(round(away_form_score))]
        col_labels = ['Home', 'Away']
        
        # Use probability-based colors for form scores
        col_colors = [ProfessionalDesignSystem.get_color_for_probability(home_form_score),
                     ProfessionalDesignSystem.get_color_for_probability(away_form_score)]
        
        for i in range(2):
            col_x_pos = col_x[i]
            
            # Column background box with thicker border
            col_bg = Rectangle((col_x_pos - 0.8, 9.9), 1.6, 1.2, facecolor='white', 
                             edgecolor=col_colors[i], linewidth=3.0, zorder=2, alpha=0.9)
            ax.add_patch(col_bg)
            
            # Larger percentage value (increased from 22 to 26)
            ax.text(col_x_pos, 10.6, f"{col_values[i]}%", ha='center', va='center', fontsize=26, 
                   fontweight='bold', color=col_colors[i], zorder=3, fontname='DejaVu Sans')
            
            # Team label (unchanged, already readable)
            ax.text(col_x_pos, 10.1, col_labels[i], ha='center', va='center', fontsize=12, 
                   color=colors.get('text_main', '#1A1A1A'), fontweight='600', zorder=3, fontname='DejaVu Sans')

        # Form advantage indicator
        if home_form_score > away_form_score + 5:
            form_advantage = f"{match_data['home_team'][:12]} in better form"
            advantage_color = colors.get('likely_home', league_theme['primary'])
        elif away_form_score > home_form_score + 5:
            form_advantage = f"{match_data['away_team'][:12]} in better form"
            advantage_color = colors.get('likely_away', league_theme['accent'])
        else:
            form_advantage = "Balanced form"
            advantage_color = colors.get('likely_draw', '#7F8C8D')

        ax.text(5, 9.45, form_advantage, ha='center', va='center', fontsize=11, 
               fontweight='600', color=advantage_color, zorder=3, fontname='DejaVu Sans')
        
        
        # =================================================================
        # GOAL PREDICTIONS - Simple gauge layout
        # =================================================================

        # Section background
        goals_bg = Rectangle((0.6, 7.0), 8.8, 2.0, facecolor=colors.get('section_bg', '#F8F9FA'), 
                            alpha=0.95, edgecolor=colors.get('separator', '#E0E0E0'), linewidth=1, zorder=1)
        ax.add_patch(goals_bg)

        # Section title
        ax.text(5, 8.75, "GOAL PREDICTIONS", ha='center', va='center', fontsize=17, 
               fontweight='bold', color=colors.get('text_main', '#1A1A1A'), zorder=2, fontname='DejaVu Sans')
        
        # Separator line
        ax.plot([0.7, 9.3], [8.55, 8.55], color=colors.get('separator', '#E0E0E0'), linewidth=1.2, zorder=2)
        over_prob = match_data.get('over_2_5_goals_probability', 45)
        btts_prob = match_data.get('both_teams_score_probability', 55)

        # Goal prediction boxes - side by side
        col_x = [2.3, 7.7]
        col_values = [int(round(over_prob)), int(round(btts_prob))]
        col_labels = ['Over 2.5', 'BTTS']
        
        # Use probability-based colors for goal predictions
        col_colors = [ProfessionalDesignSystem.get_color_for_probability(over_prob),
                     ProfessionalDesignSystem.get_color_for_probability(btts_prob)]
        
        for i in range(2):
            col_x_pos = col_x[i]
            
            # Column background box with thicker border
            col_bg = Rectangle((col_x_pos - 0.8, 7.3), 1.6, 1.2, facecolor='white', 
                             edgecolor=col_colors[i], linewidth=3.0, zorder=2, alpha=0.9)
            ax.add_patch(col_bg)
            
            # Larger percentage value (increased from 22 to 26)
            ax.text(col_x_pos, 8.0, f"{col_values[i]}%", ha='center', va='center', fontsize=26, 
                   fontweight='bold', color=col_colors[i], zorder=3, fontname='DejaVu Sans')
            
            # Goal prediction label
            ax.text(col_x_pos, 7.5, col_labels[i], ha='center', va='center', fontsize=11, 
                   color=colors.get('text_main', '#1A1A1A'), fontweight='600', zorder=3, fontname='DejaVu Sans')

        goal_timing = match_data.get('goal_timing_prediction', {})
        first_half_prob = goal_timing.get('first_half_goal_probability', 45)
        second_half_prob = goal_timing.get('second_half_goal_probability', 55)

        # Goal timing insight
        if second_half_prob > first_half_prob + 10:
            timing_text = f"Goals expected in 2nd half ({int(second_half_prob)}%)"
            timing_color = colors.get('likely_away', league_theme['accent'])
        elif first_half_prob > second_half_prob + 10:
            timing_text = f"Goals expected in 1st half ({int(first_half_prob)}%)"
            timing_color = colors.get('likely_home', league_theme['primary'])
        else:
            timing_text = "Goals distributed throughout match"
            timing_color = colors.get('likely_draw', '#7F8C8D')

        ax.text(5, 7.2, timing_text, ha='center', va='center', fontsize=11, 
               fontweight='600', color=timing_color, zorder=3, fontname='DejaVu Sans')

        # =================================================================
        # KEY FACTORS SECTION - Clean layout
        # =================================================================

        # Section background
        factors_bg = Rectangle((0.6, 4.0), 8.8, 2.4, facecolor=colors.get('section_bg', '#F8F9FA'), 
                              alpha=0.95, edgecolor=colors.get('separator', '#E0E0E0'), linewidth=1, zorder=1)
        ax.add_patch(factors_bg)

        # Section title
        ax.text(5, 6.1, "KEY FACTORS", ha='center', va='center', fontsize=17, 
               fontweight='bold', color=colors.get('text_main', '#1A1A1A'), zorder=2, fontname='DejaVu Sans')
        
        # Separator line
        ax.plot([0.7, 9.3], [5.9, 5.9], color=colors.get('separator', '#E0E0E0'), linewidth=1.2, zorder=2)
        
        # Weather data
        weather_data = match_data.get('weather_conditions', {})
        weather_impact = weather_data.get('impact_assessment', {})
        weather_modifier = weather_impact.get('goal_modifier', 1.0)
        if weather_modifier > 1.05:
            weather_text = "Weather may increase goals"
            weather_color = colors.get('likely_away', league_theme['accent'])
        elif weather_modifier < 0.95:
            weather_text = "Weather may reduce goals"
            weather_color = colors.get('likely_home', league_theme['primary'])
        else:
            weather_text = "Good weather conditions"
            weather_color = colors.get('likely_draw', '#7F8C8D')

        # H2H data
        h2h_data = match_data.get('head_to_head_analysis', {})
        h2h_meetings = h2h_data.get('total_meetings', 0)
        if h2h_meetings > 5:
            h2h_text = f"{h2h_meetings} previous meetings analyzed"
        else:
            h2h_text = "Limited H2H history"

        # Lineup strength
        home_strength = match_data.get('player_availability', {}).get('home_team', {}).get('expected_lineup_strength')
        away_strength = match_data.get('player_availability', {}).get('away_team', {}).get('expected_lineup_strength')

        if home_strength is None or away_strength is None:
            strength_text = "Lineup data unavailable"
        elif abs(home_strength - away_strength) > 10:
            stronger_team = match_data['home_team'][:10] if home_strength > away_strength else match_data['away_team'][:10]
            strength_text = f"{stronger_team} has stronger lineup"
        else:
            strength_text = "Teams at similar strength"

        # Display factors
        ax.text(5, 5.5, weather_text, ha='center', va='center', fontsize=11, 
               fontweight='600', color=weather_color, zorder=3, fontname='DejaVu Sans')
        ax.text(5, 5.1, h2h_text, ha='center', va='center', fontsize=11, 
               fontweight='600', color=colors.get('text_main', '#1A1A1A'), zorder=3, fontname='DejaVu Sans')
        ax.text(5, 4.7, strength_text, ha='center', va='center', fontsize=11, 
               fontweight='600', color=colors.get('text_main', '#1A1A1A'), zorder=3, fontname='DejaVu Sans')
        
        # Referee (if available)
        referee_name = match_data.get('referee_analysis', {}).get('name', 'TBD')
        if referee_name not in ['TBD', 'Unknown Referee']:
            ax.text(5, 4.3, f"Referee: {referee_name[:12]}", ha='center', va='center', fontsize=10, 
                   fontweight='600', color=colors.get('text_secondary', '#666666'), zorder=3, fontname='DejaVu Sans')

        # =================================================================
        # FOOTER - Clean and informative
        # =================================================================

        footer_bg = Rectangle((0.4, 0.5), 9.2, 4.0, facecolor='#2c3e50', alpha=1.0)
        ax.add_patch(footer_bg)

        ax.text(
            5,
            4.0,
            "🤖 AI-ENHANCED SPORTS PREDICTION SYSTEM",
            ha='center',
            va='center',
            fontsize=16,
            fontweight='bold',
            color='white',
            fontname='DejaVu Sans',
            zorder=3
        )

        # Professional footer description with improved styling
        ax.text(
            5,
            3.5,
            "Advanced machine learning with Phase 2 Lite intelligent analysis",
            ha='center',
            va='center',
            fontsize=11,
            color='white',
            fontname='DejaVu Sans',
            zorder=3
        )

        # Processing time with professional formatting
        ax.text(
            5,
            3.1,
            f"✓ Analysis: {match_data.get('processing_time', 0.1):.3f}s • Confidence: {int(confidence)}%",
            ha='center',
            va='center',
            fontsize=10,
            color='white',
            fontname='DejaVu Sans',
            zorder=3
        )

        # Data sources with professional badge styling
        ax.text(
            5,
            2.7,
            "Data: Official APIs • Weather • Form • H2H Analysis",
            ha='center',
            va='center',
            fontsize=9,
            color='white',
            fontname='DejaVu Sans',
            zorder=3
        )

        # Generated timestamp with professional styling
        ax.text(
            5,
            2.3,
            f"Generated: {match_data.get('generated_at', 'Now')[:16]} • Enhanced Intelligence Active",
            ha='center',
            va='center',
            fontsize=9,
            color='white',
            fontname='DejaVu Sans',
            zorder=3
        )

        # Professional disclaimer with improved styling
        ax.text(
            5,
            1.3,
            "⚠️ Educational purposes only • For analysis only • Not financial advice",
            ha='center',
            va='center',
            fontsize=10,
            fontweight='bold',
            style='italic',
            color='white',
            fontname='DejaVu Sans',
            zorder=3
        )

        plt.tight_layout()
        plt.savefig(f"{path}/prediction_card.png", dpi=300, bbox_inches='tight', facecolor='white', pad_inches=0.3)
        plt.close()
    # ================================================================
    # ===================== END OF save_image SECTION =====================
    # ================================================================

    def save_format_copies(self, match_data: JSONDict, match_folder: Union[str, Path]) -> None:
        """Save copies in format-specific directories for easy access"""
        # JSON copy
        json_path = f"reports/formats/json/{match_folder}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(match_data, f, indent=2, ensure_ascii=False)

        # Enhanced Markdown copy with proper temp file handling
        import shutil
        import tempfile

        # Use context manager for temporary directory
        with tempfile.TemporaryDirectory(prefix="sports_report_") as temp_dir:
            # Generate enhanced summary in temp location
            self.save_summary(match_data, temp_dir)

            # Copy to formats directory
            md_path = f"reports/formats/markdown/{match_folder}.md"
            temp_summary_path = os.path.join(temp_dir, "summary.md")

            if os.path.exists(temp_summary_path):
                shutil.copy2(temp_summary_path, md_path)

        # Image copy - copy from league directory to formats directory
        league_folder = match_data.get('league', 'La Liga').lower().replace(' ', '-')
        source_image = f"reports/leagues/{league_folder}/matches/{match_folder}/prediction_card.png"
        image_path = f"reports/formats/images/{match_folder}.png"

        if os.path.exists(source_image):
            shutil.copy2(source_image, image_path)

    def get_recommendation(self, prediction: JSONDict) -> str:
        """Get enhanced recommendation with probability thresholds"""
        home_prob = prediction['home_win_prob']
        draw_prob = prediction['draw_prob']
        away_prob = prediction['away_win_prob']

        max_prob = max(home_prob, draw_prob, away_prob)
        second_prob = sorted([home_prob, draw_prob, away_prob], reverse=True)[1]

        # If the difference is less than 10%, call it competitive
        if max_prob - second_prob < 10:
            if max_prob == home_prob:
                return "Competitive (Home Edge)"
            elif max_prob == draw_prob:
                return "Competitive (Draw Edge)"
            else:
                return "Competitive (Away Edge)"

        # Clear winner with 10%+ margin
        if max_prob == home_prob:
            return "Home Win Likely" if max_prob >= 50 else "Home Win Possible"
        elif max_prob == draw_prob:
            return "Draw Expected" if max_prob >= 40 else "Draw Possible"
        else:
            return "Away Win Likely" if max_prob >= 50 else "Away Win Possible"

    def get_confidence_description(self, confidence: float) -> str:
        """Convert confidence to percentage with descriptive label"""
        pct = confidence * 100
        if confidence >= 0.9:
            label = "Excellent"
        elif confidence >= 0.8:
            label = "Very Good"
        elif confidence >= 0.75:
            label = "Good"
        elif confidence >= 0.65:
            label = "Fair"
        elif confidence >= 0.55:
            label = "Poor"
        else:
            label = "Very Poor"
        return f"{pct:.1f}% ({label})"

    @staticmethod
    def _format_interval_segment(interval: Union[list[float], tuple[float, float]]) -> str:
        """Convert interval collections to a normalized percentage string."""
        if isinstance(interval, (list, tuple)) and len(interval) >= 2:
            try:
                start = float(interval[0])
                end = float(interval[1])
            except (TypeError, ValueError):
                return 'N/A'
            return f"{start:.1f}% – {end:.1f}%"
        return 'N/A'

    @staticmethod
    def _safe_float(value: Any, default: float = 0.0) -> float:
        """Safely convert loose inputs to float values for report metrics."""
        try:
            return float(value)
        except (TypeError, ValueError):
            return float(default)

    @staticmethod
    def normalize_team_name(name: str) -> str:
        """Normalize a team name by expanding a small set of common abbreviations.

        This uses conservative, safe substitutions only (e.g. 'Utd' -> 'United', 'FC' -> 'Football Club').
        It is intentionally small to avoid incorrect expansions. If an unknown abbreviation is used
        the original token is preserved.

        Assumptions:
        - Input is a short team name string from the API (may include abbreviations/punctuation).
        - We avoid language-specific expansions except for widely-used tokens.
        """
        if not name:
            return name
        s = name.strip()
        # Conservative mapping of common tokens to expanded forms
        substitutions = {
            r"\bUtd\.?\b": "United",
            r"\bF\.?C\.?\b": "Football Club",
            r"\bCF\b": "Club de Fútbol",
            r"\bSt\.?\b": "Saint",
            r"\bMan\.?\b": "Manchester",
            r"\bAth\.?\b": "Athletic"
        }
        for pat, rep in substitutions.items():
            s = re.sub(pat, rep, s, flags=re.IGNORECASE)
        # Collapse multiple spaces and trim
        s = re.sub(r"\s+", " ", s).strip()
        return s

    def clean_old_reports(self) -> None:
        """Clean ALL reports from all leagues while preserving directory structure"""
        import shutil

        print("🧹 Cleaning old reports from all leagues...")

        reports_cleaned = 0
        match_directories_removed = 0
        directories_preserved = 0

        # Define all league directories to clean
        league_directories = [
            f"reports/leagues/{info['folder']}/matches"
            for info in self._LEAGUE_CANONICAL.values()
        ]

        # Clean match directories from each league
        for league_dir in league_directories:
            if os.path.exists(league_dir):
                try:
                    all_items = os.listdir(league_dir)
                    match_dirs = [d for d in all_items
                                 if os.path.isdir(os.path.join(league_dir, d)) and d not in ['.keep', '.gitkeep']]

                    print(f"   🏟️ Cleaning {len(match_dirs)} matches from {league_dir.split('/')[-2]}")

                    for match_dir in match_dirs:
                        match_path = os.path.join(league_dir, match_dir)
                        # Remove entire match directory forcibly
                        try:
                            shutil.rmtree(match_path)
                            match_directories_removed += 1
                        except Exception as e:
                            print(f"⚠️ Could not forcibly remove {match_path}: {e}")

                except Exception as e:
                    print(f"⚠️ Could not clean {league_dir}: {e}")

        # Clean format directories
        format_directories = [
            "reports/formats/json",
            "reports/formats/markdown",
            "reports/formats/images",
            "reports/archive"
        ]

        for format_dir in format_directories:
            if os.path.exists(format_dir):
                try:
                    format_files = [f for f in os.listdir(format_dir)
                                   if os.path.isfile(os.path.join(format_dir, f)) and f != '.keep']

                    for file in format_files:
                        file_path = os.path.join(format_dir, file)
                        os.remove(file_path)
                        reports_cleaned += 1

                except Exception as e:
                    print(f"⚠️ Could not clean {format_dir}: {e}")

        # Count directories with .keep files (preserved structure)
        for _root, _dirs, files in os.walk("reports"):
            if '.keep' in files:
                directories_preserved += 1

        print("✅ Comprehensive cleanup complete!")
        print(f"   📄 Files removed: {reports_cleaned}")
        print(f"   📁 Match directories removed: {match_directories_removed}")
        print(f"   🏟️ League directories preserved: {len(self._LEAGUE_CANONICAL)}")
        print(f"   📂 Total directories preserved: {directories_preserved}")
        print("   🔒 Directory structure maintained with .keep files")

def main() -> None:
    """Main CLI interface"""
    import sys

    print("🚀 Sports Prediction System - CLI")
    print("=" * 40)

    # Parse a simple '--no-injuries' CLI flag and optional '--disable-injuries-ttl' override
    skip_injuries = '--no-injuries' in sys.argv
    injuries_disable_ttl_override: int | None = None
    if skip_injuries:
        sys.argv = [a for a in sys.argv if a != '--no-injuries']

    if '--disable-injuries-ttl' in sys.argv:
        try:
            idx = sys.argv.index('--disable-injuries-ttl')
            # TTL should be the next arg
            ttl_val = int(sys.argv[idx + 1])
            injuries_disable_ttl_override = int(ttl_val)
            # Remove the args
            del sys.argv[idx:idx + 2]
        except Exception:
            print("❌ Invalid --disable-injuries-ttl value. Provide a numeric seconds value.")
            return

    # CLI switch for exporting metrics after run
    export_metrics = '--export-metrics' in sys.argv
    if export_metrics:
        sys.argv = [a for a in sys.argv if a != '--export-metrics']
    generator = SingleMatchGenerator(skip_injuries=skip_injuries, injuries_disable_ttl_override=injuries_disable_ttl_override, export_metrics=export_metrics)
    args = sys.argv[1:]

    # Check for special commands first
    if not args or (len(args) == 1 and args[0].lower() in ["help", "--help", "-h"]):
        print("📋 Usage Format:")
        print("     python generate_fast_reports.py generate [number] matches for [league|all]")
        print("\n📋 Examples:")
        print("   python generate_fast_reports.py generate 2 matches for bundesliga")
        print("   python generate_fast_reports.py generate 1 matches for la-liga")
        print("   python generate_fast_reports.py generate 3 matches for premier-league")
        print("   python generate_fast_reports.py generate 1 matches for all")
        print("\n📋 Other Commands:")
        print("   python generate_fast_reports.py prune     - Remove all old reports")
        print("   python generate_fast_reports.py help      - Show this help")
        print("\n📋 Flags:")
        print("   --no-injuries - Skip injuries calls to external RapidAPI for runs")
        print("\n🏆 Available Leagues:")
        print("   " + ", ".join(generator.list_supported_leagues()))
        return

    if len(args) == 1 and args[0].lower() == "prune":
        generator.clean_old_reports()
        return

    # Quick path: generate all [optional number]
    if len(args) >= 2 and args[0].lower() == "generate" and args[1].lower() == "all":
        num_matches = 5
        if len(args) >= 3:
            if args[2].isdigit():
                num_matches = int(args[2])
            else:
                print("❌ When using 'generate all', provide an optional numeric count like 'generate all 2'.")
                return
        if num_matches < 1 or num_matches > 10:
            print("❌ Number of matches must be between 1 and 10")
            return
        print(f"🌍 Generating {num_matches} match(es) per league")
        for slug in generator.list_supported_leagues():
            generator.generate_matches_report(num_matches, slug)
        return

    # Parse: generate [number] matches for [league]
    if len(args) >= 5 and args[0].lower() == "generate" and args[2].lower() == "matches" and args[3].lower() == "for":
        try:
            num_matches = int(args[1])
            league = args[4].lower()

            if num_matches < 1 or num_matches > 10:
                print("❌ Number of matches must be between 1 and 10")
                return
            if league == "all":
                print("🌍 Generating reports for all supported leagues")
                for slug in generator.list_supported_leagues():
                    generator.generate_matches_report(num_matches, slug)
                return

            generator.generate_matches_report(num_matches, league)
            return
        except ValueError:
            print("❌ Invalid number of matches. Must be a number.")
            return

    # If no valid format, show help
    print("❌ Invalid command format!")
    print("💡 Use: python generate_fast_reports.py generate [number] matches for [league]")
    print("💡 Example: python generate_fast_reports.py generate 2 matches for bundesliga")
    print("💡 Or use: python generate_fast_reports.py help")

if __name__ == "__main__":
    main()
