"""
Context-Aware Weighting Module for Phase 3

Applies dynamic adjustments based on match context:
- Home/away effects
- Season phase effects
- Competition level effects
- Venue performance effects
"""

import json
import os
from typing import Dict, Optional, Tuple
from datetime import date


class ContextExtractor:
    """
    Extracts and applies context-based confidence adjustments.

    Provides four types of adjustments:
    1. Home/Away Effects - Teams perform differently at home vs away
    2. Season Phase Effects - Start vs end of season have different patterns
    3. Competition Level Effects - Title contenders vs relegation fighters
    4. Venue Performance Effects - Stadium-specific advantages
    """

    # Home/away factors by team performance level
    HOME_AWAY_FACTORS = {
        "elite": {
            "home_advantage": 1.05,
            "away_disadvantage": 0.95,
            "neutral_variance": 0.02,
        },
        "strong": {
            "home_advantage": 1.07,
            "away_disadvantage": 0.93,
            "neutral_variance": 0.03,
        },
        "average": {
            "home_advantage": 1.08,
            "away_disadvantage": 0.92,
            "neutral_variance": 0.04,
        },
        "weak": {
            "home_advantage": 1.06,
            "away_disadvantage": 0.94,
            "neutral_variance": 0.03,
        },
    }

    # Season phase effects
    SEASON_PHASES = {
        "early": {  # Aug-Sep: Teams settling in
            "factor": 0.95,
            "reason": "Formation settling, new signings integrating",
        },
        "buildup": {  # Oct-Nov: Teams in form
            "factor": 1.02,
            "reason": "Teams hitting stride, patterns established",
        },
        "midseason": {  # Dec-Jan: Winter breaks, injuries
            "factor": 0.98,
            "reason": "Break disruptions, injury accumulation",
        },
        "second_half": {  # Feb-Mar: Title race clarifying
            "factor": 1.03,
            "reason": "Table positions clear, motivation peaks",
        },
        "late": {  # Apr-May: Final positions settling
            "factor": 1.00,
            "reason": "Most predictable phase",
        },
    }

    # Competition level adjustments
    COMPETITION_LEVEL = {
        "title_contender": {
            "vs_weak": 1.10,  # High confidence vs weak teams
            "vs_contender": 0.98,  # Lower confidence vs similar strength
            "vs_elite": 0.95,  # Much lower confidence vs elite
        },
        "mid_table": {"vs_weak": 1.05, "vs_mid": 1.00, "vs_strong": 0.95},
        "relegation": {"vs_weak": 0.95, "vs_mid": 0.92, "vs_strong": 0.88},
    }

    def __init__(self, cache_dir: Optional[str] = None):
        """
        Initialize ContextExtractor.

        Args:
            cache_dir: Directory for persisting venue performance data
        """
        self.cache_dir = cache_dir or "data/cache"

        # Venue performance history
        self.venue_performance: Dict[str, Dict] = {}

        # Load persisted venue data
        self._load_venue_performance()

    def get_season_phase(self, match_date: Optional[date] = None) -> str:
        """
        Determine season phase based on match date.

        Args:
            match_date: Date of match (defaults to today)

        Returns:
            Season phase key: 'early', 'buildup', 'midseason', 'second_half', 'late'
        """
        if match_date is None:
            match_date = date.today()

        month = match_date.month

        # European football season: Aug-May
        if month in [8, 9]:  # Aug-Sep
            return "early"
        elif month in [10, 11]:  # Oct-Nov
            return "buildup"
        elif month in [12, 1]:  # Dec-Jan
            return "midseason"
        elif month in [2, 3]:  # Feb-Mar
            return "second_half"
        else:  # Apr-May (or Jun-Jul offseason)
            return "late"

    def calculate_home_away_adjustment(
        self,
        is_home: bool,
        home_team_level: str = "average",
        away_team_level: str = "average",
    ) -> Tuple[float, Dict]:
        """
        Calculate home/away adjustment factor.

        Home teams win ~55% of matches. This adjustment captures:
        - Elite teams maintain advantage everywhere
        - Weak teams struggle away more than strong teams

        Args:
            is_home: True if calculating for home team
            home_team_level: 'elite', 'strong', 'average', 'weak'
            away_team_level: 'elite', 'strong', 'average', 'weak'

        Returns:
            Tuple of (adjustment_factor, metadata)
        """
        home_factors = self.HOME_AWAY_FACTORS.get(
            home_team_level, self.HOME_AWAY_FACTORS["average"]
        )
        away_factors = self.HOME_AWAY_FACTORS.get(
            away_team_level, self.HOME_AWAY_FACTORS["average"]
        )

        if is_home:
            factor = home_factors["home_advantage"]
            base_variance = home_factors["neutral_variance"]
        else:
            factor = away_factors["away_disadvantage"]
            base_variance = away_factors["neutral_variance"]

        metadata = {
            "type": "home_away",
            "is_home": is_home,
            "home_team_level": home_team_level,
            "away_team_level": away_team_level,
            "factor": factor,
            "variance": base_variance,
            "range": (factor - base_variance, factor + base_variance),
        }

        return factor, metadata

    def calculate_season_phase_adjustment(
        self, match_date: Optional[date] = None
    ) -> Tuple[float, Dict]:
        """
        Calculate season phase adjustment factor.

        Args:
            match_date: Date of match (defaults to today)

        Returns:
            Tuple of (adjustment_factor, metadata)
        """
        phase = self.get_season_phase(match_date)
        phase_data = self.SEASON_PHASES.get(phase, self.SEASON_PHASES["late"])

        factor = phase_data["factor"]

        metadata = {
            "type": "season_phase",
            "phase": phase,
            "reason": phase_data["reason"],
            "factor": factor,
            "month": match_date.month if match_date else date.today().month,
        }

        return factor, metadata

    def calculate_competition_level_adjustment(
        self, home_level: str = "mid_table", away_level: str = "mid_table"
    ) -> Tuple[float, Dict]:
        """
        Calculate competition level adjustment.

        Captures that matches between mismatched teams are more predictable.
        Elite vs weak = high predictability (elite usually wins)
        Elite vs elite = low predictability (toss-up)

        Args:
            home_level: 'title_contender', 'mid_table', 'relegation'
            away_level: 'title_contender', 'mid_table', 'relegation'

        Returns:
            Tuple of (adjustment_factor, metadata)
        """
        home_comp = self.COMPETITION_LEVEL.get(
            home_level, self.COMPETITION_LEVEL["mid_table"]
        )

        # Determine which bucket away team falls into
        if away_level == "title_contender":
            away_bucket = "vs_elite"
        elif away_level == "relegation":
            away_bucket = "vs_weak"
        else:
            away_bucket = "vs_mid"

        factor = home_comp.get(away_bucket, 1.0)

        metadata = {
            "type": "competition_level",
            "home_level": home_level,
            "away_level": away_level,
            "away_bucket": away_bucket,
            "factor": factor,
            "interpretation": "mismatched" if abs(factor - 1.0) > 0.05 else "balanced",
        }

        return factor, metadata

    def calculate_venue_performance_adjustment(
        self, venue: str, team: str, is_home: bool
    ) -> Tuple[float, Dict]:
        """
        Calculate venue-specific performance adjustment.

        Tracks if specific teams perform better/worse at specific venues.

        Args:
            venue: Venue name/identifier
            team: Team name/identifier
            is_home: True if team plays at home

        Returns:
            Tuple of (adjustment_factor, metadata)
        """
        venue_key = f"{venue}_{team}" if is_home else f"{venue}_vs_{team}"

        if venue_key in self.venue_performance:
            perf = self.venue_performance[venue_key]
            # Success rate at venue: 0.4-0.6 normal, <0.4 or >0.6 significant
            factor = 1.0 + (perf["win_rate"] - 0.5) * 0.08  # Scale to ±4%
            factor = max(0.92, min(1.08, factor))  # Clamp to ±8%

            metadata = {
                "type": "venue_performance",
                "venue": venue,
                "team": team,
                "is_home": is_home,
                "factor": factor,
                "win_rate": perf["win_rate"],
                "samples": perf["samples"],
                "data_confidence": "high" if perf["samples"] > 5 else "low",
            }
        else:
            # No data, use neutral
            factor = 1.0
            metadata = {
                "type": "venue_performance",
                "venue": venue,
                "team": team,
                "is_home": is_home,
                "factor": 1.0,
                "reason": "no_historical_data",
            }

        return factor, metadata

    def record_match_at_venue(
        self, venue: str, home_team: str, away_team: str, home_won: bool
    ) -> None:
        """
        Record match result for venue performance tracking.

        Args:
            venue: Venue name/identifier
            home_team: Home team name/identifier
            away_team: Away team name/identifier
            home_won: Whether home team won
        """
        # Update home team venue record
        home_key = f"{venue}_{home_team}"
        if home_key not in self.venue_performance:
            self.venue_performance[home_key] = {"wins": 0, "total": 0}

        self.venue_performance[home_key]["total"] += 1
        if home_won:
            self.venue_performance[home_key]["wins"] += 1
        self.venue_performance[home_key]["win_rate"] = (
            self.venue_performance[home_key]["wins"]
            / self.venue_performance[home_key]["total"]
        )
        self.venue_performance[home_key]["samples"] = self.venue_performance[home_key][
            "total"
        ]

        # Update away team venue record
        away_key = f"{venue}_vs_{away_team}"
        if away_key not in self.venue_performance:
            self.venue_performance[away_key] = {"wins": 0, "total": 0}

        self.venue_performance[away_key]["total"] += 1
        if not home_won:
            self.venue_performance[away_key]["wins"] += 1
        self.venue_performance[away_key]["win_rate"] = (
            self.venue_performance[away_key]["wins"]
            / self.venue_performance[away_key]["total"]
        )
        self.venue_performance[away_key]["samples"] = self.venue_performance[away_key][
            "total"
        ]

    def apply_all_context_adjustments(
        self,
        confidence: float,
        is_home: bool,
        home_team_level: str = "average",
        away_team_level: str = "average",
        match_date: Optional[date] = None,
        home_competition_level: str = "mid_table",
        away_competition_level: str = "mid_table",
        venue: Optional[str] = None,
        team: Optional[str] = None,
    ) -> Tuple[float, Dict]:
        """
        Apply all context adjustments to confidence.

        Combines home/away, season phase, competition level, and venue effects.

        Args:
            confidence: Raw confidence (0.0-1.0)
            is_home: True if predicting for home team
            home_team_level: Team level for home team
            away_team_level: Team level for away team
            match_date: Date of match
            home_competition_level: Competition position of home team
            away_competition_level: Competition position of away team
            venue: Venue name (optional)
            team: Team name (optional, for venue adjustment)

        Returns:
            Tuple of (adjusted_confidence, all_metadata)
        """
        all_metadata = {"raw_confidence": confidence, "adjustments": {}}

        adjusted = confidence

        # 1. Home/away adjustment
        ha_factor, ha_meta = self.calculate_home_away_adjustment(
            is_home, home_team_level, away_team_level
        )
        adjusted *= ha_factor
        all_metadata["adjustments"]["home_away"] = ha_meta

        # 2. Season phase adjustment
        sp_factor, sp_meta = self.calculate_season_phase_adjustment(match_date)
        adjusted *= sp_factor
        all_metadata["adjustments"]["season_phase"] = sp_meta

        # 3. Competition level adjustment
        comp_level = home_competition_level if is_home else away_competition_level
        opp_level = away_competition_level if is_home else home_competition_level
        cl_factor, cl_meta = self.calculate_competition_level_adjustment(
            comp_level, opp_level
        )
        adjusted *= cl_factor
        all_metadata["adjustments"]["competition_level"] = cl_meta

        # 4. Venue adjustment (if data available)
        if venue and team:
            v_factor, v_meta = self.calculate_venue_performance_adjustment(
                venue, team, is_home
            )
            adjusted *= v_factor
            all_metadata["adjustments"]["venue"] = v_meta
        else:
            all_metadata["adjustments"]["venue"] = {"reason": "no_venue_data"}

        # Clamp to valid range
        adjusted = max(0.0, min(1.0, adjusted))

        # Calculate overall adjustment factor
        all_metadata["overall_factor"] = (
            adjusted / confidence if confidence > 0 else 1.0
        )
        all_metadata["final_confidence"] = adjusted

        return adjusted, all_metadata

    def _load_venue_performance(self) -> None:
        """Load persisted venue performance data."""
        if not self.cache_dir or not os.path.exists(self.cache_dir):
            return

        venue_file = os.path.join(self.cache_dir, "venue_performance.json")
        if os.path.exists(venue_file):
            try:
                with open(venue_file, "r") as f:
                    self.venue_performance = json.load(f)
            except Exception:
                pass  # Silently fail if load is corrupted

    def save_venue_performance(self) -> None:
        """Save venue performance data."""
        if not self.cache_dir:
            return

        os.makedirs(self.cache_dir, exist_ok=True)

        try:
            with open(os.path.join(self.cache_dir, "venue_performance.json"), "w") as f:
                json.dump(self.venue_performance, f, indent=2)
        except Exception:
            pass  # Silently fail if save fails
