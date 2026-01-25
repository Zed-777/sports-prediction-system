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
from datetime import datetime, timedelta
from pathlib import Path

import matplotlib.pyplot as plt
from app.utils.http import safe_request_get
import yaml
from matplotlib.patches import FancyBboxPatch, Rectangle
from typing import Any, Dict, Optional, List, Union, cast
from app.types import JSONDict

# Suppress font warnings for cleaner output
warnings.filterwarnings("ignore", category=UserWarning, message=".*missing from font.*")


# Safe print helper: avoid UnicodeEncodeError on consoles that don't support emojis
def safe_print(*args, **kwargs):
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        # Remove non-ASCII characters as a fallback
        new_args = []
        for a in args:
            if isinstance(a, str):
                new_args.append("".join(ch for ch in a if ord(ch) < 128))
            else:
                new_args.append(a)
        print(*new_args, **kwargs)


CURRENT_DIR = Path(__file__).parent

# ============================================================================
# PROFESSIONAL DESIGN SYSTEM FOR SPORTS CARDS
# ============================================================================


class ProfessionalDesignSystem:
    """Professional design system for sports analytics cards"""

    # League-specific color themes for premium appearance
    LEAGUE_THEMES = {
        "la-liga": {
            "primary": "#003DA5",  # Royal Blue
            "secondary": "#FFD700",  # Gold
            "accent": "#8B0000",  # Deep Crimson
            "light_primary": "#E6F0FF",  # Light blue for backgrounds
        },
        "premier-league": {
            "primary": "#004CD4",  # Royal Blue
            "secondary": "#FFD700",  # Gold
            "accent": "#1F1F1F",  # Dark Charcoal
            "light_primary": "#E6F2FF",
        },
        "serie-a": {
            "primary": "#003A70",  # Deep Blue
            "secondary": "#CE1126",  # Red
            "accent": "#FFFFFF",  # White
            "light_primary": "#E6F0FF",
        },
        "bundesliga": {
            "primary": "#000000",  # Black
            "secondary": "#F4B942",  # Gold
            "accent": "#DD0000",  # Red
            "light_primary": "#F5F5F5",
        },
        "ligue-1": {
            "primary": "#002D5D",  # Navy Blue
            "secondary": "#F7A600",  # Gold
            "accent": "#EF3B39",  # Red
            "light_primary": "#E6F0FF",
        },
    }

    # Professional color palette
    BASE_COLORS = {
        "header_bg": "#1a1a1a",
        "main_bg": "#FFFFFF",
        "main_border": "#D0D0D0",
        "section_bg": "#F8F9FA",
        "text_main": "#1a1a1a",
        "text_secondary": "#666666",
        "text_light": "#999999",
        "gauge_bg": "#E8E8E8",
        "separator": "#E0E0E0",
        "shadow": "#000000",
        "success": "#27AE60",
        "warning": "#F39C12",
        "danger": "#E74C3C",
    }

    @classmethod
    def get_theme(cls, league_name: str) -> Dict[str, str]:
        """Get theme colors for league"""
        # Normalize league name
        normalized = league_name.lower().replace(" ", "-")
        return cls.LEAGUE_THEMES.get(normalized, cls.LEAGUE_THEMES["la-liga"])

    @classmethod
    def get_color_for_probability(cls, probability: float) -> str:
        """Get color gradient for probability: 0-25% red, 25-50% orange, 50-75% cyan, 75-100% green"""
        p = max(0.0, min(100.0, probability))
        if p >= 75:
            return "#27AE60"  # Green - 75-100%
        elif p >= 50:
            return "#17A2B8"  # Cyan - 50-75% (highly visible)
        elif p >= 25:
            return "#F39C12"  # Orange - 25-50%
        else:
            return "#E74C3C"  # Red - 0-25%

    # Professional typography system for consistent styling
    TYPOGRAPHY = {
        "title": {"size": 26, "weight": "bold", "font": "DejaVu Sans"},
        "heading": {"size": 19, "weight": "bold", "font": "DejaVu Sans"},
        "subheading": {"size": 14, "weight": "bold", "font": "DejaVu Sans"},
        "label": {"size": 12, "weight": "bold", "font": "DejaVu Sans"},
        "value": {"size": 23, "weight": "bold", "font": "DejaVu Sans"},
        "body": {"size": 11, "weight": "normal", "font": "DejaVu Sans"},
        "small": {"size": 10, "weight": "normal", "font": "DejaVu Sans"},
    }

    @classmethod
    def apply_text(
        cls,
        ax,
        text: str,
        x: float,
        y: float,
        style: str = "body",
        color: str = None,
        zorder: int = 1,
        **kwargs,
    ) -> None:
        """Apply typography with consistent professional styling."""
        if style not in cls.TYPOGRAPHY:
            style = "body"
        typo = cls.TYPOGRAPHY[style]

        if color is None:
            color = cls.BASE_COLORS["text_main"]

        ax.text(
            x,
            y,
            text,
            ha="center",
            va="center",
            fontsize=typo["size"],
            fontweight=typo["weight"],
            fontname=typo["font"],
            color=color,
            zorder=zorder,
            **kwargs,
        )

    @staticmethod
    def draw_sparkline(
        ax,
        x_pos: float,
        y_pos: float,
        width: float,
        height: float,
        values: list,
        color: str = "#3498DB",
        title: str = "",
    ) -> None:
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
            ax.text(
                x_pos,
                y_pos,
                "N/A",
                ha="center",
                va="center",
                fontsize=8,
                color="#999999",
                style="italic",
            )
            return

        # Normalize values to 0-1 range for positioning
        min_val = min(values)
        max_val = max(values)
        value_range = max_val - min_val if max_val > min_val else 1

        normalized = [(v - min_val) / value_range for v in values]

        # Calculate x positions for points
        n_points = len(values)
        x_spacing = width / (n_points - 1) if n_points > 1 else width
        x_coords = [x_pos - width / 2 + i * x_spacing for i in range(n_points)]
        y_coords = [y_pos - height / 2 + (n * height) for n in normalized]

        # Draw sparkline path
        ax.plot(x_coords, y_coords, color=color, linewidth=1.5, zorder=3, alpha=0.8)

        # Draw mini data points
        ax.scatter(x_coords, y_coords, s=15, color=color, zorder=4, alpha=0.6)

        # Highlight last value with larger point
        ax.scatter(
            [x_coords[-1]],
            [y_coords[-1]],
            s=25,
            color=color,
            zorder=5,
            alpha=1.0,
            edgecolors="white",
            linewidth=0.5,
        )

        # Optional background area under curve
        y_baseline = [y_pos - height / 2] * n_points
        ax.fill_between(
            x_coords, y_coords, y_baseline, alpha=0.1, color=color, zorder=1
        )

    @staticmethod
    def draw_h2h_history(
        ax,
        x_pos: float,
        y_pos: float,
        width: float,
        height: float,
        h2h_results: list,
        home_team: str = "",
        away_team: str = "",
        home_color: str = "#3498DB",
        away_color: str = "#E74C3C",
    ) -> None:
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
            ax.text(
                x_pos,
                y_pos,
                "No H2H History",
                ha="center",
                va="center",
                fontsize=14,
                color="#999999",
                style="italic",
                fontweight="bold",
            )
            return

        # Limit to last 5 meetings
        recent_h2h = h2h_results[-5:]

        # Draw mini result squares for each match
        box_size = (width - 0.3) / len(recent_h2h)
        start_x = x_pos - width / 2 + 0.15

        for i, match in enumerate(recent_h2h):
            box_x = start_x + i * box_size
            box_y = y_pos

            # Determine color based on winner
            result = match.get("winner", "draw")
            if result == "home":
                result_color = home_color
                result_symbol = "🏠"
            elif result == "away":
                result_color = away_color
                result_symbol = "✈️"
            else:
                result_color = "#7F8C8D"
                result_symbol = "="

            # Draw match result box
            result_box = FancyBboxPatch(
                (box_x - box_size / 2 + 0.05, box_y - height / 2 + 0.05),
                box_size - 0.1,
                height - 0.1,
                boxstyle="round,pad=0.03",
                facecolor=result_color,
                edgecolor=result_color,
                alpha=0.2,
                linewidth=1,
                zorder=2,
            )
            ax.add_patch(result_box)

            # Score text
            score = match.get("score", "-")
            ax.text(
                box_x,
                box_y + 0.08,
                score,
                ha="center",
                va="center",
                fontsize=8,
                fontweight="bold",
                color=result_color,
                zorder=3,
            )

            # Result indicator
            ax.text(
                box_x,
                box_y - 0.10,
                result_symbol,
                ha="center",
                va="center",
                fontsize=14,
                zorder=3,
            )


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
        "la-liga": {"code": "PD", "name": "La Liga", "folder": "la-liga"},
        "premier-league": {
            "code": "PL",
            "name": "Premier League",
            "folder": "premier-league",
        },
        "bundesliga": {"code": "BL1", "name": "Bundesliga", "folder": "bundesliga"},
        "serie-a": {"code": "SA", "name": "Serie A", "folder": "serie-a"},
        "ligue-1": {"code": "FL1", "name": "Ligue 1", "folder": "ligue-1"},
    }

    _LEAGUE_ALIASES = {
        "laliga": "la-liga",
        "premierleague": "premier-league",
        "seriea": "serie-a",
        "ligue1": "ligue-1",
    }

    def __init__(
        self,
        skip_injuries: bool = False,
        injuries_disable_ttl_override: int | None = None,
        export_metrics: bool = False,
        export_metrics_dir: str | None = None,
    ) -> None:
        api_key = os.getenv("FOOTBALL_DATA_API_KEY")
        if not api_key:
            raise ValueError(
                "FOOTBALL_DATA_API_KEY environment variable not set. Please configure it in .env or your shell environment."
            )
        self.api_key = api_key
        self.headers = {"X-Auth-Token": self.api_key}

        # Smart configuration validation
        self.validate_environment()
        self.setup_directory_structure()

        # Initialize enhanced prediction engines
        self.enhanced_predictor = EnhancedPredictor(self.api_key)
        self.data_quality_enhancer = DataQualityEnhancer(self.api_key)
        # Respect CLI preference to skip injury API calls
        self.data_quality_enhancer.skip_injuries = skip_injuries

        # Initialize PredictionTracker and attach to predictor for production recording
        try:
            from app.models.prediction_tracker import PredictionTracker

            self.prediction_tracker = PredictionTracker()
            # Attach tracker to enhanced predictor if attribute present
            try:
                self.enhanced_predictor.prediction_tracker = self.prediction_tracker
            except Exception:
                pass
        except Exception:
            self.prediction_tracker = None
        # If CLI override present, pass it to the enhancer
        self.data_quality_enhancer.injuries_disable_ttl_override = (
            injuries_disable_ttl_override
        )
        # Metrics export option
        self.export_metrics = export_metrics
        self.export_metrics_dir = export_metrics_dir or "reports/metrics"

        # Load centralized settings (safe fallback to empty dict)
        self._settings: Dict[str, Any] = {}
        try:
            cfg_path = Path(__file__).parent / "config" / "settings.yaml"
            if cfg_path.exists():
                with open(cfg_path, encoding="utf-8") as _f:
                    self._settings = yaml.safe_load(_f) or {}
        except Exception:
            self._settings = {}

        # Phase 2 Lite integration
        if PHASE2_LITE_AVAILABLE:
            self.phase2_lite_predictor: Optional[Phase2LitePredictor] = (
                Phase2LitePredictor(self.api_key)
            )
            print("Phase 2 Lite enhanced intelligence active!")
        else:
            self.phase2_lite_predictor = None

    # Small helpful utilities to ensure backward compatibility with older templates
    def format_team_name_for_display(self, team_name: str) -> str:
        """Return a cleaned, display-ready team name."""
        if not team_name:
            return "Unknown"
        # Simple cleanup: collapse extra whitespace and title-case common names
        return " ".join(team_name.split()).strip()

    def short_team_name(self, team_name: str, max_len: int = 18) -> str:
        """Return a shortened version of the team name for tight layouts."""
        name = self.format_team_name_for_display(team_name)
        if len(name) <= max_len:
            return name
        return name[: max_len - 3] + "..."

    def normalize_team_name(self, name: str) -> str:
        """Normalize a team name for filenames and consistent comparisons.

        This delegates to the module-level `normalize_team_name` function when
        available, falling back to a simple formatter if needed.
        """
        try:
            # Use global module function to avoid recursive method call
            return globals()["normalize_team_name"](name)
        except Exception:
            return self.format_team_name_for_display(name or "")

    def _safe_float(self, value: Any, default: float = 0.0) -> float:
        """Convert various inputs to a float with a safe default.

        Handles strings with percentages and gracefully falls back to the
        provided default if conversion fails.
        """
        try:
            if value is None:
                return float(default)
            if isinstance(value, str):
                v = value.strip()
                # handle percentage strings like "45%"
                if v.endswith("%"):
                    v = v[:-1]
                return float(v)
            return float(value)
        except Exception:
            return float(default)

    def get_confidence_description(self, confidence: float) -> str:
        """Convert confidence into a human-readable percentage label."""
        try:
            pct = float(confidence) * 100.0
        except Exception:
            pct = 0.0

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

    def _format_advanced_predictions_section(self, match_data: JSONDict) -> str:
        """Delegate to module-level implementation for advanced predictions formatting."""
        return _format_advanced_predictions_section_impl(match_data)

    def validate_environment(self) -> None:
        """Smart environment validation with helpful guidance"""
        issues = []
        if not self.api_key or self.api_key == "":

            issues.append(
                "❌ API key not found. Set FOOTBALL_DATA_API_KEY environment variable"
            )
        elif len(self.api_key) < 10:
            issues.append("⚠️  API key seems too short - check if it's complete")

        # Check required modules
        required_modules = ["matplotlib", "numpy", "requests"]
        for module in required_modules:
            try:
                __import__(module)
            except ImportError:
                issues.append(
                    f"❌ Missing required module: {module}. Run: pip install {module}"
                )

        # Check directory permissions
        try:
            os.makedirs("reports/test", exist_ok=True)
            os.rmdir("reports/test")
        except PermissionError:
            issues.append("❌ Cannot write to reports directory. Check permissions")

        if issues:
            safe_print("🔧 CONFIGURATION ISSUES DETECTED:")
            for issue in issues:
                safe_print(f"   {issue}")
            safe_print("Note: Fix these issues before generating reports")
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
            "reports/archive",
        ]

        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            # Create .keep file to preserve directory structure
            keep_file = os.path.join(directory, ".keep")
            if not os.path.exists(keep_file):
                with open(keep_file, "w", encoding="utf-8") as f:
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
        cfg = self._settings.get("constants", {})
        th = cfg.get("color_thresholds", [25, 50, 75])
        palette_candidate = cfg.get("color_palette")
        palette: list[str]
        if isinstance(palette_candidate, (list, tuple)) and len(palette_candidate) >= 4:
            palette = [str(x) for x in palette_candidate[:4]]
        else:
            palette = ["#e74c3c", "#f39c12", "#f1c40f", "#2ecc71"]
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

    def generate_matches_report(
        self,
        num_matches: int,
        league_name: str,
        match_delay: int = 0,
        home_team: str | None = None,
        away_team: str | None = None,
    ) -> None:
        """Generate Phase 2 Lite enhanced reports for the next set of matches.

        Args:
            num_matches: Number of matches to generate
            league_name: League identifier
            match_delay: Delay in seconds between matches (0 = no delay)
            home_team: Optional exact or partial home team name to generate a specific match report
            away_team: Optional exact or partial away team name to generate a specific match report

        If both `home_team` and `away_team` are provided, the method will attempt to locate
        the scheduled match within the next `num_matches` matches and generate a report for
        that match only. Matching is case-insensitive and allows partial name matches.
        """

        start_time = time.time()

        league_info = self.get_league_info(league_name)
        if not league_info:
            print(f"❌ Unknown league: {league_name}")
            print("Available leagues: " + ", ".join(self.list_supported_leagues()))
            return

        safe_print(f"🏆 Generating Next {num_matches} {league_info['name']} Match(es)")
        safe_print("=" * 50)
        safe_print(f"⏱️  Started at: {datetime.now().strftime('%H:%M:%S')}")

        url = f"https://api.football-data.org/v4/competitions/{league_info['code']}/matches"
        params: Dict[str, Union[str, int]] = {
            "status": "SCHEDULED",
            "limit": num_matches,
        }
        params = {k: str(v) for k, v in params.items()}

        try:
            response = safe_request_get(
                url, headers=self.headers, params=params, logger=None
            )
            response.raise_for_status()
            data = cast(JSONDict, response.json())
            all_matches = data.get("matches", [])
            matches = all_matches[:num_matches]
        except Exception as exc:
            print(f"❌ Error fetching data: {exc}")
            return

        if not matches:
            print("❌ No upcoming matches found")
            return

        # If a specific match is requested by home/away team names, attempt to find it
        if home_team and away_team:
            def _normalize_for_match(s: str) -> str:
                return re.sub(r"[^a-z0-9]+", "", s.lower()) if s else ""

            target_home = _normalize_for_match(home_team)
            target_away = _normalize_for_match(away_team)

            def _match_candidate(m: JSONDict) -> bool:
                candidate_home = _normalize_for_match(m.get("homeTeam", {}).get("name", ""))
                candidate_away = _normalize_for_match(m.get("awayTeam", {}).get("name", ""))
                # Accept either exact normalized equality or substring matches
                return (
                    (target_home == candidate_home or target_home in candidate_home)
                    and (target_away == candidate_away or target_away in candidate_away)
                )

            found = [m for m in matches if _match_candidate(m)]
            if not found:
                print(
                    f"❌ No scheduled match found matching '{home_team}' vs '{away_team}' in the next {num_matches} scheduled matches"
                )
                return
            matches = [found[0]]  # Only process the first matching scheduled match

        safe_print(f"📅 Found {len(matches)} upcoming match(es)")
        safe_print("")

        for index, match in enumerate(matches, start=1):
            # Normalize team names to avoid abbreviations in displays and filenames
            raw_home = match["homeTeam"]["name"]
            raw_away = match["awayTeam"]["name"]
            home_team = self.normalize_team_name(raw_home) if raw_home else "Home Team"
            away_team = self.normalize_team_name(raw_away) if raw_away else "Away Team"
            match_date = match["utcDate"][:10]
            match_time = match["utcDate"][11:16]

            print(
                f"[MATCH {index}/{len(matches)}] Processing: {home_team} vs {away_team} on {match_date}"
            )

            # Use a safe slug for filesystem names
            def slugify(name: str) -> str:
                if not name:
                    return "team"
                s = name.lower()
                # Replace any non-alphanumeric characters with hyphens
                s = re.sub(r"[^a-z0-9]+", "-", s)
                s = s.strip("-")
                return s or "team"

            match_folder = f"{slugify(home_team)}_vs_{slugify(away_team)}_{match_date}"
            full_path = (
                f"reports/leagues/{league_info['folder']}/matches/{match_folder}"
            )
            os.makedirs(full_path, exist_ok=True)

            try:
                competition_code = get_competition_code_from_league(
                    league_info["folder"]
                )
            except Exception:
                competition_code = league_info["code"]

            try:
                if self.phase2_lite_predictor is not None:
                    prediction = self.phase2_lite_predictor.enhanced_prediction(
                        match, competition_code
                    )
                    prediction_engine = prediction.get(
                        "prediction_engine", "Enhanced Intelligence v4.1 + Phase 2 Lite"
                    )
                else:
                    prediction = self.enhanced_predictor.enhanced_prediction(
                        match, competition_code
                    )
                    prediction_engine = prediction.get(
                        "prediction_engine", "Enhanced Intelligence v4.1"
                    )
            except Exception as exc:
                print(
                    f"   [ERROR] Prediction failed for {home_team} vs {away_team}: {exc}"
                )
                continue

            try:
                enhanced_data = (
                    self.data_quality_enhancer.comprehensive_data_enhancement(match)
                )
            except Exception as exc:
                print(f"   [WARNING] Data quality enhancer issue: {exc}")
                enhanced_data = {}

            reliability_metrics = (
                prediction.get("reliability_metrics")
                or prediction.get("prediction_reliability")
                or {}
            )
            calibration_details = prediction.get("calibration_details", {})
            confidence_intervals = prediction.get("confidence_intervals", {})

            # Extract data for enhanced confidence calculation
            h2h_data = prediction.get(
                "head_to_head_analysis", prediction.get("head_to_head", {})
            )
            weather_data = enhanced_data.get("weather_conditions", {})
            player_data = enhanced_data.get("player_availability", {})
            referee_data = enhanced_data.get("referee_analysis", {})
            team_news = enhanced_data.get("team_news", {})

            confidence_value = self._safe_float(prediction.get("confidence"), 0.6)

            # Enhanced confidence calculation based on multiple real factors
            data_quality_score = enhanced_data.get("data_quality_score", 75) / 100.0
            reliability_score = (
                reliability_metrics.get("score", 60) / 100.0
                if reliability_metrics
                else 0.6
            )
            calibration_applied = 1.08 if calibration_details.get("applied") else 1.0
            h2h_total = h2h_data.get("total_meetings", 0)
            h2h_bonus = min(
                0.12, h2h_total * 0.008
            )  # Up to 12% bonus for comprehensive H2H data

            # Additional data availability bonuses
            weather_available = bool(weather_data.get("conditions"))
            player_available = bool(
                player_data.get("home_team") or player_data.get("away_team")
            )
            referee_available = bool(
                referee_data.get("name")
                and referee_data.get("name") not in ["TBD", "Unknown Referee"]
            )
            team_news_available = bool(
                team_news.get("home_team") or team_news.get("away_team")
            )

            data_availability_bonus = (
                weather_available * 0.03
                + player_available * 0.04
                + referee_available * 0.02
                + team_news_available * 0.03
            )

            # Weighted calculation: base * (data_quality + reliability + calibration + h2h + data_availability)
            confidence_multiplier = (
                1.0
                + (data_quality_score - 0.5) * 0.6
                + (reliability_score - 0.5) * 0.7
                + (calibration_applied - 1.0)
                + h2h_bonus
                + data_availability_bonus
            )
            confidence_value = confidence_value * confidence_multiplier

            # DYNAMIC minimum based on data availability - don't inflate confidence for poor data
            # Count how many data sources are available (0-4)
            data_sources_available = sum(
                [
                    weather_available,
                    player_available,
                    referee_available,
                    team_news_available,
                ]
            )
            # Base minimum: 45% with no data, up to 75% with all 4 sources + good quality
            # This prevents artificially high confidence when data is sparse
            dynamic_min_confidence = (
                0.45
                + (data_sources_available * 0.05)
                + (data_quality_score - 0.5) * 0.15
            )
            dynamic_min_confidence = max(
                0.40, min(0.75, dynamic_min_confidence)
            )  # Floor 40%, ceiling 75%

            confidence_value = max(dynamic_min_confidence, min(0.95, confidence_value))

            accuracy_probability = self._safe_float(
                prediction.get("report_accuracy_probability"), 0.65
            )

            # FIX: Calculate multiplier safely THEN apply bounds
            # (calibration_applied - 1.0) can be unbounded, so clamp BEFORE multiplication
            calibration_factor = max(
                0.0, min(2.0, calibration_applied - 1.0)
            )  # Clamp to [0, 2]
            accuracy_multiplier = (
                1.0
                + (data_quality_score - 0.5) * 0.55
                + (reliability_score - 0.5) * 0.65
                + calibration_factor
                + h2h_bonus * 0.9
                + data_availability_bonus * 0.8
            )
            # Further bound multiplier itself to prevent overflow
            accuracy_multiplier = max(0.5, min(1.8, accuracy_multiplier))
            accuracy_probability = accuracy_probability * accuracy_multiplier
            # Use same dynamic minimum for accuracy
            accuracy_probability = max(
                dynamic_min_confidence, min(0.95, accuracy_probability)
            )

            # Defensive extraction for win probabilities
            home_prob_raw = prediction.get(
                "home_win_probability", prediction.get("home_win_prob", 0.0)
            )
            home_prob = self._safe_float(home_prob_raw, 0.0)

            draw_prob_raw = prediction.get(
                "draw_probability", prediction.get("draw_prob", 0.0)
            )
            draw_prob = self._safe_float(draw_prob_raw, 0.0)

            away_prob_raw = prediction.get(
                "away_win_probability", prediction.get("away_win_prob", 0.0)
            )
            away_prob = self._safe_float(away_prob_raw, 0.0)

            expected_home_goals = self._safe_float(
                prediction.get("expected_home_goals"), 1.5
            )
            expected_away_goals = self._safe_float(
                prediction.get("expected_away_goals"), 1.2
            )
            processing_time = self._safe_float(prediction.get("processing_time"), 0.0)
            score_probability = self._safe_float(
                prediction.get("score_probability"), 10.0
            )
            score_probability_normalized = self._safe_float(
                prediction.get("score_probability_normalized"), 5.0
            )
            top3_combined_probability = self._safe_float(
                prediction.get("top3_combined_probability"), 25.0
            )
            top3_probability_normalized = self._safe_float(
                prediction.get("top3_probability_normalized"), 7.0
            )

            # Calculate over 2.5 and BTTS from expected goals if not provided (Poisson-based)
            over_2_5_raw = prediction.get(
                "over_2_5_goals_probability", prediction.get("over_2_5_probability")
            )
            if over_2_5_raw is not None:
                over_2_5_probability = self._safe_float(over_2_5_raw, 45.0)
            else:
                # Calculate from expected goals using Poisson distribution
                import math

                total_expected = expected_home_goals + expected_away_goals
                prob_under_2_5 = sum(
                    (total_expected**k * math.exp(-total_expected)) / math.factorial(k)
                    for k in range(3)  # 0, 1, 2 goals
                )
                over_2_5_probability = (1 - prob_under_2_5) * 100

            btts_raw = prediction.get("both_teams_score_probability")
            if btts_raw is not None:
                both_teams_score_probability = self._safe_float(btts_raw, 55.0)
            else:
                # Calculate from expected goals: P(BTTS) = P(home scores) * P(away scores)
                import math

                home_scores_prob = 1 - math.exp(-expected_home_goals)
                away_scores_prob = 1 - math.exp(-expected_away_goals)
                both_teams_score_probability = home_scores_prob * away_scores_prob * 100

            # Ensure expected_final_score does not contain team name text (use numeric score)
            raw_expected_score = prediction.get("expected_final_score", "1-1")
            # If the prediction includes letters (team names), reconstruct from expected goals
            if isinstance(raw_expected_score, str) and re.search(
                r"[A-Za-z]", raw_expected_score
            ):
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
                prediction.get("odds")
                or prediction.get("market_odds")
                or prediction.get("bookmakers")
                or prediction.get("betting")
            )

            flashscore_present = bool(
                enhanced_data.get("flashscore")
                or enhanced_data.get("flashscore_snapshot")
                or enhanced_data.get("flashscore_data")
            )

            match_data = {
                "match_id": match.get("id"),
                "home_team": (
                    home_team if home_team else prediction.get("home_team", "Home")
                ),
                "away_team": (
                    away_team if away_team else prediction.get("away_team", "Away")
                ),
                "date": match_date,
                "time": match_time,
                "league": league_info["name"],
                "confidence": round(confidence_value, 3),
                "report_accuracy_probability": round(accuracy_probability, 3),
                "home_win_probability": round(home_prob, 3),
                "draw_probability": round(draw_prob, 3),
                "away_win_probability": round(away_prob, 3),
                "expected_home_goals": round(expected_home_goals, 1),
                "expected_away_goals": round(expected_away_goals, 1),
                "processing_time": round(processing_time, 3),
                "recommendation": self.get_recommendation(
                    {
                        "home_win_prob": home_prob,
                        "draw_prob": draw_prob,
                        "away_win_prob": away_prob,
                    }
                ),
                "confidence_level": self.get_confidence_description(confidence_value),
                "expected_final_score": safe_expected_score,
                "score_probability": round(score_probability, 1),
                "score_probability_normalized": round(score_probability_normalized, 1),
                "top3_combined_probability": round(top3_combined_probability, 1),
                "top3_probability_normalized": round(top3_probability_normalized, 1),
                "alternative_scores": prediction.get("alternative_scores", []),
                "score_probabilities": prediction.get("score_probabilities", []),
                "score_probabilities_normalized": prediction.get(
                    "score_probabilities_normalized", []
                ),
                "over_2_5_goals_probability": round(over_2_5_probability, 1),
                "both_teams_score_probability": round(both_teams_score_probability, 1),
                "head_to_head_analysis": prediction.get(
                    "head_to_head_analysis", prediction.get("head_to_head", {})
                ),
                "home_performance_analysis": prediction.get(
                    "home_performance_analysis", prediction.get("home_performance", {})
                ),
                "away_performance_analysis": prediction.get(
                    "away_performance_analysis", prediction.get("away_performance", {})
                ),
                "goal_timing_prediction": prediction.get(
                    "goal_timing_prediction", prediction.get("goal_timing", {})
                ),
                "intelligence_summary": prediction.get("intelligence_summary", {}),
                "player_availability": enhanced_data.get("player_availability", {}),
                "weather_conditions": enhanced_data.get("weather_conditions", {}),
                "referee_analysis": enhanced_data.get("referee_analysis", {}),
                "team_news": enhanced_data.get("team_news", {}),
                "data_quality_score": enhanced_data.get("data_quality_score", 75.0),
                "reliability_metrics": reliability_metrics,
                "calibration_details": calibration_details,
                "confidence_intervals": confidence_intervals,
                # Data provenance flags: True when live/derived data existed; False when fallback/estimated used
                "data_provenance": {
                    "weather": bool(weather_available),
                    "player_availability": bool(player_available),
                    "referee": bool(referee_available),
                    "team_news": bool(team_news_available),
                    "h2h": bool(h2h_total and h2h_total > 0),
                    "odds": bool(odds_available),
                    "flashscore": bool(flashscore_present),
                },
                "phase2_lite_enhanced": prediction.get("phase2_lite_enhanced", False),
                "prediction_engine": prediction_engine,
                # Phase 4-7 Enhanced Data
                "advanced_predictions": {
                    "btts": prediction.get("btts", {}),
                    "over_under": prediction.get("over_under", {}),
                    "exact_scores": prediction.get("exact_scores", []),
                    "two_stage_score": prediction.get("two_stage_score", {}),
                },
                "shot_quality": prediction.get("shot_quality", {}),
                "defensive_metrics": prediction.get("defensive_metrics", {}),
                "odds_movement": prediction.get("odds_movement", {}),
                "market_implied": prediction.get("market_implied", {}),
                "sharp_money_alert": prediction.get("sharp_money_alert", {}),
                "player_impact": prediction.get("player_impact", {}),
                # Phase enhancement flags
                "phase_enhancements": {
                    "phase1_enhanced": prediction.get("phase1_enhanced", False),
                    "phase2_enhanced": prediction.get("phase2_enhanced", False),
                    "phase3_enhanced": prediction.get("phase3_enhanced", False),
                    "phase4_enhanced": prediction.get("phase4_enhanced", False),
                    "phase5_enhanced": prediction.get("phase5_enhanced", False),
                    "phase6_enhanced": prediction.get("phase6_enhanced", False),
                    "phase7_enhanced": prediction.get("phase7_enhanced", False),
                },
                # Optimization metadata from enhanced ensemble (Phase 2 Lite + v4.2)
                "optimization_metadata": {
                    "match_context": prediction.get("match_context", "unknown"),
                    "model_agreement_factor": prediction.get(
                        "model_agreement_factor", 0.5
                    ),
                    "optimization_applied": prediction.get(
                        "optimization_applied", False
                    ),
                    "ensemble_weights": prediction.get("component_weights", {}),
                },
                "generated_at": datetime.now().isoformat(),
                # Provider IDs (if available) for reliable post-match mapping
                "provider_ids": {
                    "football_data_id": match.get("id"),
                    "flashscore_id": (
                        (match.get("flashscore_data") or {}).get("id")
                        if isinstance(match, dict)
                        else None
                    ),
                },
            }

            # Merge enhanced data provenance into match_data for final output
            enhanced_prov = (
                enhanced_data.get("data_provenance", {})
                if isinstance(enhanced_data, dict)
                else {}
            )
            if enhanced_prov:
                # Detailed provenance under a dedicated field
                match_data.setdefault("data_provenance_details", {})
                match_data["data_provenance_details"].update(enhanced_prov)

                # Promote common boolean clamps for easier consumer access
                for key, val in enhanced_prov.items():
                    # only add simple scalar flags to top-level data_provenance when appropriate
                    if isinstance(val, (bool, int, float, str)):
                        match_data["data_provenance"][key] = val

            self.save_json(match_data, full_path)
            self.save_summary(match_data, full_path)
            try:
                self.save_image(match_data, full_path)
            except Exception as e:
                # Ensure image generation failures do not stop report generation
                safe_print(f"⚠️  Image generation failed for match {match_folder}: {e}")
                # Attempt to write a placeholder image to indicate failure
                try:
                    placeholder_fig = plt.figure(figsize=(6, 4))
                    plt.text(
                        0.5,
                        0.5,
                        "Image generation failed",
                        ha="center",
                        va="center",
                        fontsize=14,
                    )
                    plt.axis("off")
                    plt.savefig(
                        f"{full_path}/prediction_card.png", dpi=150, bbox_inches="tight"
                    )
                    plt.close(placeholder_fig)
                    print(
                        f"   • Wrote placeholder image at: {full_path}/prediction_card.png"
                    )
                except Exception:
                    # If placeholder fails, continue silently but log
                    print(
                        "   • Could not write placeholder image for match", match_folder
                    )
            self.save_format_copies(match_data, match_folder)

            # Guarantee: ensure a PNG exists for every report. If missing or zero-sized, write a fallback placeholder image.
            try:
                if ensure_prediction_image_exists(full_path, match_data, match_folder):
                    print(f"   • Verified/created prediction image for: {match_folder}")
                else:
                    safe_print(f"⚠️ Could not create a fallback prediction image for: {match_folder}")
            except Exception as fallback_ex:
                safe_print(f"⚠️ Could not write fallback image for match {match_folder}: {fallback_ex}")
            print("   Phase 2 Lite report generated")
            print(
                f"   Expected Score: {match_data['expected_final_score']} ({match_data['score_probability']:.1f}%)"
            )
            safe_print(
                f"   ⚽ Expected Goals: {match_data['expected_home_goals']:.1f} - {match_data['expected_away_goals']:.1f}"
            )
            safe_print(
                f"   📊 Data Confidence: {match_data['confidence']:.1%} | Accuracy {match_data['report_accuracy_probability']:.1%}"
            )

            if reliability_metrics:
                rel_indicator = reliability_metrics.get(
                    "indicator"
                ) or reliability_metrics.get("level", "Reliability")
                rel_score = reliability_metrics.get("score")
                if rel_score is not None:
                    safe_print(f"   🔒 Reliability: {rel_indicator} ({rel_score:.1f})")
                else:
                    safe_print(f"   🔒 Reliability: {rel_indicator}")
                recommendation = reliability_metrics.get("recommendation")
                if recommendation:
                    safe_print(f"   💡 Reliability Note: {recommendation}")

            if calibration_details.get("applied"):
                shrink = calibration_details.get("shrink_factor", 0.0) * 100
                safe_print(f"   🧭 Calibration applied ({shrink:.1f}% neutral blend)")

            print(f"   • Saved to: {full_path}")
            print()

            # Add delay between matches if specified (helps avoid API rate limiting)
            if match_delay > 0 and index < len(matches):
                print(
                    f"   ⏳ Waiting {match_delay}s before next match (rate limit protection)..."
                )
                time.sleep(match_delay)

        total_time = time.time() - start_time
        avg_time = total_time / len(matches) if matches else 0

        safe_print(f"[COMPLETE] All {len(matches)} {league_info['name']} reports completed!")
        safe_print(f"⏱️  Total execution time: {total_time:.2f}s")
        safe_print(f"⚡ Average per match: {avg_time:.2f}s")
        safe_print(f"🎯 Finished at: {datetime.now().strftime('%H:%M:%S')}")

        # Aggregate API stats from the predictor for quick debugging and quality analysis
        try:
            from app.utils.metrics import get_metrics

            m = get_metrics()
            api_calls = 0
            api_errors = 0
            # Sum across API keys if present
            for key, counters in (m or {}).items():
                api_calls += counters.get("calls", 0) or 0
                api_errors += counters.get("errors", 0) or 0
            warnings_list = (
                getattr(self.enhanced_predictor, "data_quality_warnings", []) or []
            )
            if api_calls or api_errors or warnings_list:
                print("\n[API METRICS]")
                print(f"  API calls: {api_calls}")
                print(f"  API errors (requests + rate): {api_errors}")
                print(f"  Data quality warnings: {len(warnings_list)}")
                for w in warnings_list[-5:]:
                    print(f"    - {w}")
        except Exception:
            # Keep summary non-fatal if predictor attributes change
            pass
        # Export metrics optionally
        try:
            if getattr(self, "export_metrics", False):
                try:
                    from scripts.export_metrics import main as export_metrics_main

                    export_metrics_main(self.export_metrics_dir)
                except Exception as e:
                    safe_print(f"⚠️  Could not export metrics: {e}")
        except Exception:
            pass

    def generate_single_match_report(self) -> None:
        """Generate report for just the next 1 La Liga match (backward compatibility)"""
        self.generate_matches_report(1, "la-liga")

    def generate_match_by_team_names(
        self,
        home_query: str,
        away_query: str,
        league_name: str,
        lookahead_days: int = 30,
    ) -> None:
        """Generate a report for a specific match identified by home and away team query strings.

        Args:
            home_query: Partial or full home team name to match
            away_query: Partial or full away team name to match
            league_name: League identifier (slug)
            lookahead_days: How many days ahead to search for scheduled matches
        """
        league_info = self.get_league_info(league_name)
        if not league_info:
            print(f"❌ Unknown league: {league_name}")
            print("Available leagues: " + ", ".join(self.list_supported_leagues()))
            return

        # Build date range for the lookahead window
        today = datetime.utcnow().date()
        date_from = today.isoformat()
        date_to = (today + timedelta(days=lookahead_days)).isoformat()

        url = f"https://api.football-data.org/v4/competitions/{league_info['code']}/matches"
        params: Dict[str, Union[str, int]] = {
            "status": "SCHEDULED",
            "dateFrom": date_from,
            "dateTo": date_to,
            "limit": 200,
        }
        params = {k: str(v) for k, v in params.items()}

        try:
            response = safe_request_get(url, headers=self.headers, params=params)
            response.raise_for_status()
            data = cast(JSONDict, response.json())
            all_matches = data.get("matches", [])
        except Exception as exc:
            print(f"❌ Error fetching data: {exc}")
            return

        # Normalize queries
        hq = home_query.lower().strip()
        aq = away_query.lower().strip()

        found = None
        for m in all_matches:
            raw_home = m.get("homeTeam", {}).get("name", "") or ""
            raw_away = m.get("awayTeam", {}).get("name", "") or ""
            nh = self.normalize_team_name(raw_home)
            na = self.normalize_team_name(raw_away)
            # match if both substrings present in normalized names
            if hq in nh.lower() and aq in na.lower():
                found = m
                break

        if not found:
            print(
                f"❌ No scheduled match found for '{home_query} vs {away_query}' in {league_info['name']} within next {lookahead_days} days."
            )
            # Fallback: try again without status filter (some matches may be TIMED or PAUSED)
            try:
                params2 = {"dateFrom": date_from, "dateTo": date_to, "limit": 200}
                params2 = {k: str(v) for k, v in params2.items()}
                response2 = safe_request_get(url, headers=self.headers, params=params2)
                response2.raise_for_status()
                data2 = cast(JSONDict, response2.json())
                all_matches2 = data2.get("matches", [])
                for m in all_matches2:
                    raw_home = m.get("homeTeam", {}).get("name", "") or ""
                    raw_away = m.get("awayTeam", {}).get("name", "") or ""
                    nh = self.normalize_team_name(raw_home)
                    na = self.normalize_team_name(raw_away)
                    if hq in nh.lower() and aq in na.lower():
                        found = m
                        print("ℹ️  Found a match in fallback search (no status filter).")
                        break
            except Exception as exc:
                safe_print(f"❌ Fallback fetch failed: {exc}")

            if not found:
                return

        # Reuse the single-match processing logic from generate_matches_report
        home_team = self.normalize_team_name(found["homeTeam"]["name"])
        away_team = self.normalize_team_name(found["awayTeam"]["name"])
        match_date = found["utcDate"][:10]
        match_time = found["utcDate"][11:16]

        def slugify(name: str) -> str:
            if not name:
                return "team"
            s = name.lower()
            s = re.sub(r"[^a-z0-9]+", "-", s)
            s = s.strip("-")
            return s or "team"

        match_folder = f"{slugify(home_team)}_vs_{slugify(away_team)}_{match_date}"
        full_path = f"reports/leagues/{league_info['folder']}/matches/{match_folder}"
        os.makedirs(full_path, exist_ok=True)

        try:
            competition_code = get_competition_code_from_league(league_info["folder"])
        except Exception:
            competition_code = league_info["code"]

        try:
            if self.phase2_lite_predictor is not None:
                prediction = self.phase2_lite_predictor.enhanced_prediction(
                    found, competition_code
                )
                prediction_engine = prediction.get(
                    "prediction_engine", "Enhanced Intelligence v4.1 + Phase 2 Lite"
                )
            else:
                prediction = self.enhanced_predictor.enhanced_prediction(
                    found, competition_code
                )
                prediction_engine = prediction.get(
                    "prediction_engine", "Enhanced Intelligence v4.1"
                )
        except Exception as exc:
            print(f"   [ERROR] Prediction failed for {home_team} vs {away_team}: {exc}")
            return

        try:
            enhanced_data = self.data_quality_enhancer.comprehensive_data_enhancement(
                found
            )
        except Exception as exc:
            print(f"   [WARNING] Data quality enhancer issue: {exc}")
            enhanced_data = {}

        # Build match_data using same defensive extraction logic as generate_matches_report
        try:
            # Defensive confidence and metric extraction
            confidence_value = self._safe_float(prediction.get("confidence"), 0.6)
            data_quality_score = enhanced_data.get("data_quality_score", 0.75)
            reliability_metrics = enhanced_data.get("reliability_metrics", {}) or {}
            reliability_score = self._safe_float(reliability_metrics.get("score"), 0.7)
            calibration_applied = self._safe_float(
                prediction.get("calibration_applied"), 1.0
            )
            h2h_bonus = self._safe_float(prediction.get("h2h_bonus", 0.0), 0.0)
            data_availability_bonus = 0.0

            # accuracy/probability extraction (safe)
            home_prob = self._safe_float(
                prediction.get(
                    "home_win_probability", prediction.get("home_win_prob", 0.0)
                ),
                0.0,
            )
            draw_prob = self._safe_float(
                prediction.get("draw_probability", prediction.get("draw_prob", 0.0)),
                0.0,
            )
            away_prob = self._safe_float(
                prediction.get(
                    "away_win_probability", prediction.get("away_win_prob", 0.0)
                ),
                0.0,
            )

            expected_home_goals = self._safe_float(
                prediction.get("expected_home_goals"), 1.5
            )
            expected_away_goals = self._safe_float(
                prediction.get("expected_away_goals"), 1.2
            )

            # Additional defensive metrics
            score_probability = self._safe_float(
                prediction.get("score_probability"), 10.0
            )
            score_probability_normalized = self._safe_float(
                prediction.get("score_probability_normalized"), 5.0
            )
            top3_combined_probability = self._safe_float(
                prediction.get("top3_combined_probability"), 25.0
            )
            top3_probability_normalized = self._safe_float(
                prediction.get("top3_probability_normalized"), 7.0
            )
            processing_time = self._safe_float(prediction.get("processing_time"), 0.0)

            # Safe expected final score
            raw_expected_score = prediction.get("expected_final_score", "1-1")
            if isinstance(raw_expected_score, str) and re.search(
                r"[A-Za-z]", raw_expected_score
            ):
                safe_expected_score = f"{int(round(expected_home_goals))}-{int(round(expected_away_goals))}"
            else:
                m = None
                if isinstance(raw_expected_score, str):
                    m = re.search(r"(\d+)\s*[-–]\s*(\d+)", raw_expected_score)
                if m:
                    safe_expected_score = f"{m.group(1)}-{m.group(2)}"
                else:
                    safe_expected_score = f"{int(round(expected_home_goals))}-{int(round(expected_away_goals))}"

            over_2_5_raw = prediction.get(
                "over_2_5_goals_probability", prediction.get("over_2_5_probability")
            )
            if over_2_5_raw is not None:
                over_2_5_probability = self._safe_float(over_2_5_raw, 45.0)
            else:
                import math

                total_expected = expected_home_goals + expected_away_goals
                prob_under_2_5 = sum(
                    (total_expected**k * math.exp(-total_expected)) / math.factorial(k)
                    for k in range(3)
                )
                over_2_5_probability = (1 - prob_under_2_5) * 100

            btts_raw = prediction.get("both_teams_score_probability")
            if btts_raw is not None:
                both_teams_score_probability = self._safe_float(btts_raw, 55.0)
            else:
                import math

                home_scores_prob = 1 - math.exp(-expected_home_goals)
                away_scores_prob = 1 - math.exp(-expected_away_goals)
                both_teams_score_probability = home_scores_prob * away_scores_prob * 100
            # Minimal provenance flags
            weather_available = bool(enhanced_data.get("weather_conditions"))
            player_available = bool(enhanced_data.get("player_availability"))
            referee_available = bool(enhanced_data.get("referee_analysis"))
            team_news_available = bool(enhanced_data.get("team_news"))

            match_data = {
                "match_id": found.get("id"),
                "home_team": home_team,
                "away_team": away_team,
                "date": match_date,
                "time": match_time,
                "league": league_info["name"],
                "confidence": round(confidence_value, 3),
                "report_accuracy_probability": round(
                    self._safe_float(
                        prediction.get("report_accuracy_probability", 0.65), 0.65
                    ),
                    3,
                ),
                "home_win_probability": round(home_prob, 3),
                "draw_probability": round(draw_prob, 3),
                "away_win_probability": round(away_prob, 3),
                "expected_home_goals": round(expected_home_goals, 1),
                "expected_away_goals": round(expected_away_goals, 1),
                "expected_final_score": safe_expected_score,
                "score_probability": round(score_probability, 1),
                "score_probability_normalized": round(score_probability_normalized, 1),
                "top3_combined_probability": round(top3_combined_probability, 1),
                "top3_probability_normalized": round(top3_probability_normalized, 1),
                "over_2_5_goals_probability": round(over_2_5_probability, 1),
                "both_teams_score_probability": round(both_teams_score_probability, 1),
                "recommendation": self.get_recommendation(
                    {
                        "home_win_prob": home_prob,
                        "draw_prob": draw_prob,
                        "away_win_prob": away_prob,
                    }
                ),
                "confidence_level": self.get_confidence_description(confidence_value),
                "head_to_head_analysis": prediction.get(
                    "head_to_head_analysis", prediction.get("head_to_head", {})
                ),
                "home_performance_analysis": prediction.get(
                    "home_performance_analysis", prediction.get("home_performance", {})
                ),
                "away_performance_analysis": prediction.get(
                    "away_performance_analysis", prediction.get("away_performance", {})
                ),
                "intelligence_summary": prediction.get("intelligence_summary", {}),
                "player_availability": enhanced_data.get("player_availability", {}),
                "weather_conditions": enhanced_data.get("weather_conditions", {}),
                "referee_analysis": enhanced_data.get("referee_analysis", {}),
                "team_news": enhanced_data.get("team_news", {}),
                "data_quality_score": enhanced_data.get("data_quality_score", 75.0),
                "reliability_metrics": reliability_metrics,
                "prediction_engine": prediction_engine,
                "generated_at": datetime.now().isoformat(),
                "raw_prediction": prediction,
                "data_enhancement": enhanced_data,
            }

            # Advanced model shadow/prediction (non-blocking)
            try:
                adv_cfg = (
                    self._settings.get("models", {}).get("advanced_model", {})
                    if self._settings
                    else {}
                )
                adv_enabled = adv_cfg.get("enabled", True)
                adv_mode = adv_cfg.get("mode", "shadow")
                # Attempt to locate a model artifact in models/advanced
                model_dir = Path("models/advanced")
                model_artifact = None
                if model_dir.exists():
                    candidates = sorted(
                        [p for p in model_dir.iterdir() if p.is_file()],
                        key=lambda p: p.name,
                    )
                    if candidates:
                        model_artifact = candidates[-1]
                if adv_enabled and model_artifact is not None:
                    try:
                        from app.models.advanced_predictor import AdvancedAIMLPredictor

                        adv = AdvancedAIMLPredictor(model_artifact)
                        feat = adv.extract_advanced_features(
                            {
                                "expected_home_goals": match_data.get(
                                    "expected_home_goals"
                                ),
                                "expected_away_goals": match_data.get(
                                    "expected_away_goals"
                                ),
                                "home_win_prob": match_data.get("home_win_probability")
                                or match_data.get("raw_prediction", {}).get(
                                    "home_win_prob"
                                ),
                                "draw_prob": match_data.get("draw_probability")
                                or match_data.get("raw_prediction", {}).get(
                                    "draw_prob"
                                ),
                                "away_win_prob": match_data.get("away_win_probability")
                                or match_data.get("raw_prediction", {}).get(
                                    "away_win_prob"
                                ),
                                "confidence": match_data.get(
                                    "report_accuracy_probability"
                                )
                                or match_data.get("raw_prediction", {}).get(
                                    "confidence"
                                ),
                            }
                        )
                        adv_pred = adv.predict_with_ml_ensemble(feat)
                        match_data["advanced_model"] = {
                            "mode": adv_mode,
                            "model_artifact": str(model_artifact),
                            "prediction": adv_pred,
                        }
                    except Exception as e:
                        safe_print(f"⚠️ Advanced model prediction failed (non-blocking): {e}")
            except Exception:
                pass

            # Save results
            self.save_json(match_data, full_path)
            self.save_summary(match_data, full_path)
            print(f"✅ Report generated: {full_path}")
        except Exception as exc:
            print(f"❌ Failed to save report: {exc}")
            return

    def save_json(self, match_data: JSONDict, path: Union[str, Path]) -> None:
        """Save match data as JSON. Synthetic reports are redirected to `reports/simulated/` to avoid publishing made-up data in the normal reports area."""
        # Base synthetic detection from existing flags
        is_synthetic = bool(
            match_data.get("is_synthetic")
            or match_data.get("fallback_used")
            or (match_data.get("prediction_method") or "").startswith("fallback")
            or (match_data.get("mode") or "") == "simulated"
        )

        # Publication gate: treat low-confidence or low data-quality reports as synthetic
        try:
            pub_gate = self._settings.get("reporting", {}).get("publication_gate", {}) if getattr(self, "_settings", None) else {}
            if pub_gate.get("enabled", True) and not is_synthetic:
                min_conf = float(pub_gate.get("min_confidence", 0.5))
                min_dq = float(pub_gate.get("min_data_quality_score", 60.0))
                # canonical confidence field preferences
                confidence = match_data.get("report_accuracy_probability")
                if confidence is None:
                    confidence = match_data.get("confidence")
                confidence = float(confidence or 0.0)
                data_quality = float(match_data.get("data_quality_score") or 0.0)
                if confidence < min_conf or data_quality < min_dq:
                    is_synthetic = True
                    # annotate reason
                    match_data = dict(match_data)
                    match_data.setdefault("synthetic_reason", "publication_gate_threshold")
                    match_data.setdefault("is_synthetic", True)
                    match_data.setdefault("synthetic_notice", "Report did not meet publication thresholds and was segregated to reports/simulated for audit.")
                    safe_print("⚠️ Publication gate: report below thresholds - redirecting to reports/simulated")
        except Exception:
            # Fail safe: if config inaccessible, proceed with existing flags
            pass
        if is_synthetic:
            # Annotate and write to a simulated-reports folder instead
            match_data = dict(match_data)
            match_data["synthetic_notice"] = (
                "This report is synthetic/fallback and is NOT driven by live or sufficient historical data. "
                "It has been written to the simulated reports directory to avoid accidental publication."
            )
            safe_print("⚠️ Synthetic/fallback prediction detected - saving to reports/simulated to avoid publication")
            # Determine league subfolder from original path if possible
            try:
                p = Path(path)
                parts = p.parts
                if "leagues" in parts:
                    idx = parts.index("leagues")
                    league = parts[idx + 1]
                else:
                    league = "unknown"
            except Exception:
                league = "unknown"
            synthetic_dir = Path("reports") / "simulated" / league / "matches" / (Path(path).name + "_synthetic")
            synthetic_dir.mkdir(parents=True, exist_ok=True)
            with open(synthetic_dir / "prediction.json", "w", encoding="utf-8") as f:
                json.dump(match_data, f, indent=2, ensure_ascii=False)
            # Also write a small marker file for quick inspection
            with open(synthetic_dir / "SYNTHETIC_NOTICE.txt", "w", encoding="utf-8") as f:
                f.write(match_data["synthetic_notice"])
            return

        # Normal (non-synthetic) path
        with open(f"{path}/prediction.json", "w", encoding="utf-8") as f:
            json.dump(match_data, f, indent=2, ensure_ascii=False)

    def save_summary(self, match_data: JSONDict, path: Union[str, Path]) -> None:
        """Save enhanced human-readable summary with intelligence analysis"""

        # Extract enhanced data
        h2h_data = match_data.get("head_to_head_analysis", {})
        home_perf = match_data.get("home_performance_analysis", {})
        away_perf = match_data.get("away_performance_analysis", {})
        goal_timing = match_data.get("goal_timing_prediction", {})
        intelligence = match_data.get("intelligence_summary", {})
        player_data = match_data.get("player_availability", {})
        weather_data = match_data.get("weather_conditions", {})
        referee_data = match_data.get("referee_analysis", {})
        team_news = match_data.get("team_news", {})
        reliability_metrics = match_data.get("reliability_metrics", {}) or {}
        calibration_details = match_data.get("calibration_details", {}) or {}
        confidence_intervals = match_data.get("confidence_intervals", {}) or {}

        # Ensure advanced model prediction is available when regenerating summary (shadow mode by default)
        try:
            if "advanced_model" not in match_data:
                adv_cfg = (
                    self._settings.get("models", {}).get("advanced_model", {})
                    if self._settings
                    else {}
                )
                adv_enabled = adv_cfg.get("enabled", True)
                adv_mode = adv_cfg.get("mode", "shadow")
                model_dir = Path("models/advanced")
                model_artifact = None
                if model_dir.exists():
                    candidates = sorted(
                        [p for p in model_dir.iterdir() if p.is_file()],
                        key=lambda p: p.name,
                    )
                    if candidates:
                        model_artifact = candidates[-1]
                if adv_enabled and model_artifact is not None:
                    from app.models.advanced_predictor import AdvancedAIMLPredictor

                    adv = AdvancedAIMLPredictor(model_artifact)
                    feat = adv.extract_advanced_features(
                        {
                            "expected_home_goals": match_data.get(
                                "expected_home_goals"
                            ),
                            "expected_away_goals": match_data.get(
                                "expected_away_goals"
                            ),
                            "home_win_prob": match_data.get("home_win_probability")
                            or match_data.get("raw_prediction", {}).get(
                                "home_win_prob"
                            ),
                            "draw_prob": match_data.get("draw_probability")
                            or match_data.get("raw_prediction", {}).get("draw_prob"),
                            "away_win_prob": match_data.get("away_win_probability")
                            or match_data.get("raw_prediction", {}).get(
                                "away_win_prob"
                            ),
                            "confidence": match_data.get("report_accuracy_probability")
                            or match_data.get("raw_prediction", {}).get("confidence"),
                        }
                    )
                    adv_pred = adv.predict_with_ml_ensemble(feat)
                    print(f"[DEBUG] advanced model predicted: {adv_pred}")
                    match_data["advanced_model"] = {
                        "mode": adv_mode,
                        "model_artifact": str(model_artifact),
                        "prediction": adv_pred,
                    }
                    # Persist the updated JSON immediately so regenerate calls write the model outputs back to disk
                    try:
                        self.save_json(match_data, path)
                    except Exception:
                        pass
        except Exception:
            pass

        prediction_engine = match_data.get(
            "prediction_engine", "Enhanced Intelligence v4.1"
        )
        phase2_active = "Phase 2 Lite" in prediction_engine
        engine_title = (
            "Enhanced Intelligence v4.1 + Phase 2 Lite"
            if phase2_active
            else prediction_engine
        )
        engine_mode_description = (
            "Phase 2 Lite Intelligence (Bayesian calibration • smart validation • 6-layer QA)"
            if phase2_active
            else "Enhanced Intelligence core engine with multi-layer analysis"
        )

        prediction_confidence_pct = (
            match_data.get("report_accuracy_probability", 0.65) * 100
        )
        data_confidence_pct = match_data.get("confidence", 0.5) * 100
        data_confidence_level = match_data.get("confidence_level", "Unknown").title()
        data_quality_score = match_data.get("data_quality_score", 75.0)
        reliability_score_value = reliability_metrics.get("score")

        # Safe top-level display variables (avoid KeyErrors on missing optional fields)
        home_team = match_data.get("home_team", match_data.get("home", "Home"))
        away_team = match_data.get("away_team", match_data.get("away", "Away"))
        date_display = match_data.get("date", "TBD")
        time_display = match_data.get("time", "TBD")

        # If this report is synthetic/fallback, add a visible banner and avoid making a full public summary
        is_synthetic = bool(
            match_data.get("is_synthetic")
            or match_data.get("fallback_used")
            or (match_data.get("prediction_method") or "").startswith("fallback")
            or (match_data.get("mode") or "") == "simulated"
        )
        if is_synthetic:
            synth_notice = match_data.get("synthetic_notice", "Synthetic/fallback report - not data-driven")
            synth_banner = [
                "# ⚠️ SYNTHETIC / FALLBACK REPORT",
                "",
                f"> {synth_notice}",
                "",
                "This report is intentionally segregated and should not be used for decision-making.",
            ]
            try:
                synthetic_summary_dir = Path("reports") / "simulated"
                synthetic_summary_dir.mkdir(parents=True, exist_ok=True)
                # Write a brief summary file to the synthetic area for auditing
                league = match_data.get("league") or match_data.get("competition", {}).get("code") or "unknown"
                out_dir = Path("reports") / "simulated" / league
                out_dir.mkdir(parents=True, exist_ok=True)
                with open(out_dir / f"{match_data.get('id', 'match')}_SYNTHETIC_SUMMARY.md", "w", encoding="utf-8") as out:
                    out.write("\n".join(synth_banner))
            except Exception:
                pass
            # Proceed to still build local variables for internal use, but do not add other public signals

        # Score probability breakdown (defensive to missing/invalid structures)
        score_probabilities = match_data.get("score_probabilities", [])
        score_probabilities_normalized = match_data.get(
            "score_probabilities_normalized", []
        )
        score_lines = []
        for idx, item in enumerate(score_probabilities[:3]):
            try:
                score, probability = item
            except Exception:
                continue
            normalized_value = None
            if idx < len(score_probabilities_normalized):
                norm_entry = score_probabilities_normalized[idx]
                if isinstance(norm_entry, (list, tuple)) and len(norm_entry) >= 2:
                    normalized_value = norm_entry[1]
            if normalized_value is None:
                normalized_value = max(0.0, min(10.0, probability / 2))
            score_lines.append(
                f"  - {score}: **{normalized_value:.0f}/10** ({probability:.1f}%)"
            )
        if not score_lines:
            score_lines.append("  - Data insufficient for detailed score probabilities")
        score_breakdown = "\n".join(score_lines)

        key_factors = intelligence.get(
            "key_factors", ["Standard analysis factors applied"]
        )
        key_factors_block = "\n".join([f"- {factor}" for factor in key_factors])

        overall_risk = "🟡 MEDIUM RISK"
        if reliability_score_value is not None:
            if reliability_score_value < 55:
                overall_risk = "🔴 HIGH RISK"
            elif reliability_score_value < 70:
                overall_risk = "🟡 MEDIUM RISK"
            else:
                overall_risk = "🟢 LOW RISK"
        else:
            overall_risk = (
                "🔴 HIGH RISK"
                if match_data.get("confidence", 0.33) < 0.4
                else (
                    "🟡 MEDIUM RISK"
                    if match_data.get("confidence", 0.33) < 0.7
                    else "🟢 LOW RISK"
                )
            )

        if reliability_metrics:
            indicator = reliability_metrics.get("indicator") or reliability_metrics.get(
                "level", "Unknown"
            )
            if reliability_score_value is not None:
                data_reliability = f"{indicator} ({reliability_score_value:.1f})"
            else:
                data_reliability = indicator
        else:
            data_reliability = (
                "🔴 Low"
                if data_quality_score < 60
                else "🟡 Medium"
                if data_quality_score < 80
                else "🟢 High"
            )
        prediction_stability = (
            "Volatile"
            if abs(
                match_data.get("home_win_probability", 43.7)
                - match_data.get("away_win_probability", 19.0)
            )
            < 15
            else "Stable"
        )

        head_to_head_total = h2h_data.get("total_meetings", 0)
        home_record_vs_opponent = (
            "No H2H Data"
            if head_to_head_total == 0
            else f"{h2h_data.get('home_advantage_vs_opponent', 0):.1f}%"
        )
        away_record_vs_opponent = (
            "No H2H Data"
            if head_to_head_total == 0
            else f"{h2h_data.get('away_record_vs_opponent', 0):.1f}%"
        )
        recent_h2h_form = (
            "No recent meetings"
            if head_to_head_total == 0
            else intelligence.get("recent_h2h_form", "No data")
        )
        avg_goals_home = (
            "No H2H Data"
            if head_to_head_total == 0
            else f"{h2h_data.get('avg_goals_for_when_home', 0):.1f}"
        )
        avg_goals_away = (
            "No H2H Data"
            if head_to_head_total == 0
            else f"{h2h_data.get('avg_goals_for_when_away', 0):.1f}"
        )

        def format_list(
            items: list[Any],
            default_text: str = "None reported",
            limit: Optional[int] = None,
        ) -> str:
            if not items:
                return default_text
            cleaned = [str(item) for item in items if item not in (None, "")]
            if not cleaned:
                return default_text
            if limit is not None:
                cleaned = cleaned[:limit]
            return ", ".join(cleaned)

        def format_recent_matches(
            recent_matches: list, team_name: str, max_matches: int = 5
        ) -> str:
            """Format recent match results into a clear readable format"""
            if not recent_matches:
                return "No recent match data available"

            result_emoji = {"W": "✅", "D": "🟡", "L": "❌"}
            lines = []
            for match in recent_matches[:max_matches]:
                result = match.get("result", "?")
                goals_for = match.get("goals_for", 0)
                goals_against = match.get("goals_against", 0)
                opponent = match.get("opponent", "Unknown")
                # Shorten opponent name if too long
                if len(opponent) > 20:
                    opponent = opponent[:18] + "..."
                emoji = result_emoji.get(result, "❓")
                lines.append(
                    f"  - {emoji} **{result}** {goals_for}-{goals_against} vs {opponent}"
                )

            return "\n".join(lines) if lines else "No recent match data"

        # Format recent match results for both teams
        home_recent_matches = home_perf.get("home", {}).get("recent_matches", [])
        away_recent_matches = away_perf.get("away", {}).get("recent_matches", [])

        home_recent_results = format_recent_matches(
            home_recent_matches, match_data.get("home_team", "Home")
        )
        away_recent_results = format_recent_matches(
            away_recent_matches, match_data.get("away_team", "Away")
        )

        tactical_adjustments = format_list(
            weather_data.get("impact_assessment", {}).get("tactical_adjustments"),
            "Normal game tactics expected",
            limit=2,
        )
        stadium_effects = format_list(
            weather_data.get("impact_assessment", {}).get("stadium_effects"),
            "Standard outdoor conditions",
            limit=2,
        )
        home_injury_concerns = format_list(
            player_data.get("home_team", {}).get("injury_concerns"),
            "Standard rotation expected",
        )
        away_injury_concerns = format_list(
            player_data.get("away_team", {}).get("injury_concerns"),
            "Standard rotation expected",
        )
        home_key_changes = format_list(
            team_news.get("home_team", {}).get("key_changes"),
            "Standard preparation expected",
        )
        away_key_changes = format_list(
            team_news.get("away_team", {}).get("key_changes"),
            "Standard preparation expected",
        )

        if reliability_metrics:
            rec_text = reliability_metrics.get(
                "recommendation", "Reliability insight unavailable"
            )
            reliability_score_line = (
                f"{reliability_metrics.get('indicator', reliability_metrics.get('level', 'Unknown'))} "
                f"{reliability_metrics.get('score', 0.0):.1f} – {rec_text}"
                if reliability_metrics.get("score") is not None
                else f"{reliability_metrics.get('indicator', reliability_metrics.get('level', 'Unknown'))} – {rec_text}"
            )
        else:
            reliability_score_line = "Reliability metrics unavailable for this match"

        if confidence_intervals and isinstance(confidence_intervals, dict):
            home_interval = confidence_intervals.get("home")
            draw_interval = confidence_intervals.get("draw")
            away_interval = confidence_intervals.get("away")
            def _call_format_interval(interval_val):
                # Prefer instance method if available, otherwise use module-level helper or fallback
                if callable(getattr(self, '_format_interval_segment', None)):
                    try:
                        return self._format_interval_segment(interval_val)
                    except Exception:
                        pass
                if callable(globals().get('_format_interval_segment')):
                    try:
                        return globals()['_format_interval_segment'](interval_val)
                    except Exception:
                        pass
                # Fallback
                try:
                    if isinstance(interval_val, (list, tuple)) and len(interval_val) >= 2:
                        return f"{float(interval_val[0]):.1f}% – {float(interval_val[1]):.1f}%"
                except Exception:
                    pass
                return "N/A"

            home_str = _call_format_interval(home_interval) if isinstance(home_interval, (list, tuple)) else "N/A"
            draw_str = _call_format_interval(draw_interval) if isinstance(draw_interval, (list, tuple)) else "N/A"
            away_str = _call_format_interval(away_interval) if isinstance(away_interval, (list, tuple)) else "N/A"

            confidence_interval_line = (
                f"Home {home_str}, Draw {draw_str}, Away {away_str}"
            )
        else:
            confidence_interval_line = "Interval unavailable – limited reliability data"

        calibration_summary = "No calibration required (high reliability)"
        if calibration_details:
            if calibration_details.get("applied"):
                shrink_pct = calibration_details.get("shrink_factor", 0.0) * 100.0
                if calibration_details.get("notes"):
                    calibration_summary = calibration_details["notes"][0]
                else:
                    calibration_summary = f"Probabilities calibrated with {shrink_pct:.1f}% neutral blend."
            elif calibration_details.get("notes"):
                calibration_summary = calibration_details["notes"][0]

            accuracy_adj = calibration_details.get("accuracy_adjustment")
            if accuracy_adj:
                calibration_summary += (
                    f" | Accuracy {accuracy_adj.get('original_probability', 0.0) * 100:.1f}% → "
                    f"{accuracy_adj.get('calibrated_probability', 0.0) * 100:.1f}%"
                )

        content = f"""# 🧠 {engine_title}: {home_team} vs {away_team}

## 🎯 Executive Summary

- **League:** {match_data.get("league", "Unknown")}
- **Date & Time:** {date_display} at {time_display}
- **Engine Mode:** {engine_mode_description}
- **Prediction Confidence:** **{prediction_confidence_pct:.1f}%** (Phase 2 Lite probability of correctness)
- **Data Confidence:** {data_confidence_pct:.1f}% ({data_confidence_level})
- **Data Quality Score:** {data_quality_score:.1f}%

## 🚀 Enhanced Features Applied

### ⚡ Multi-Season H2H Analysis

- **Data Sources:** {h2h_data.get("total_sources", 1)} source(s) including domestic leagues and European competitions
- **Historical Depth:** {head_to_head_total} total meetings analyzed with weighted recency

### 📈 Form Summary

| Team | Form Score | Momentum | Streak | Scoring | Conceding |
|------|------------|----------|--------|---------|-----------|
| **{match_data.get("home_team", "Home")[:20]}** | {home_perf.get("home", {}).get("weighted_form_score", 50):.0f}% | {home_perf.get("home", {}).get("momentum_direction", "Stable")} | {home_perf.get("home", {}).get("current_streak", "N/A")} | {home_perf.get("home", {}).get("scoring_form", 1.3):.1f}/game | {home_perf.get("home", {}).get("defensive_form", 1.2):.1f}/game |
| **{match_data.get("away_team", "Away")[:20]}** | {away_perf.get("away", {}).get("weighted_form_score", 50):.0f}% | {away_perf.get("away", {}).get("momentum_direction", "Stable")} | {away_perf.get("away", {}).get("current_streak", "N/A")} | {away_perf.get("away", {}).get("scoring_form", 1.0):.1f}/game | {away_perf.get("away", {}).get("defensive_form", 1.6):.1f}/game |

### 🌤️ Weather Intelligence System

- **Conditions Severity:** {weather_data.get("impact_assessment", {}).get("weather_severity", "MILD")}
- **Goal Impact Modifier:** {(weather_data.get("impact_assessment", {}).get("goal_modifier") or 1.0):.2f}x
- **Playing Style Effect:** {weather_data.get("impact_assessment", {}).get("playing_style_effect", "Normal")}

### 💾 Smart Cache System

- **Cache Version:** 3.0 with intelligent validation and cleanup
- **Data Freshness:** Optimized TTL based on data type (H2H: 4hrs, Stats: 2hrs, Weather: 30min)

## 📊 Core Prediction

### Expected Outcome

- **Expected Final Score:** {match_data.get("expected_final_score", "N/A")} ⭐ **{match_data.get("score_probability_normalized", 5.0):.0f}/10** ({match_data.get("score_probability", 10.0):.1f}%)
- **Top 3 Scores Combined:** ⭐ **{match_data.get("top3_probability_normalized", 7.0):.0f}/10** ({match_data.get("top3_combined_probability", 25.0):.1f}%)
- **Expected Goals:** {match_data.get("expected_home_goals", 0.0):.1f} - {match_data.get("expected_away_goals", 0.0):.1f}
- **Recommendation:** {match_data.get("recommendation", "N/A")}
- **Processing Time:** {match_data.get("processing_time", 0.0):.2f}s

### Score Probability Breakdown

- **Most Likely Scores (1-10 Scale):**
{score_breakdown}

### Betting Market Analysis

- **Over 2.5 Goals:** {match_data.get("over_2_5_goals_probability", 0.0):.1f}%
- **Both Teams to Score:** {match_data.get("both_teams_score_probability", 0.0):.1f}%
- **Alternative Scores:** {", ".join(match_data.get("alternative_scores", []))}

### Win Probabilities

 - **{match_data.get("home_team", "Home")} Win:** {match_data.get("home_win_probability", 0.0):.1f}%
- **Draw:** {match_data.get("draw_probability", 0.0):.1f}%
- **{match_data.get("away_team", "Away")} Win:** {match_data.get("away_win_probability", 0.0):.1f}%

## 🎲 Advanced Predictions (Phase 4-7 Enhanced)

{self._format_advanced_predictions_section(match_data)}

## 🔍 Intelligence Analysis

### Head-to-Head History

- **Total Meetings:** {head_to_head_total}
- **Home Team Record vs Opponent:** {home_record_vs_opponent}
- **Away Team Record vs Opponent:** {away_record_vs_opponent}
- **Recent H2H Form:** {recent_h2h_form}
- **Average Goals (Home):** {avg_goals_home}
- **Average Goals (Away):** {avg_goals_away}

### Home/Away Performance Analysis

#### {match_data["home_team"]} (Enhanced Home Analysis)

**📋 Last 5 Home Results:**

{home_recent_results}

**Traditional Stats:**

- **Home Win Rate:** {home_perf.get("home", {}).get("win_rate", 50):.1f}% ({home_perf.get("home", {}).get("matches", 0)} matches)
- **Home Goals Per Game:** {home_perf.get("home", {}).get("avg_goals_for", 1.5):.1f}
- **Home Goals Conceded:** {home_perf.get("home", {}).get("avg_goals_against", 1.2):.1f}

**Form Intelligence:**

- **Form Score:** {home_perf.get("home", {}).get("weighted_form_score", 50):.1f}% | **Momentum:** {home_perf.get("home", {}).get("momentum_direction", "Stable")} | **Streak:** {home_perf.get("home", {}).get("current_streak", "No active streak")}
- **Form Quality:** {home_perf.get("home", {}).get("form_quality", "Average")} | **Consistency:** {home_perf.get("home", {}).get("consistency_score", 50):.0f}%
- **Scoring Form:** {home_perf.get("home", {}).get("scoring_form", 1.3):.2f} goals/game | **Defensive Form:** {home_perf.get("home", {}).get("defensive_form", 1.2):.2f} conceded/game

#### {match_data["away_team"]} (Enhanced Away Analysis)

**📋 Last 5 Away Results:**

{away_recent_results}

**Traditional Stats:**

- **Away Win Rate:** {away_perf.get("away", {}).get("win_rate", 30):.1f}% ({away_perf.get("away", {}).get("matches", 0)} matches)
- **Away Goals Per Game:** {away_perf.get("away", {}).get("avg_goals_for", 1.2):.1f}
- **Away Goals Conceded:** {away_perf.get("away", {}).get("avg_goals_against", 1.6):.1f}

**Form Intelligence:**

- **Form Score:** {away_perf.get("away", {}).get("weighted_form_score", 50):.1f}% | **Momentum:** {away_perf.get("away", {}).get("momentum_direction", "Stable")} | **Streak:** {away_perf.get("away", {}).get("current_streak", "No active streak")}
- **Form Quality:** {away_perf.get("away", {}).get("form_quality", "Average")} | **Consistency:** {away_perf.get("away", {}).get("consistency_score", 50):.0f}%
- **Scoring Form:** {away_perf.get("away", {}).get("scoring_form", 1.0):.2f} goals/game | **Defensive Form:** {away_perf.get("away", {}).get("defensive_form", 1.6):.2f} conceded/game

### ⏰ Goal Timing Prediction

- **First Half Goal Probability:** {goal_timing.get("first_half_goal_probability", 45):.0f}%
- **Second Half Goal Probability:** {goal_timing.get("second_half_goal_probability", 55):.0f}%
- **Late Goal Likelihood:** {goal_timing.get("late_goal_likelihood", 20):.0f}%
- **Early Goal Likelihood:** {goal_timing.get("early_goal_likelihood", 15):.0f}%
- **Home Attack Style:** {goal_timing.get("home_attack_style", "balanced").title()}
- **Away Attack Style:** {goal_timing.get("away_attack_style", "balanced").title()}

## 📈 Data Quality Enhancements

### Player Availability

#### {match_data["home_team"]} Players

- **Squad Status:** {"Real-time data unavailable" if not player_data.get("home_team") else "Live injury tracking active"}
- **Expected Lineup Strength:** {"⚠️ Data unavailable" if not player_data.get("home_team") or player_data.get("home_team", {}).get("expected_lineup_strength") is None else f"{player_data.get('home_team', {}).get('expected_lineup_strength', 85):.1f}%"}
- **Data Source:** {"⚠️ No injury API configured" if not player_data.get("home_team") else "Live injury database"}
- **Injury Impact:** {"⚠️ Real injury data unavailable" if not player_data.get("home_team") else home_injury_concerns}

#### {match_data["away_team"]} Players

- **Squad Status:** {"Real-time data unavailable" if not player_data.get("away_team") else "Live injury tracking active"}
- **Expected Lineup Strength:** {"⚠️ Data unavailable" if not player_data.get("away_team") or player_data.get("away_team", {}).get("expected_lineup_strength") is None else f"{player_data.get('away_team', {}).get('expected_lineup_strength', 85):.1f}%"}
- **Data Source:** {"⚠️ No injury API configured" if not player_data.get("away_team") else "Live injury database"}
- **Injury Impact:** {"⚠️ Real injury data unavailable" if not player_data.get("away_team") else away_injury_concerns}

### 🌤️ Enhanced Weather Intelligence System

**Current Conditions:**

- **Temperature:** {weather_data.get("conditions", {}).get("temperature", "Unknown")}{("°C" if weather_data.get("conditions", {}).get("temperature") else " (Match day forecast pending)")}
- **Precipitation:** {weather_data.get("conditions", {}).get("precipitation", "TBD")}{("mm" if weather_data.get("conditions", {}).get("precipitation") is not None else " (Forecast pending)")}
- **Wind Speed:** {weather_data.get("conditions", {}).get("wind_speed", "Normal expected")}{(" km/h" if weather_data.get("conditions", {}).get("wind_speed") else "")}
- **Humidity:** {weather_data.get("conditions", {}).get("humidity", "Normal")}{("%" if weather_data.get("conditions", {}).get("humidity") else "")}

**Enhanced Intelligence Analysis:**

- **Weather Severity:** {weather_data.get("impact_assessment", {}).get("weather_severity", "MILD")} 🌡️
- **Goal Impact Modifier:** {weather_data.get("impact_assessment", {}).get("goal_modifier", 1.0):.2f}x (affects expected scoring)
- **Playing Style Effect:** {weather_data.get("impact_assessment", {}).get("playing_style_effect", "Normal").replace("_", " ").title()}
- **Tactical Adjustments:** {tactical_adjustments}
- **Stadium Effects:** {stadium_effects}
- **Conditions Summary:** {weather_data.get("impact_assessment", {}).get("conditions_summary", "Good playing conditions expected")}

### Referee Analysis

- **Referee:** {referee_data.get("name", "To Be Announced")}
- **Data Availability:** {"Limited referee data" if referee_data.get("name") == "Unknown Referee" else "Full referee profile available"}
- **Home Bias:** {"⚠️ Data unavailable" if referee_data.get("home_bias_pct") is None else f"{referee_data.get('home_bias_pct', 51):.1f}%"}
- **Match Experience:** {"⚠️ Data unavailable" if referee_data.get("cards_per_game") is None else f"{referee_data.get('cards_per_game', 3.5):.1f} cards/game avg"}
- **Average Penalties Per Game:** {"⚠️ Data unavailable" if referee_data.get("penalties_per_game") is None else f"{referee_data.get('penalties_per_game', 0.2):.1f}"}
- **Strictness Level:** {referee_data.get("strict_level", "unknown").title()}
- **Experience Level:** {referee_data.get("experience_level", "unknown").title()}

### Team News & Tactical Analysis

#### {match_data["home_team"]} Tactics

- **Formation Analysis:** {"Predicted 4-3-3/4-4-2 (standard)" if not team_news.get("home_team") else team_news.get("home_team", {}).get("formation_expected", "Formation TBD")}
- **Tactical Approach:** {"Based on recent form analysis" if not team_news.get("home_team") else team_news.get("home_team", {}).get("tactical_approach", "balanced").title()}
- **Team Strength:** {"⚠️ Data unavailable" if not team_news.get("home_team") or team_news.get("home_team", {}).get("lineup_strength") is None else f"Live assessment: {team_news.get('home_team', {}).get('lineup_strength', 85):.1f}%"}
- **Pre-Match Intel:** {"⚠️ Team news unavailable" if not team_news.get("home_team") else home_key_changes}

#### {match_data["away_team"]} Tactics

- **Formation Analysis:** {"⚠️ Data unavailable" if not team_news.get("away_team") else team_news.get("away_team", {}).get("formation_expected", "Formation TBD")}
- **Tactical Approach:** {"⚠️ Data unavailable" if not team_news.get("away_team") else team_news.get("away_team", {}).get("tactical_approach", "balanced").title()}
- **Team Strength:** {"⚠️ Data unavailable" if not team_news.get("away_team") or team_news.get("away_team", {}).get("lineup_strength") is None else f"Live assessment: {team_news.get('away_team', {}).get('lineup_strength', 85):.1f}%"}
- **Pre-Match Intel:** {"Standard preparation expected" if not team_news.get("away_team") else away_key_changes}

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
- **Head-to-Head Data Availability:** {"✅ Good" if head_to_head_total >= 3 else "⚠️ Limited"}
- **Recent Form Data:** {"✅ Comprehensive" if home_perf.get("home", {}).get("matches", 0) >= 10 else "⚠️ Limited"}
- **Enhanced Data Integration:** {"✅ Full Integration" if data_quality_score >= 80 else "⚠️ Partial Data"}

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
- **Generated:** {match_data.get("generated_at", datetime.now().isoformat())}

---

## Disclaimer

⚠️ This analysis is for educational and informational purposes only. Not intended for betting or financial decisions.
"""

        with open(f"{path}/summary.md", "w", encoding="utf-8") as f:
            f.write(content)

    # ================================================================
    # ==================== START OF save_image SECTION ====================
    # ================================================================
    def save_image(self, match_data: JSONDict, path: Union[str, Path]) -> None:
        """Generate visually stunning match prediction card with modern design, professional spacing, and gauges

        This function is defensive: it will not raise exceptions for missing optional fields and will
        write a placeholder image if anything goes wrong during rendering.
        """
        try:
            reliability_metrics = match_data.get("reliability_metrics", {}) or {}
            reliability_score = reliability_metrics.get("score")

            # Use safe defaults for required display fields
            home_team = match_data.get("home_team", match_data.get("home", "Home"))
            away_team = match_data.get("away_team", match_data.get("away", "Away"))
            date = match_data.get("date", "")
            time_str = match_data.get("time", "")
            expected_final_score = match_data.get("expected_final_score", "N/A")
            expected_home_goals = float(
                match_data.get("expected_home_goals", 0.0) or 0.0
            )
            expected_away_goals = float(
                match_data.get("expected_away_goals", 0.0) or 0.0
            )
            # Use report_accuracy_probability as canonical source for displayed confidence; fallback to 'confidence' if present
            confidence = (
                float(
                    match_data.get(
                        "report_accuracy_probability", match_data.get("confidence", 0.0)
                    )
                    or 0.0
                )
                * 100
            )
            processing_time = float(match_data.get("processing_time", 0.0) or 0.0)

            # Read visual/layout defaults from settings (with safe fallbacks)
            fig_size = (
                self._settings.get("constants", {})
                .get("layout", {})
                .get("figure_size", [14, 32])
            )
            fig, ax = plt.subplots(figsize=(fig_size[0], fig_size[1]))
            ax.set_xlim(0, 10)
            ax.set_ylim(0, 32)
            ax.axis("off")

            fig.patch.set_facecolor("#FFFFFF")
            fig.subplots_adjust(left=0.05, right=0.95, top=0.98, bottom=0.02)

            # Get league name for theme selection
            league_name = match_data.get("league", "La Liga")

            # Load visual constants with professional design system
            vis = self._settings.get("constants", {}).get("visual_defaults", {})

            # Get league-specific theme
            league_theme = ProfessionalDesignSystem.get_theme(league_name)

            # Build color palette with league theme
            base_colors = ProfessionalDesignSystem.BASE_COLORS.copy()
            colors = self._settings.get("constants", {}).get(
                "colors", base_colors.copy()
            )

            # Override with professional defaults and league theme
            colors.update(
                {
                    "header_bg": league_theme["primary"],
                    "main_bg": "#FFFFFF",
                    "main_border": "#E0E0E0",
                    "results_bg": league_theme["light_primary"],
                    "results_bg_edge": league_theme["primary"],
                    "text_main": "#1A1A1A",
                    "text_secondary": "#666666",
                    "gauge_bg": "#F0F0F0",
                    "section_bg": "#F8F9FA",
                    "separator": "#E0E0E0",
                    "likely_home": league_theme["primary"],
                    "likely_draw": "#7F8C8D",
                    "likely_away": league_theme["accent"],
                    "perf_bg": league_theme["primary"],
                    "goals_bg": league_theme["secondary"],
                    "underline": league_theme["primary"],
                    "shadow": "#00000015",
                }
            )

            # font sizes
            header_fs = vis.get("header_fontsize", 14)
            subtitle_fs = vis.get("subtitle_fontsize", 11)
            section_title_fs = vis.get("section_title_fontsize", 11)
            label_fs = vis.get("label_fontsize", 11)
            value_fs = vis.get("value_fontsize", 14)

            # Draw header
            shadow = FancyBboxPatch(
                (0.22, 0.28),
                9.6,
                19.4,
                boxstyle="round,pad=0.02,rounding_size=0.05",
                facecolor=colors.get("shadow", "#000000"),
                alpha=0.06,
                edgecolor="none",
                zorder=0,
            )
            ax.add_patch(shadow)
            main_box = FancyBboxPatch(
                (0.2, 0.3),
                9.6,
                19.4,
                boxstyle="round,pad=0.02,rounding_size=0.05",
                facecolor=colors.get("main_bg", "#fdfdfd"),
                edgecolor=colors.get("main_border", "#7f8c8d"),
                linewidth=2,
                zorder=1,
            )
            ax.add_patch(main_box)

            header_bg = Rectangle(
                (0.4, 27.5),
                9.2,
                4.0,
                facecolor=colors.get("header_bg", "#003DA5"),
                alpha=0.7,
                zorder=2,
            )
            ax.add_patch(header_bg)

            ax.text(
                5,
                30.8,
                f"{home_team}",
                ha="center",
                va="center",
                fontsize=header_fs,
                fontweight="bold",
                color="white",
                zorder=3,
                fontname="DejaVu Sans",
            )
            ax.text(
                5,
                29.8,
                "VS",
                ha="center",
                va="center",
                fontsize=subtitle_fs - 2,
                fontweight="bold",
                color="white",
                alpha=0.9,
                zorder=3,
                fontname="DejaVu Sans",
            )
            ax.text(
                5,
                28.8,
                f"{away_team}",
                ha="center",
                va="center",
                fontsize=header_fs,
                fontweight="bold",
                color="white",
                zorder=3,
                fontname="DejaVu Sans",
            )
            ax.text(
                5,
                27.9,
                f"{match_data.get('league', 'League')} • {date} • {time_str}",
                ha="center",
                va="center",
                fontsize=14,
                fontweight="bold",
                color="white",
                alpha=0.95,
                zorder=3,
                fontname="DejaVu Sans",
            )

            # Predicted score
            ax.text(
                5,
                25.2,
                "PREDICTED FINAL SCORE",
                ha="center",
                va="center",
                fontsize=section_title_fs,
                fontweight="bold",
                color=colors.get("text_main", "#111111"),
            )
            ax.text(
                5,
                24.2,
                f"{self.format_team_name_for_display(home_team)} {expected_final_score} {self.format_team_name_for_display(away_team)}",
                ha="center",
                va="center",
                fontsize=value_fs,
                fontweight="bold",
                color=colors.get("text_main", "#111111"),
            )

            ax.text(
                5,
                23.3,
                f"Expected Goals: {self.format_team_name_for_display(home_team)} {expected_home_goals:.1f} - {expected_away_goals:.1f} {self.format_team_name_for_display(away_team)}",
                ha="center",
                va="center",
                fontsize=label_fs,
                fontweight="bold",
                color=colors.get("text_main", "#111111"),
            )

            # Confidence metrics (initial / summary values were removed to avoid duplicate rendering; drawn in SECTION 1 below)

            # NOTE: saving moved to the end of the function to ensure all drawing operations are complete before writing the image.
            plt.tight_layout()
            # Saving deferred to the end of the function
            pass
        except Exception as e:
            safe_print(f"⚠️  save_image encountered an error: {e}")
            # Attempt to create a minimal placeholder image so callers can rely on file existence
            try:
                from PIL import Image, ImageDraw, ImageFont

                img_path = f"{path}/prediction_card.png"
                w, h = 1200, 800
                img = Image.new("RGB", (w, h), color="#ffffff")
                draw = ImageDraw.Draw(img)
                try:
                    font_bold = ImageFont.truetype("DejaVuSans-Bold.ttf", 36)
                except Exception:
                    font_bold = None
                draw.text(
                    (w // 2, h // 2),
                    "Image generation failed",
                    fill="#000000",
                    anchor="ms",
                    font=font_bold,
                )
                img.save(img_path, format="PNG")
                print(f"   • Wrote Pillow placeholder image at: {img_path}")
            except Exception as e2:
                print(f"   • Could not write placeholder image: {e2}")

        # =================================================================
        # SECTION 1: MATCH CONFIDENCE METRICS (Top - Light Blue Background)
        # =================================================================
        # Section background group
        metrics_bg = Rectangle(
            (0.5, 20.5),
            9.0,
            2.2,
            facecolor="#e8f4f8",
            alpha=0.6,
            edgecolor="#3498db",
            linewidth=2,
            zorder=1,
        )
        ax.add_patch(metrics_bg)

        # Section category label
        ax.text(
            0.8,
            22.3,
            "CONFIDENCE METRICS",
            ha="left",
            va="center",
            fontsize=14,
            fontweight="bold",
            color="#2c3e50",
            zorder=2,
            fontname="DejaVu Sans",
        )

        # Divider line - lowered to avoid text
        ax.plot(
            [0.7, 9.3],
            [21.8, 21.8],
            color="#3498db",
            linewidth=1.5,
            zorder=2,
            alpha=0.5,
        )

        # Confidence and Data Quality display with color coding (no boxes)
        # Confidence already computed above as canonical source; just get display color
        conf_color = ProfessionalDesignSystem.get_color_for_probability(confidence)

        data_quality = match_data.get("data_quality_score", 75.0)
        dq_color = ProfessionalDesignSystem.get_color_for_probability(data_quality)

        # Confidence display (left) - no box - moved up for better spacing
        ax.text(
            2.65,
            21.6,
            f"{int(round(confidence))}%",
            ha="center",
            va="center",
            fontsize=22,
            fontweight="bold",
            color=conf_color,
            zorder=3,
            fontname="DejaVu Sans",
        )
        ax.text(
            2.65,
            20.9,
            "Prediction",
            ha="center",
            va="center",
            fontsize=14,
            color="#000000",
            fontweight="bold",
            zorder=3,
            fontname="DejaVu Sans",
        )
        ax.text(
            2.65,
            20.6,
            "Confidence",
            ha="center",
            va="center",
            fontsize=14,
            color="#000000",
            fontweight="bold",
            zorder=3,
            fontname="DejaVu Sans",
        )

        # Data Quality display (right) - no box
        ax.text(
            7.35,
            21.6,
            f"{int(round(data_quality))}%",
            ha="center",
            va="center",
            fontsize=22,
            fontweight="bold",
            color=dq_color,
            zorder=3,
            fontname="DejaVu Sans",
        )
        ax.text(
            7.35,
            20.9,
            "Data",
            ha="center",
            va="center",
            fontsize=14,
            color="#000000",
            fontweight="bold",
            zorder=3,
            fontname="DejaVu Sans",
        )
        ax.text(
            7.35,
            20.6,
            "Quality",
            ha="center",
            va="center",
            fontsize=14,
            color="#000000",
            fontweight="bold",
            zorder=3,
            fontname="DejaVu Sans",
        )

        # Add spacing after confidence metrics
        # (blank space 19.0-18.8)

        # =================================================================
        # SECTION 2: PREDICTION ANALYSIS (Middle - Light Green Background)
        # =================================================================
        # Section background group - LARGE SECTION
        analysis_bg = Rectangle(
            (0.5, 1.0),
            9.0,
            18.5,
            facecolor="#e8f8f0",
            alpha=0.6,
            edgecolor="#27ae60",
            linewidth=2,
            zorder=1,
        )
        ax.add_patch(analysis_bg)

        # Section category label
        ax.text(
            0.8,
            19.2,
            "PREDICTION ANALYSIS",
            ha="left",
            va="center",
            fontsize=14,
            fontweight="bold",
            color="#2c3e50",
            zorder=2,
            fontname="DejaVu Sans",
        )

        # Divider line
        ax.plot(
            [0.7, 9.3],
            [19.0, 19.0],
            color="#27ae60",
            linewidth=1.5,
            zorder=2,
            alpha=0.5,
        )

        # Add spacing after prediction analysis
        # (blank space 19.0-18.8)

        # ===== MATCH OUTCOME PROBABILITIES =====
        ax.text(
            5,
            18.5,
            "Match Outcome Probability",
            ha="center",
            va="center",
            fontsize=13,
            fontweight="bold",
            color=colors.get("text_main", "#1A1A1A"),
            zorder=2,
            fontname="DejaVu Sans",
        )

        # Win/Draw/Away probabilities
        home_win = match_data.get("home_win_probability", 0)
        draw = match_data.get("draw_probability", 0)
        away_win = match_data.get("away_win_probability", 0)

        home_team = match_data.get("home_team", "Home")
        away_team = match_data.get("away_team", "Away")

        col_labels = [home_team, "Draw", away_team]
        col_x = [1.8, 5.0, 8.2]
        col_values = [int(round(home_win)), int(round(draw)), int(round(away_win))]

        col_colors = [
            ProfessionalDesignSystem.get_color_for_probability(home_win),
            ProfessionalDesignSystem.get_color_for_probability(draw),
            ProfessionalDesignSystem.get_color_for_probability(away_win),
        ]

        # Uniform box sizing - SAME HEIGHT FOR ALL
        box_width = 2.2
        box_height = 1.5
        box_y = 16.5

        for i in range(3):
            col_x_pos = col_x[i]
            col_bg = Rectangle(
                (col_x_pos - box_width / 2, box_y),
                box_width,
                box_height,
                facecolor="white",
                edgecolor=col_colors[i],
                linewidth=5.0,
                zorder=2,
                alpha=0.9,
            )
            ax.add_patch(col_bg)

            ax.text(
                col_x_pos,
                box_y + 1.1,
                f"{col_values[i]}%",
                ha="center",
                va="center",
                fontsize=22,
                fontweight="bold",
                color=col_colors[i],
                zorder=3,
                fontname="DejaVu Sans",
            )

            label = col_labels[i]
            if len(label) > 15:
                words = label.split()
                if len(words) > 1:
                    label = f"{' '.join(words[:-1])}\\n{words[-1]}"

            ax.text(
                col_x_pos,
                box_y + 0.35,
                label,
                ha="center",
                va="center",
                fontsize=14,
                color="#000000",
                zorder=3,
                fontweight="bold",
                fontname="DejaVu Sans",
            )

        # ===== TEAM FORM (with consistent theme colors, not probability-based) =====
        ax.text(
            5,
            14.8,
            "Team Form Assessment",
            ha="center",
            va="center",
            fontsize=13,
            fontweight="bold",
            color=colors.get("text_main", "#1A1A1A"),
            zorder=2,
            fontname="DejaVu Sans",
        )

        home_form = match_data.get("home_performance_analysis", {}).get("home", {})
        away_form = match_data.get("away_performance_analysis", {}).get("away", {})

        home_form_score = home_form.get("weighted_form_score", 50)
        away_form_score = away_form.get("weighted_form_score", 50)

        # Get win rates to determine team strength tier
        home_win_rate = home_form.get("win_rate", 0.5) * 100
        away_win_rate = away_form.get("win_rate", 0.5) * 100

        def get_strength_tier(win_rate):
            if win_rate >= 65:
                return "Elite", "#27AE60"
            elif win_rate >= 50:
                return "Strong", "#17A2B8"
            elif win_rate >= 35:
                return "Average", "#F39C12"
            else:
                return "Struggling", "#E74C3C"

        home_tier, home_tier_color = get_strength_tier(home_win_rate)
        away_tier, away_tier_color = get_strength_tier(away_win_rate)

        col_x = [2.5, 7.5]
        col_values = [int(round(home_form_score)), int(round(away_form_score))]
        col_labels = ["Home Team", "Away Team"]
        col_tiers = [(home_tier, home_tier_color), (away_tier, away_tier_color)]

        # Use PROBABILITY-BASED colors for form scores (not fixed theme colors)
        form_box_colors = [
            ProfessionalDesignSystem.get_color_for_probability(home_form_score),
            ProfessionalDesignSystem.get_color_for_probability(away_form_score),
        ]

        box_width_2 = 3.3
        form_box_height = 1.5
        form_box_y = 13.0

        for i in range(2):
            col_x_pos = col_x[i]
            # No box - just text with color coding
            ax.text(
                col_x_pos,
                form_box_y + 1.1,
                f"{col_values[i]}%",
                ha="center",
                va="center",
                fontsize=22,
                fontweight="bold",
                color=form_box_colors[i],
                zorder=3,
                fontname="DejaVu Sans",
            )

            ax.text(
                col_x_pos,
                form_box_y + 0.35,
                col_labels[i],
                ha="center",
                va="center",
                fontsize=14,
                color="#000000",
                fontweight="bold",
                zorder=3,
                fontname="DejaVu Sans",
            )

            # Show team strength tier below label
            tier_label, tier_color = col_tiers[i]
            ax.text(
                col_x_pos,
                form_box_y - 0.1,
                f"({tier_label})",
                ha="center",
                va="center",
                fontsize=11,
                color=tier_color,
                fontweight="bold",
                zorder=3,
                fontname="DejaVu Sans",
            )

        # ===== LAST 5 MATCHES W/D/L VISUALIZATION =====
        # Extract recent match results from performance data
        home_recent = home_form.get("recent_matches", [])[:5]
        away_recent = away_form.get("recent_matches", [])[:5]

        # W/D/L color mapping
        result_colors = {"W": "#27AE60", "D": "#F39C12", "L": "#E74C3C"}
        form_y = 12.35

        # Home team last 5 (left side)
        home_form_str = (
            [m.get("result", "?") for m in home_recent] if home_recent else []
        )
        for idx, result in enumerate(home_form_str[:5]):
            x_offset = 1.5 + idx * 0.5
            color = result_colors.get(result, "#95a5a6")
            ax.text(
                x_offset,
                form_y,
                "●",
                ha="center",
                va="center",
                fontsize=14,
                color=color,
                zorder=3,
                fontname="DejaVu Sans",
            )

        # Away team last 5 (right side)
        away_form_str = (
            [m.get("result", "?") for m in away_recent] if away_recent else []
        )
        for idx, result in enumerate(away_form_str[:5]):
            x_offset = 6.5 + idx * 0.5
            color = result_colors.get(result, "#95a5a6")
            ax.text(
                x_offset,
                form_y,
                "●",
                ha="center",
                va="center",
                fontsize=14,
                color=color,
                zorder=3,
                fontname="DejaVu Sans",
            )

        # Form legend (compact)
        if home_form_str or away_form_str:
            ax.text(
                5,
                form_y,
                "Last 5:",
                ha="center",
                va="center",
                fontsize=11,
                color="#666666",
                zorder=3,
                fontname="DejaVu Sans",
            )

        if home_form_score > away_form_score + 5:
            form_advantage = f"{home_team} in better form"
            advantage_color = form_box_colors[0]
        elif away_form_score > home_form_score + 5:
            form_advantage = f"{away_team} in better form"
            advantage_color = form_box_colors[1]
        else:
            form_advantage = "Teams in similar form"
            advantage_color = colors.get("likely_draw", "#7F8C8D")

        ax.text(
            5,
            12.0,
            form_advantage,
            ha="center",
            va="center",
            fontsize=14,
            fontweight="bold",
            color=advantage_color,
            zorder=3,
            fontname="DejaVu Sans",
        )

        # ===== EXPECTED GOALS =====
        ax.text(
            5,
            11.3,
            "Expected Goals Prediction",
            ha="center",
            va="center",
            fontsize=13,
            fontweight="bold",
            color=colors.get("text_main", "#1A1A1A"),
            zorder=2,
            fontname="DejaVu Sans",
        )

        # Get expected goals for dynamic calculation of fallbacks
        exp_home = match_data.get("expected_home_goals", 1.5)
        exp_away = match_data.get("expected_away_goals", 1.2)
        total_exp = exp_home + exp_away

        # Calculate dynamic fallbacks using Poisson if not provided
        import math

        default_over_2_5 = (
            1
            - sum(
                (total_exp**k * math.exp(-total_exp)) / math.factorial(k)
                for k in range(3)
            )
        ) * 100
        default_btts = (1 - math.exp(-exp_home)) * (1 - math.exp(-exp_away)) * 100

        over_prob = match_data.get("over_2_5_goals_probability", default_over_2_5)
        btts_prob = match_data.get("both_teams_score_probability", default_btts)

        col_x = [2.5, 7.5]
        col_values = [int(round(over_prob)), int(round(btts_prob))]
        col_labels = ["More Than 2 Goals", "Both Teams Score"]

        col_colors = [
            ProfessionalDesignSystem.get_color_for_probability(over_prob),
            ProfessionalDesignSystem.get_color_for_probability(btts_prob),
        ]

        box_width_3 = 3.3
        goals_box_height = 1.5
        goals_box_y = 9.6

        for i in range(2):
            col_x_pos = col_x[i]
            # No box - just text with color coding
            ax.text(
                col_x_pos,
                goals_box_y + 1.1,
                f"{col_values[i]}%",
                ha="center",
                va="center",
                fontsize=22,
                fontweight="bold",
                color=col_colors[i],
                zorder=3,
                fontname="DejaVu Sans",
            )

            ax.text(
                col_x_pos,
                goals_box_y + 0.35,
                col_labels[i],
                ha="center",
                va="center",
                fontsize=14,
                color="#000000",
                fontweight="bold",
                zorder=3,
                fontname="DejaVu Sans",
            )

        # ===== MATCH FACTORS (Individual Boxes) =====
        ax.text(
            5,
            9.0,
            "Match Factors",
            ha="center",
            va="center",
            fontsize=13,
            fontweight="bold",
            color=colors.get("text_main", "#1A1A1A"),
            zorder=2,
            fontname="DejaVu Sans",
        )

        # Get factor data
        weather_data = match_data.get("weather_conditions", {})
        weather_impact = weather_data.get("impact_assessment", {})
        weather_modifier = weather_impact.get("goal_modifier", 1.0)

        h2h_data = match_data.get("head_to_head_analysis", {})
        h2h_meetings = h2h_data.get("total_meetings", 0)

        home_strength = (
            match_data.get("player_availability", {})
            .get("home_team", {})
            .get("expected_lineup_strength")
        )
        away_strength = (
            match_data.get("player_availability", {})
            .get("away_team", {})
            .get("expected_lineup_strength")
        )

        # Extract actual weather data for display with impact analysis
        weather_conditions = weather_data.get("conditions", {})
        weather_impact = weather_data.get("impact_assessment", {})
        weather_temp = weather_conditions.get("temperature")
        weather_desc = weather_conditions.get("conditions", "")
        weather_wind = weather_conditions.get("wind_speed", 0)
        weather_precip = weather_conditions.get("precipitation", 0)
        goal_modifier = weather_impact.get("goal_modifier", 1.0)
        weather_severity = weather_impact.get("weather_severity", "MILD")
        playing_style = weather_impact.get("playing_style_effect", "normal")
        tactical_notes = weather_impact.get("tactical_adjustments", [])

        # Generate weather impact description based on conditions
        weather_effects = []
        if weather_temp is not None:
            if weather_temp < 5:
                weather_effects.append("Cold slows play")
            elif weather_temp > 28:
                weather_effects.append("Heat causes fatigue")

        if weather_wind > 25:
            weather_effects.append("Strong wind affects accuracy")
        elif weather_wind > 15:
            weather_effects.append("Wind impacts long balls")

        if weather_precip > 5:
            weather_effects.append("Heavy rain slows game")
        elif weather_precip > 1:
            weather_effects.append("Wet pitch faster play")

        # Add goal modifier effect
        if goal_modifier < 0.92:
            weather_effects.append(f"Goals ↓{int((1 - goal_modifier) * 100)}%")
        elif goal_modifier > 1.08:
            weather_effects.append(f"Goals ↑{int((goal_modifier - 1) * 100)}%")

        # Create weather display text
        if weather_temp is not None:
            weather_text = f"{weather_temp:.0f}°C {weather_desc[:6]}"
            # Determine color based on impact severity
            if weather_severity == "SEVERE" or weather_temp < 3 or weather_temp > 32:
                weather_color = "#e74c3c"  # Red - extreme
            elif (
                weather_severity == "MODERATE"
                or weather_temp < 8
                or weather_temp > 28
                or weather_wind > 20
            ):
                weather_color = "#f39c12"  # Orange - moderate impact
            else:
                weather_color = "#27ae60"  # Green - ideal conditions
        elif goal_modifier > 1.05:
            weather_text = "High Scoring"
            weather_color = "#e74c3c"
        elif goal_modifier < 0.95:
            weather_text = "Low Scoring"
            weather_color = "#3498db"
        else:
            weather_text = "Neutral"
            weather_color = "#7F8C8D"

        # Build weather impact summary for display
        if weather_effects:
            weather_impact_text = weather_effects[0][:18]  # First effect, truncated
        elif tactical_notes and len(tactical_notes) > 0:
            weather_impact_text = str(tactical_notes[0])[:18]
        else:
            weather_impact_text = "No significant impact"

        if h2h_meetings > 5:
            h2h_text = f"H2H: {h2h_meetings} games"
            h2h_color = "#27ae60"  # Green - data available
            # Add H2H record summary if available
            h2h_home_wins = h2h_data.get("home_wins", 0)
            h2h_away_wins = h2h_data.get("away_wins", 0)
            h2h_draws = h2h_data.get("draws", 0)
            if h2h_home_wins or h2h_away_wins or h2h_draws:
                h2h_impact_text = f"{h2h_home_wins}W-{h2h_draws}D-{h2h_away_wins}L"
            else:
                h2h_impact_text = None
        elif h2h_meetings > 0:
            h2h_text = f"H2H: {h2h_meetings} games"
            h2h_color = "#f39c12"  # Orange - limited data
            h2h_impact_text = None
        else:
            h2h_text = "H2H: No data"
            h2h_color = "#95a5a6"  # Gray - no data
            h2h_impact_text = None

        if home_strength is not None and away_strength is not None:
            if abs(home_strength - away_strength) > 10:
                strength_text = "Lineups: Unequal"
                strength_color = "#e74c3c"  # Red
            else:
                strength_text = "Lineups: Equal"
                strength_color = "#27ae60"  # Green
        else:
            strength_text = "Lineups: Pending"
            strength_color = "#95a5a6"  # Light gray

        # Referee assessment
        referee_name = match_data.get("referee_analysis", {}).get("name", "TBD")
        if referee_name not in ["TBD", "Unknown Referee"]:
            referee_text = f"Ref: {referee_name[:15]}"
            referee_color = "#9b59b6"  # Purple
        else:
            referee_text = "Referee: TBD"
            referee_color = "#95a5a6"  # Light gray

        # Create 4 boxes in 2x2 grid for factors - aligned with Expected Goals boxes above
        factor_boxes = [
            (
                2.5,
                weather_text,
                weather_color,
                weather_impact_text,
            ),  # Weather with impact
            (7.5, h2h_text, h2h_color, h2h_impact_text),  # H2H with record
            (2.5, strength_text, strength_color, None),
            (7.5, referee_text, referee_color, None),
        ]

        factor_box_width = 2.8
        factor_box_height = 1.2
        factor_y_top = 7.9
        factor_y_bottom = 6.4

        # Top row factors (Weather with impact, H2H)
        for idx in range(2):
            x_pos = factor_boxes[idx][0]
            text = factor_boxes[idx][1]
            color = factor_boxes[idx][2]
            impact_text = factor_boxes[idx][3] if len(factor_boxes[idx]) > 3 else None

            factor_bg = Rectangle(
                (x_pos - factor_box_width / 2, factor_y_top),
                factor_box_width,
                factor_box_height,
                facecolor="#E8E8E8",
                edgecolor=color,
                linewidth=3.5,
                zorder=2,
                alpha=0.9,
            )
            ax.add_patch(factor_bg)

            if impact_text:
                # Weather box: Show temp on top, impact below
                ax.text(
                    x_pos,
                    factor_y_top + 0.85,
                    text,
                    ha="center",
                    va="center",
                    fontsize=13,
                    fontweight="bold",
                    color="#000000",
                    zorder=3,
                    fontname="DejaVu Sans",
                )
                ax.text(
                    x_pos,
                    factor_y_top + 0.4,
                    impact_text,
                    ha="center",
                    va="center",
                    fontsize=14,
                    fontweight="bold",
                    color=color,
                    zorder=3,
                    fontname="DejaVu Sans",
                )
            else:
                ax.text(
                    x_pos,
                    factor_y_top + 0.7,
                    text,
                    ha="center",
                    va="center",
                    fontsize=14,
                    fontweight="bold",
                    color="#000000",
                    zorder=3,
                    fontname="DejaVu Sans",
                )

        # Bottom row factors (Lineups, Referee) - now with dynamic colored borders
        for idx in range(2, 4):
            x_pos = factor_boxes[idx][0]
            text = factor_boxes[idx][1]
            color = factor_boxes[idx][2]

            factor_bg = Rectangle(
                (x_pos - factor_box_width / 2, factor_y_bottom),
                factor_box_width,
                factor_box_height,
                facecolor="#E8E8E8",
                edgecolor=color,
                linewidth=3.5,
                zorder=2,
                alpha=0.9,
            )
            ax.add_patch(factor_bg)

            ax.text(
                x_pos,
                factor_y_bottom + 0.7,
                text,
                ha="center",
                va="center",
                fontsize=14,
                fontweight="bold",
                color="#000000",
                zorder=3,
                fontname="DejaVu Sans",
            )

        # =================================================================
        # COLOR LEGEND - Explains border colors to users
        # =================================================================
        legend_y = 5.85
        ax.text(
            5,
            legend_y,
            "🔑 Color Key:",
            ha="center",
            va="center",
            fontsize=14,
            fontweight="bold",
            color="#2c3e50",
            zorder=3,
            fontname="DejaVu Sans",
        )

        # Legend items - probability scale with descriptive words
        legend_row1 = [
            (1.0, "●", "#27AE60", "75%+ Great"),  # Green - excellent
            (3.0, "●", "#17A2B8", "50-74% Good"),  # Cyan - good
            (5.0, "●", "#F39C12", "25-49% Fair"),  # Orange - moderate
            (7.0, "●", "#E74C3C", "0-24% Poor"),  # Red - low
            (8.8, "●", "#9b59b6", "Info"),  # Purple - informational
        ]

        for x, symbol, color, label in legend_row1:
            ax.text(
                x,
                legend_y - 0.45,
                symbol,
                ha="center",
                va="center",
                fontsize=14,
                color=color,
                zorder=3,
                fontname="DejaVu Sans",
            )
            ax.text(
                x + 0.35,
                legend_y - 0.45,
                label,
                ha="left",
                va="center",
                fontsize=14,
                color="#333333",
                zorder=3,
                fontname="DejaVu Sans",
            )

        # =================================================================
        # FOOTER - Clean and informative (moved down to avoid legend overlap)
        # =================================================================

        footer_bg = Rectangle((0.4, 0.3), 9.2, 4.8, facecolor="#2c3e50", alpha=1.0)
        ax.add_patch(footer_bg)

        ax.text(
            5,
            4.6,
            "🤖 AI-ENHANCED SPORTS PREDICTION SYSTEM",
            ha="center",
            va="center",
            fontsize=14,
            fontweight="bold",
            color="white",
            fontname="DejaVu Sans",
            zorder=3,
        )

        # Professional footer description with improved styling
        ax.text(
            5,
            4.1,
            "Advanced machine learning with Phase 2 Lite intelligent analysis",
            ha="center",
            va="center",
            fontsize=14,
            color="white",
            fontname="DejaVu Sans",
            zorder=3,
        )

        # Processing time with professional formatting
        ax.text(
            5,
            3.6,
            f"✓ Analysis: {match_data.get('processing_time', 0.1):.3f}s • Confidence: {int(confidence)}%",
            ha="center",
            va="center",
            fontsize=14,
            color="white",
            fontname="DejaVu Sans",
            zorder=3,
        )

        # Data sources with professional badge styling
        ax.text(
            5,
            3.1,
            "Data: Official APIs • Weather • Form • H2H Analysis",
            ha="center",
            va="center",
            fontsize=14,
            color="white",
            fontname="DejaVu Sans",
            zorder=3,
        )

        # Generated timestamp with professional styling
        ax.text(
            5,
            2.6,
            f"Generated: {match_data.get('generated_at', 'Now')[:16]} • Enhanced Intelligence Active",
            ha="center",
            va="center",
            fontsize=14,
            color="white",
            fontname="DejaVu Sans",
            zorder=3,
        )

        # Professional disclaimer with improved styling
        ax.text(
            5,
            1.5,
            "⚠️ Educational purposes only • For analysis only • Not financial advice",
            ha="center",
            va="center",
            fontsize=14,
            fontweight="bold",
            style="italic",
            color="white",
            fontname="DejaVu Sans",
            zorder=3,
        )

        # Final save: render to temp file, verify contents, then atomically move to final path
        plt.tight_layout()
        tmp_path = f"{path}/prediction_card.mpl.png"
        final_path = f"{path}/prediction_card.png"
        print("[TRACE] about to call plt.savefig to temp file (final save)")
        plt.savefig(
            tmp_path, dpi=300, bbox_inches="tight", facecolor="white", pad_inches=0.3
        )
        print("[TRACE] matplotlib final temp save completed")
        plt.close()

        try:
            from PIL import Image, ImageDraw, ImageFont

            im = Image.open(tmp_path).convert("RGB")
            nonwhite = sum(1 for px in im.getdata() if px != (255, 255, 255))
            print(f"[TRACE] final temp image nonwhite pixels: {nonwhite}")
            if nonwhite > 0:
                try:
                    import shutil, os

                    shutil.move(tmp_path, final_path)
                    # verify final file
                    im2 = Image.open(final_path).convert("RGB")
                    nonwhite2 = sum(1 for px in im2.getdata() if px != (255, 255, 255))
                    print(f"[TRACE] final file nonwhite pixels after move: {nonwhite2}")
                    if nonwhite2 == 0:
                        print(
                            "[WARN] final file appears blank after move; writing pillow fallback instead"
                        )
                        raise RuntimeError("Final moved file blank")
                except Exception as e:
                    print("[WARN] could not move temp to final or final file blank:", e)
                    try:
                        im.save(final_path)
                        print(f"   • Saved final image at: {final_path}")
                    except Exception as e2:
                        print("[WARN] could not save image with PIL:", e2)
            else:
                print(
                    "[WARN] Matplotlib final temp output blank; writing Pillow fallback image"
                )
                w, h = 1200, 800
                img = Image.new("RGB", (w, h), color="#ffffff")
                draw = ImageDraw.Draw(img)
                try:
                    font_bold = ImageFont.truetype("DejaVuSans-Bold.ttf", 44)
                    font_reg = ImageFont.truetype("DejaVuSans.ttf", 22)
                except Exception as e:
                    print("[WARN] could not load truetype fonts:", e)
                    font_bold = None
                    font_reg = None
                draw.rectangle([(0, 0), (w, 120)], fill=("#004CD4"))
                draw.text(
                    (w // 2, 30),
                    f"{match_data.get('home_team', 'Home')}  vs  {match_data.get('away_team', 'Away')}",
                    fill="white",
                    anchor="ms",
                    font=font_bold,
                )
                score = match_data.get("expected_final_score", "N/A")
                draw.text(
                    (w // 2, 160),
                    f"Predicted: {score}",
                    fill="#222222",
                    anchor="ms",
                    font=font_bold,
                )
                draw.text(
                    (w // 2, 220),
                    f"{match_data.get('date', '')} {match_data.get('time', '')}",
                    fill="#444444",
                    anchor="ms",
                    font=font_reg,
                )
                draw.text(
                    (w // 2, h - 80),
                    f"Confidence: {int(round((match_data.get('confidence', 0.0)) * 100))}% | Generated: {match_data.get('generated_at', '')}",
                    fill="#666666",
                    anchor="ms",
                    font=font_reg,
                )
                img.save(final_path, format="PNG")
                print(f"   • Wrote Pillow fallback image at: {final_path}")
                try:
                    import os

                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
                except Exception:
                    pass
        except Exception as e:
            print("[WARN] final save verification failed:", e)

        # Final check: ensure PNG exists and is not empty. If missing, attempt a forced placeholder and fail loudly
        try:
            import os
            if not os.path.exists(final_path) or os.path.getsize(final_path) == 0:
                print(f"[WARN] final image missing or empty at {final_path}; writing forced placeholder and raising")
                try:
                    from PIL import Image, ImageDraw
                    w, h = 1200, 800
                    img = Image.new("RGB", (w, h), color="#ffffff")
                    draw = ImageDraw.Draw(img)
                    draw.text((w // 2, h // 2), "Image generation failed", fill="#000000", anchor="ms")
                    img.save(final_path, format="PNG")
                    print(f"   • Wrote forced placeholder image at: {final_path}")
                except Exception as e2:
                    print("[ERROR] Could not write forced placeholder image:", e2)
                    raise RuntimeError("Image generation failed; no image could be written")
                # If we wrote placeholder but it's still empty, raise
                if not os.path.exists(final_path) or os.path.getsize(final_path) == 0:
                    raise RuntimeError("Image generation failed; final image missing after forced placeholder")
        except Exception as e_final:
            # Re-raise to allow outer callers to handle and create global placeholder
            print("[ERROR] Final image verification failed:", e_final)
            raise

    # ================================================================
    # ===================== END OF save_image SECTION =====================
    # ================================================================

    def save_format_copies(
        self, match_data: JSONDict, match_folder: Union[str, Path]
    ) -> None:
        """Save copies in format-specific directories for easy access"""
        # JSON copy
        json_path = f"reports/formats/json/{match_folder}.json"
        with open(json_path, "w", encoding="utf-8") as f:
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
        league_folder = match_data.get("league", "La Liga").lower().replace(" ", "-")
        source_image = f"reports/leagues/{league_folder}/matches/{match_folder}/prediction_card.png"
        image_path = f"reports/formats/images/{match_folder}.png"

        if os.path.exists(source_image):
            shutil.copy2(source_image, image_path)

    def get_recommendation(self, prediction: JSONDict) -> str:
        """Get enhanced recommendation with probability thresholds.

        This uses the reported win/draw probabilities and returns a concise
        human-friendly recommendation string.
        """
        # Defensive extraction of probabilities with sensible defaults
        home_prob = prediction.get("home_win_prob") or prediction.get("home_prob") or 0.0
        draw_prob = prediction.get("draw_prob") or prediction.get("draw_probability") or 0.0
        away_prob = prediction.get("away_win_prob") or prediction.get("away_prob") or 0.0

        max_prob = max(home_prob, draw_prob, away_prob)
        second_prob = sorted([home_prob, draw_prob, away_prob], reverse=True)[1]

        # If the difference is less than 10 percentage points, call it competitive
        if (max_prob - second_prob) < 10:
            if max_prob == home_prob:
                return "Competitive (Home Edge)"
            elif max_prob == draw_prob:
                return "Competitive (Draw Edge)"
            else:
                return "Competitive (Away Edge)"

        # Clear winner with >10pt margin
        if max_prob == home_prob:
            return "Home Win Likely" if max_prob >= 50 else "Home Win Possible"
        elif max_prob == draw_prob:
            return "Draw Expected" if max_prob >= 40 else "Draw Possible"
        else:
            return "Away Win Likely" if max_prob >= 50 else "Away Win Possible"


def ensure_prediction_image_exists(full_path: str, match_data: Dict[str, Any], match_folder: str) -> bool:
    """Ensure a PNG prediction image exists at full_path/prediction_card.png.
    Returns True if the image exists or was created successfully, False otherwise.

    This helper is safe to call in tests (does not depend on the rest of the generator).
    """
    try:
        img_path = os.path.join(full_path, "prediction_card.png")
        # Quick check
        if os.path.exists(img_path) and os.path.getsize(img_path) > 0:
            return True

        # Create directories if missing
        os.makedirs(full_path, exist_ok=True)

        # Try to write a placeholder using Pillow
        from PIL import Image, ImageDraw
        w, h = 1200, 800
        img = Image.new("RGB", (w, h), color="#ffffff")
        draw = ImageDraw.Draw(img)
        try:
            home = match_data.get("home_team", "Home")
            away = match_data.get("away_team", "Away")
            title = f"{home} vs {away}"
            draw.text((w // 2, h // 2 - 20), title, fill="#000000", anchor="ms")
        except Exception:
            pass
        draw.text((w // 2, h // 2 + 20), "Prediction image placeholder", fill="#000000", anchor="ms")
        img.save(img_path, format="PNG")

        # Also ensure a copy exists in the unified formats directory
        try:
            import shutil
            formats_dir = os.path.join("reports", "formats", "images")
            os.makedirs(formats_dir, exist_ok=True)
            shutil.copy2(img_path, os.path.join(formats_dir, f"{match_folder}.png"))
        except Exception:
            # Non-fatal
            pass

        return True
    except Exception:
        return False

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

    def _format_interval_segment(self, interval: Union[list[float], tuple[float, float]]) -> str:
        """Instance wrapper to format interval segments.

        This fallback ensures the method is available on the instance even if the
        static helper is not bound correctly at import time (defensive fix).
        """
        # If the static implementation exists on the class, invoke it
        if hasattr(self.__class__, '_format_interval_segment') and callable(getattr(self.__class__, '_format_interval_segment')):
            try:
                # call class-level staticmethod if present
                return self.__class__._format_interval_segment(interval)
            except Exception:
                pass
        # Fallback formatting logic
        try:
            if isinstance(interval, (list, tuple)) and len(interval) >= 2:
                start = float(interval[0])
                end = float(interval[1])
                return f"{start:.1f}% – {end:.1f}%"
        except Exception:
            pass
        return "N/A"

    @staticmethod
    def _format_interval_segment(
        interval: Union[list[float], tuple[float, float]],
    ) -> str:
        """Convert interval collections to a normalized percentage string."""
        if isinstance(interval, (list, tuple)) and len(interval) >= 2:
            try:
                start = float(interval[0])
                end = float(interval[1])
            except (TypeError, ValueError):
                return "N/A"
            return f"{start:.1f}% – {end:.1f}%"
        return "N/A"

def _format_advanced_predictions_section_impl(match_data: JSONDict) -> str:
    """Format Phase 4-7 advanced predictions for markdown output."""
    lines = []

    # Get advanced predictions data
    advanced = match_data.get("advanced_predictions", {})
    shot_quality = match_data.get("shot_quality", {})
    odds_movement = match_data.get("odds_movement", {})
    player_impact = match_data.get("player_impact", {})
    phase_enhancements = match_data.get("phase_enhancements", {})

    # Phase 4: BTTS & Over/Under
    btts = advanced.get("btts", {})
    over_under = advanced.get("over_under", {})
    exact_scores = advanced.get("exact_scores", [])
    two_stage = advanced.get("two_stage_score", {})

    lines.append("### 🎯 BTTS Analysis (Phase 4)")
    if btts:
        lines.append(f"- **BTTS Yes:** {btts.get('btts_yes_probability', 0):.1f}%")
        lines.append(f"- **BTTS No:** {btts.get('btts_no_probability', 0):.1f}%")
        lines.append(f"- **Prediction:** {btts.get('prediction', 'N/A')}")
        lines.append(f"- **Confidence:** {btts.get('confidence', 0):.1f}%")
        factors = btts.get("factors", {})
        if factors:
            lines.append(
                f"- **Home Scoring Chance:** {factors.get('home_scoring_chance', 0):.1f}%"
            )
            lines.append(
                f"- **Away Scoring Chance:** {factors.get('away_scoring_chance', 0):.1f}%"
            )
    else:
        lines.append("- Data not available")

    lines.append("")
    lines.append("### 📊 Over/Under Analysis (Phase 4)")
    if over_under:
        lines.append(
            f"- **Expected Total Goals:** {over_under.get('expected_total_goals', 0):.2f}"
        )
        ou_lines = over_under.get("lines", {})
        for line_val in ["1.5", "2.5", "3.5"]:
            line_data = ou_lines.get(line_val, {})
            if line_data:
                    lines.append(
                        f"- **O/U {line_val}:** Over {line_data.get('over_probability', 0):.1f}% / Under {line_data.get('under_probability', 0):.1f}%"
                    )
            lines.append(
                f"- **Recommended Line:** {over_under.get('recommended_line', 'N/A')}"
            )
        else:
            lines.append("- Data not available")

        lines.append("")
        lines.append("### 🎲 Exact Score Predictions (Phase 4)")
        if exact_scores:
            for i, score_data in enumerate(exact_scores[:5]):
                score = score_data.get("score", "N/A")
                prob = score_data.get("probability", 0)
                lines.append(f"- **{i + 1}.** {score}: {prob:.1f}%")
        else:
            lines.append("- See score probabilities above")

        # Phase 5: Shot Quality
        lines.append("")
        lines.append("### 🎯 Shot Quality Analysis (Phase 5)")
        home_sq = shot_quality.get("home", {})
        away_sq = shot_quality.get("away", {})
        if home_sq or away_sq:
            if home_sq:
                lines.append(f"- **{home_sq.get('team_name', 'Home')}:**")
                lines.append(f"  - xG per Shot: {home_sq.get('xg_per_shot', 0):.3f}")
                lines.append(f"  - Data Quality: {home_sq.get('data_quality', 'N/A')}")
            if away_sq:
                lines.append(f"- **{away_sq.get('team_name', 'Away')}:**")
                lines.append(f"  - xG per Shot: {away_sq.get('xg_per_shot', 0):.3f}")
                lines.append(f"  - Data Quality: {away_sq.get('data_quality', 'N/A')}")
        else:
            lines.append("- Data not available")

        # Phase 6: Odds Movement
        lines.append("")
        lines.append("### 📈 Odds Movement Analysis (Phase 6)")
        if odds_movement:
            lines.append(
                f"- **Home Movement:** {odds_movement.get('home_movement', 'stable')} ({odds_movement.get('home_movement_pct', 0):.1f}%)"
            )
            lines.append(
                f"- **Away Movement:** {odds_movement.get('away_movement', 'stable')} ({odds_movement.get('away_movement_pct', 0):.1f}%)"
            )
            lines.append(
                f"- **Movement Strength:** {odds_movement.get('movement_strength', 'minimal')}"
            )
            lines.append(
                f"- **Sharp Money Detected:** {'⚠️ Yes' if odds_movement.get('sharp_money_detected') else '✅ No'}"
            )
            if odds_movement.get("sharp_money_detected"):
                lines.append(
                    f"- **Sharp Money Side:** {odds_movement.get('sharp_money_side', 'N/A')}"
                )
            lines.append(
                f"- **Market Favorite:** {odds_movement.get('market_favorite', 'N/A')}"
            )
        else:
            lines.append("- Data not available")

        # Phase 7: Player Impact
        lines.append("")
        lines.append("### 👤 Player Impact Analysis (Phase 7)")
        if player_impact and isinstance(player_impact, dict) and len(player_impact) > 0:
            home_impact = player_impact.get("home_impact", {})
            away_impact = player_impact.get("away_impact", {})
            if home_impact:
                lines.append(
                    f"- **Home Team Impact:** {home_impact.get('total_impact', 0):.2f}"
                )
            if away_impact:
                lines.append(
                    f"- **Away Team Impact:** {away_impact.get('total_impact', 0):.2f}"
                )
            if player_impact.get("key_absences"):
                lines.append(
                    f"- **Key Absences:** {', '.join(player_impact.get('key_absences', []))}"
                )
        else:
            lines.append("- Player impact data not available for this match")

        # Phase enhancements summary
        lines.append("")
        lines.append("### ⚙️ Enhancement Phases Active")
        if phase_enhancements:
            active_phases = []
            for i in range(1, 8):
                key = f"phase{i}_enhanced"
                if phase_enhancements.get(key, False):
                    active_phases.append(f"Phase {i}")
            lines.append(
                f"- **Active:** {', '.join(active_phases) if active_phases else 'None'}"
            )
        else:
            lines.append("- Phase enhancement status not available")

        return "\n".join(lines)

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
            r"\bAth\.?\b": "Athletic",
        }
        for pat, rep in substitutions.items():
            s = re.sub(pat, rep, s, flags=re.IGNORECASE)
        # Collapse multiple spaces and trim
        s = re.sub(r"\s+", " ", s).strip()
        return s

    @staticmethod
    def format_team_name_for_display(name: str, max_length: int = 20) -> str:
        """Format team name for display with consistent truncation.

        Args:
            name: Full team name
            max_length: Maximum characters before truncation (default 20)

        Returns:
            Formatted team name, truncated with '...' if necessary
        """
        if not name:
            return "Unknown"
        s = name.strip()
        if len(s) > max_length:
            return s[:max_length] + "..."
        return s

    @staticmethod
    def validate_match_data(match_data: dict) -> dict:
        """Validate and sanitize match data with safe defaults.

        Args:
            match_data: Raw match data dictionary

        Returns:
            Validated match data with safe defaults for missing fields
        """
        # Define required fields with safe defaults
        defaults = {
            "home_team": "Home Team",
            "away_team": "Away Team",
            "league": "League",
            "date": "TBD",
            "time": "00:00",
            "expected_final_score": "0-0",
            "expected_home_goals": 0.0,
            "expected_away_goals": 0.0,
            "home_win_probability": 0.0,
            "draw_probability": 0.0,
            "away_win_probability": 0.0,
            "confidence": 50.0,
        }

        # Ensure all required fields exist with safe defaults
        validated = {
            **defaults,
            **{k: v for k, v in match_data.items() if v is not None},
        }

        # Type conversion and validation
        try:
            validated["expected_home_goals"] = float(
                validated.get("expected_home_goals", 0.0)
            )
            validated["expected_away_goals"] = float(
                validated.get("expected_away_goals", 0.0)
            )
            validated["home_win_probability"] = float(
                validated.get("home_win_probability", 0.0)
            )
            validated["draw_probability"] = float(
                validated.get("draw_probability", 0.0)
            )
            validated["away_win_probability"] = float(
                validated.get("away_win_probability", 0.0)
            )
            validated["confidence"] = float(validated.get("confidence", 50.0))
        except (ValueError, TypeError):
            # If conversion fails, keep defaults
            pass

        return validated

    def clean_old_reports(self, match_filter: str | None = None, allow_prune: bool = False) -> None:
        """Clean reports from leagues while preserving directory structure.

        This operation is potentially destructive and will remove match directories
        and files under `reports/`. To prevent accidental deletion, this method
        will refuse to perform any removals unless explicitly permitted by one
        of the following:

        - The caller passes `allow_prune=True` (intended for the CLI `run-prune` command), OR
        - The environment variable `PRUNE_ALLOWED` is set to the string `'1'`.

        If `match_filter` is provided, only match directories whose name
        contains the filter substring (case-insensitive) will be removed.
        """
        import shutil

        # Enforce prune guard: do not remove reports unless `allow_prune=True` or PRUNE_ALLOWED=1
        if not allow_prune and os.getenv("PRUNE_ALLOWED") != "1":
            raise RuntimeError(
                "Refusing to remove reports: destructive operation requires explicit approval. "
                "Use the `sports-forecast run-prune` command or set PRUNE_ALLOWED=1 in the environment."
            )

        if match_filter:
            safe_print(f"Cleaning old reports matching '{match_filter}' from all leagues...")
        else:
            safe_print("Cleaning old reports from all leagues...")

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
                    match_dirs = [
                        d
                        for d in all_items
                        if os.path.isdir(os.path.join(league_dir, d))
                        and d not in [".keep", ".gitkeep"]
                    ]

                    # Optionally filter which match directories are targeted
                    if match_filter:
                        match_dirs = [d for d in match_dirs if match_filter.lower() in d.lower()]

                    print(
                        f"   🏟️ Cleaning {len(match_dirs)} matches from {league_dir.split('/')[-2]}"
                    )

                    for match_dir in match_dirs:
                        match_path = os.path.join(league_dir, match_dir)
                        # Remove entire match directory forcibly
                        try:
                            shutil.rmtree(match_path)
                            match_directories_removed += 1
                        except Exception as e:
                            safe_print(f"⚠️ Could not forcibly remove {match_path}: {e}")

                except Exception as e:
                    print(f"⚠️ Could not clean {league_dir}: {e}")

        # Clean format directories
        format_directories = [
            "reports/formats/json",
            "reports/formats/markdown",
            "reports/formats/images",
            "reports/archive",
        ]

        for format_dir in format_directories:
            if os.path.exists(format_dir):
                try:
                    format_files = [
                        f
                        for f in os.listdir(format_dir)
                        if os.path.isfile(os.path.join(format_dir, f)) and f != ".keep"
                    ]

                    for file in format_files:
                        file_path = os.path.join(format_dir, file)
                        os.remove(file_path)
                        reports_cleaned += 1

                except Exception as e:
                    print(f"⚠️ Could not clean {format_dir}: {e}")

        # Count directories with .keep files (preserved structure)
        for _root, _dirs, files in os.walk("reports"):
            if ".keep" in files:
                directories_preserved += 1

        safe_print("Comprehensive cleanup complete!")
        safe_print(f"   Files removed: {reports_cleaned}")
        safe_print(f"   Match directories removed: {match_directories_removed}")
        safe_print(f"   League directories preserved: {len(getattr(self, '_LEAGUE_CANONICAL', {}))}")
        safe_print(f"   Total directories preserved: {directories_preserved}")
        safe_print("   Directory structure maintained with .keep files")


# Backward-compatibility safeguard: ensure the SingleMatchGenerator has a usable clean_old_reports method.
# Some execution environments or import-time side effects may have left the method unavailable on the class.
# Provide a safe, minimal implementation that mirrors the intended behavior (non-destructive if directories are absent).
if not hasattr(SingleMatchGenerator, 'clean_old_reports'):
    def clean_old_reports(self, match_filter: str | None = None) -> None:
        """Fallback cleaner for reports (safe and idempotent).

        This implementation is intentionally conservative: it will remove match directories
        and clear format directories while preserving `.keep` files and directory structure.
        """
        import shutil, os

        # Enforce prune guard for fallback implementation as well
        if os.getenv("PRUNE_ALLOWED") != "1":
            raise RuntimeError("Refusing to remove reports (fallback cleaner): set PRUNE_ALLOWED=1 or use the CLI run-prune command.")

        if match_filter:
            safe_print(f"Cleaning old reports matching '{match_filter}' from all leagues...")
        else:
            safe_print("Cleaning old reports from all leagues...")

        reports_cleaned = 0
        match_directories_removed = 0
        directories_preserved = 0

        league_directories = [
            f"reports/leagues/{info['folder']}/matches"
            for info in getattr(self, '_LEAGUE_CANONICAL', {}).values()
        ]

        for league_dir in league_directories:
            if os.path.exists(league_dir):
                try:
                    all_items = os.listdir(league_dir)
                    match_dirs = [
                        d
                        for d in all_items
                        if os.path.isdir(os.path.join(league_dir, d))
                        and d not in ['.keep', '.gitkeep']
                    ]

                    if match_filter:
                        match_dirs = [d for d in match_dirs if match_filter.lower() in d.lower()]

                    safe_print(f"   Cleaning {len(match_dirs)} matches from {league_dir.split('/')[-2]}")

                    for match_dir in match_dirs:
                        match_path = os.path.join(league_dir, match_dir)
                        try:
                            shutil.rmtree(match_path)
                            match_directories_removed += 1
                        except Exception as e:
                            safe_print(f"Could not forcibly remove {match_path}: {e}")

                except Exception as e:
                    safe_print(f"Could not clean {league_dir}: {e}")

        format_directories = [
            "reports/formats/json",
            "reports/formats/markdown",
            "reports/formats/images",
            "reports/archive",
        ]

        for format_dir in format_directories:
            if os.path.exists(format_dir):
                try:
                    format_files = [
                        f
                        for f in os.listdir(format_dir)
                        if os.path.isfile(os.path.join(format_dir, f)) and f != '.keep'
                    ]

                    for file in format_files:
                        file_path = os.path.join(format_dir, file)
                        try:
                            os.remove(file_path)
                            reports_cleaned += 1
                        except Exception as e:
                            print(f"⚠️ Could not remove {file_path}: {e}")

                except Exception as e:
                    print(f"⚠️ Could not clean {format_dir}: {e}")

        for _root, _dirs, files in os.walk("reports"):
            if '.keep' in files:
                directories_preserved += 1

        safe_print("Comprehensive cleanup complete!")
        safe_print(f"   Files removed: {reports_cleaned}")
        safe_print(f"   Match directories removed: {match_directories_removed}")
        safe_print(f"   League directories preserved: {len(getattr(self, '_LEAGUE_CANONICAL', {}))}")
        safe_print(f"   Total directories preserved: {directories_preserved}")
        safe_print("   Directory structure maintained with .keep files")

    # Attach fallback method to the class
    setattr(SingleMatchGenerator, 'clean_old_reports', clean_old_reports)


def main() -> None:
    """Main CLI interface"""
    import sys

    print("[SYSTEM] Sports Prediction System - CLI")
    print("=" * 40)

    # Parse a simple '--no-injuries' CLI flag and optional '--disable-injuries-ttl' override
    skip_injuries = "--no-injuries" in sys.argv
    injuries_disable_ttl_override: int | None = None
    if skip_injuries:
        sys.argv = [a for a in sys.argv if a != "--no-injuries"]

    # Parse --delay flag for time between matches (in seconds)
    match_delay = 0
    if "--delay" in sys.argv:
        try:
            idx = sys.argv.index("--delay")
            match_delay = int(sys.argv[idx + 1])
            del sys.argv[idx : idx + 2]
            print(f"⏱️  Match delay: {match_delay}s between matches")
        except Exception:
            print("❌ Invalid --delay value. Provide seconds (e.g., --delay 60)")
            return

    if "--disable-injuries-ttl" in sys.argv:
        try:
            idx = sys.argv.index("--disable-injuries-ttl")
            # TTL should be the next arg
            ttl_val = int(sys.argv[idx + 1])
            injuries_disable_ttl_override = int(ttl_val)
            # Remove the args
            del sys.argv[idx : idx + 2]
        except Exception:
            print(
                "❌ Invalid --disable-injuries-ttl value. Provide a numeric seconds value."
            )
            return

    # CLI switch for exporting metrics after run
    export_metrics = "--export-metrics" in sys.argv
    if export_metrics:
        sys.argv = [a for a in sys.argv if a != "--export-metrics"]
    generator = SingleMatchGenerator(
        skip_injuries=skip_injuries,
        injuries_disable_ttl_override=injuries_disable_ttl_override,
        export_metrics=export_metrics,
    )
    args = sys.argv[1:]

    # Check for special commands first
    if not args or (len(args) == 1 and args[0].lower() in ["help", "--help", "-h"]):
        print("📋 Usage Format:")
        print(
            "     python generate_fast_reports.py generate [number] matches for [league|all]"
        )
        print("\n📋 Examples:")
        print("   python generate_fast_reports.py generate 2 matches for bundesliga")
        print("   python generate_fast_reports.py generate 1 matches for la-liga")
        print(
            "   python generate_fast_reports.py generate 3 matches for premier-league"
        )
        print("   python generate_fast_reports.py generate 1 matches for all")
        print("\n📋 Other Commands:")
        print("   python generate_fast_reports.py prune     - Remove all old reports")
        print("   python generate_fast_reports.py help      - Show this help")
        print("\n📋 Flags:")
        print("   --no-injuries     - Skip injuries calls to external RapidAPI")
        print(
            "   --delay [seconds] - Wait between matches (e.g., --delay 60 for 1 min)"
        )
        print("\n🏆 Available Leagues:")
        print("   " + ", ".join(generator.list_supported_leagues()))
        return

    # Prune command: optionally accept a match filter substring
    if args and args[0].lower() == "prune":
        if len(args) == 1:
            # No filter => clean all
            generator.clean_old_reports()
        else:
            # Treat everything after 'prune' as a single substring filter
            match_filter = " ".join(args[1:]).strip()
            generator.clean_old_reports(match_filter=match_filter)
        return

    # Quick path: generate all [optional number]
    if len(args) >= 2 and args[0].lower() == "generate" and args[1].lower() == "all":
        num_matches = 5
        if len(args) >= 3:
            if args[2].isdigit():
                num_matches = int(args[2])
            else:
                print(
                    "❌ When using 'generate all', provide an optional numeric count like 'generate all 2'."
                )
                return
        if num_matches < 1 or num_matches > 10:
            print("❌ Number of matches must be between 1 and 10")
            return
        print(f"🌍 Generating {num_matches} match(es) per league")
        for slug in generator.list_supported_leagues():
            generator.generate_matches_report(num_matches, slug, match_delay)
        return

    # Parse: generate [number] matches for [league]
    if (
        len(args) >= 5
        and args[0].lower() == "generate"
        and args[2].lower() == "matches"
        and args[3].lower() == "for"
    ):
        try:
            num_matches = int(args[1])
            league = args[4].lower()

            if num_matches < 1 or num_matches > 10:
                print("❌ Number of matches must be between 1 and 10")
                return
            if league == "all":
                print("🌍 Generating reports for all supported leagues")
                for slug in generator.list_supported_leagues():
                    generator.generate_matches_report(num_matches, slug, match_delay)
                return

            generator.generate_matches_report(num_matches, league, match_delay)
            return
        except ValueError:
            print("❌ Invalid number of matches. Must be a number.")
            return

    # Parse: match "Home vs Away" for [league]
    if len(args) >= 4 and args[0].lower() == "match":
        try:
            # Find 'for' keyword to separate match string from league
            lower_args = [a.lower() for a in args]
            if "for" not in lower_args:
                print(
                    '❌ Usage: python generate_fast_reports.py match "Home vs Away" for <league>'
                )
                return
            idx_for = lower_args.index("for")
            match_str = " ".join(args[1:idx_for]).strip()
            if idx_for + 1 >= len(args):
                print(
                    "❌ Please specify a league after 'for', e.g., 'for premier-league'"
                )
                return
            league = args[idx_for + 1].lower()

            # Parse match string into home and away using common separators
            parts = re.split(
                r"\s+v(?:s)?\.?\s+|\s+vs\.?\s+|\s+v\.\s+", match_str, flags=re.I
            )
            if len(parts) != 2:
                print('❌ Could not parse match string. Use format: "Home vs Away"')
                return
            home_q = parts[0].strip()
            away_q = parts[1].strip()

            generator.generate_match_by_team_names(home_q, away_q, league)
            return
        except Exception as exc:
            print(f"❌ Error processing match command: {exc}")
            return

    # If no valid format, show help
    print("❌ Invalid command format!")
    print(
        "💡 Use: python generate_fast_reports.py generate [number] matches for [league]"
    )
    print(
        "💡 Example: python generate_fast_reports.py generate 2 matches for bundesliga"
    )
    print("💡 Or use: python generate_fast_reports.py help")


if __name__ == "__main__":
    main()
