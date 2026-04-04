#!/usr/bin/env python3
"""Advanced Feature Engineering Module
OPTIMIZATION #3: High-value feature extraction for ML models
Provides 8-12 additional features beyond the base 20
"""

import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


class AdvancedFeatures:
    """Generate high-value features for prediction models"""

    def __init__(self):
        self.feature_cache = {}
        self.logger = logger

    # ========== OPTIMIZATION #3a: REST DIFFERENTIAL (Highest Impact) ==========
    def calculate_rest_differential(self, match_data: dict[str, Any]) -> float:
        """Calculate days since last match (rest advantage)

        Impact: Teams with <2 days rest underperform by ~5-8%
        Teams with 3+ days rest perform optimally

        Returns: -1.0 to +1.0 (positive favors home)
        """
        try:
            home_days_rest = float(match_data.get("home_days_since_last_match", 7.0))
            away_days_rest = float(match_data.get("away_days_since_last_match", 7.0))

            # Normalize to 0-1 scale (7 days = fully rested)
            home_rest_score = min(home_days_rest / 7.0, 1.0)
            away_rest_score = min(away_days_rest / 7.0, 1.0)

            # Rest differential (positive favors home)
            rest_differential = home_rest_score - away_rest_score

            return max(-1.0, min(rest_differential, 1.0))
        except (ValueError, TypeError):
            return 0.0  # Neutral if data unavailable

    # ========== OPTIMIZATION #3b: INJURY IMPACT SCORE (Very High) ==========
    def calculate_injury_impact(self, match_data: dict[str, Any]) -> float:
        """Calculate weighted injury impact by position importance

        Impact: Losing key players significantly affects performance
        - Goalkeeper (0.1): Backup usually similar quality
        - Defender (0.4): Very important for team structure
        - Midfielder (0.3): Important for possession/control
        - Forward (0.5): Most important, affects scoring

        Returns: -1.0 to +1.0 (negative means home team more affected)
        """
        position_importance = {
            "G": 0.1,  # Goalkeeper
            "D": 0.4,  # Defender
            "M": 0.3,  # Midfielder
            "F": 0.5,  # Forward
            "GK": 0.1,
            "CB": 0.4,
            "LB": 0.35,
            "RB": 0.35,
            "CM": 0.3,
            "LM": 0.25,
            "RM": 0.25,
            "ST": 0.5,
        }

        try:
            home_injured = match_data.get("home_injured_players", [])
            away_injured = match_data.get("away_injured_players", [])

            def calculate_team_injury_impact(injured_list: list[dict]) -> float:
                """Sum weighted importance of injured players"""
                if not injured_list:
                    return 0.0

                impact = 0.0
                for player in injured_list:
                    pos = player.get("position", "M")
                    importance = position_importance.get(pos, 0.3)
                    impact += importance

                # Normalize: max 2 key players = 1.0 impact
                return min(impact / 2.0, 1.0)

            home_injury_impact = calculate_team_injury_impact(home_injured)
            away_injury_impact = calculate_team_injury_impact(away_injured)

            # Injury differential (negative if home more injured)
            injury_differential = away_injury_impact - home_injury_impact

            return max(-1.0, min(injury_differential, 1.0))
        except (ValueError, TypeError, KeyError):
            return 0.0  # Neutral if data unavailable

    # ========== OPTIMIZATION #3c: REFEREE BIAS (Medium) ==========
    def calculate_referee_bias(
        self, match_data: dict[str, Any], historical_referee_data: dict | None = None,
    ) -> float:
        """Calculate referee's historical home/away bias

        Some referees favor home teams in penalties/decisions

        Returns: -1.0 to +1.0 (positive = favors home)
        """
        try:
            if not historical_referee_data:
                return 0.0  # No data = neutral

            referee_id = match_data.get("referee_id")
            if not referee_id or referee_id not in historical_referee_data:
                return 0.0  # No data = neutral

            ref_stats = historical_referee_data[referee_id]

            # Home team advantage in decisions
            home_penalty_rate = ref_stats.get("home_penalty_rate", 0.05)
            away_penalty_rate = ref_stats.get("away_penalty_rate", 0.05)

            # Also consider cards differential
            home_card_rate = ref_stats.get("home_card_rate", 1.8)
            away_card_rate = ref_stats.get("away_card_rate", 2.2)

            # Combined bias (penalties matter more)
            bias = (home_penalty_rate - away_penalty_rate) * 10 + (
                away_card_rate - home_card_rate
            ) * 0.05

            return max(-1.0, min(bias, 1.0))
        except (ValueError, TypeError, KeyError):
            return 0.0  # Neutral if error

    # ========== OPTIMIZATION #3d: SET-PIECE EFFICIENCY (Medium) ==========
    def calculate_set_piece_efficiency(self, match_data: dict[str, Any]) -> float:
        """Goals from corners + free kicks as % of total

        Some teams are strong from set pieces, others weak

        Returns: -1.0 to +1.0 (positive favors home set-piece efficiency)
        """
        try:
            home_sp_goals = float(match_data.get("home_set_piece_goals", 0))
            home_total_goals = float(match_data.get("home_total_goals", 10))
            away_sp_goals = float(match_data.get("away_set_piece_goals", 0))
            away_total_goals = float(match_data.get("away_total_goals", 10))

            # Avoid division by zero
            if home_total_goals == 0:
                home_sp_pct = 0.0
            else:
                home_sp_pct = home_sp_goals / home_total_goals

            if away_total_goals == 0:
                away_sp_pct = 0.0
            else:
                away_sp_pct = away_sp_goals / away_total_goals

            # Differential: positive if home better at set pieces
            sp_differential = home_sp_pct - away_sp_pct

            return max(-1.0, min(sp_differential, 1.0))
        except (ValueError, TypeError):
            return 0.0  # Neutral if error

    # ========== OPTIMIZATION #3e: SHOT ACCURACY RATIO (Medium) ==========
    def calculate_shot_accuracy(self, match_data: dict[str, Any]) -> float:
        """Expected Goals / Shots ratio (efficiency)

        Teams with high xG efficiency are more dangerous

        Returns: -1.0 to +1.0 (positive favors home)
        """
        try:
            home_shots = float(match_data.get("home_shots", 10))
            home_xg = float(match_data.get("home_expected_goals", 1.2))
            away_shots = float(match_data.get("away_shots", 10))
            away_xg = float(match_data.get("away_expected_goals", 1.0))

            # Avoid division by zero
            if home_shots > 0:
                home_accuracy = home_xg / home_shots
            else:
                home_accuracy = 0.0

            if away_shots > 0:
                away_accuracy = away_xg / away_shots
            else:
                away_accuracy = 0.0

            # Differential in accuracy
            accuracy_diff = home_accuracy - away_accuracy

            # Scale to -1 to +1 (typical range is 0.06 to 0.18)
            accuracy_diff_scaled = accuracy_diff / 0.06

            return max(-1.0, min(accuracy_diff_scaled, 1.0))
        except (ValueError, TypeError):
            return 0.0  # Neutral if error

    # ========== OPTIMIZATION #3f: WEATHER IMPACT (Lower priority) ==========
    def calculate_weather_impact(self, weather_data: dict[str, Any]) -> float:
        """Wind and rain impact on gameplay

        Strong wind favors defense, rain favors teams with good ball control

        Returns: -1.0 to +1.0 (impact on match)
        """
        try:
            wind_speed = float(weather_data.get("wind_speed_kmh", 0))
            rain_intensity = float(weather_data.get("rain_intensity", 0))  # 0-1 scale

            # Wind impact (high wind favors defensive teams)
            wind_impact = min(wind_speed / 30.0, 1.0) * 0.5  # Max 0.5 impact

            # Rain impact (typically reduces scoring)
            rain_impact = rain_intensity * 0.3  # Max 0.3 impact

            # Neutral for now (could be adjusted with team profiles)
            total_impact = wind_impact + rain_impact

            return max(-1.0, min(total_impact, 1.0))
        except (ValueError, TypeError):
            return 0.0  # Neutral if error

    # ========== OPTIMIZATION #3g: MARKET MOVEMENT (Optional) ==========
    def calculate_market_movement(self, match_data: dict[str, Any]) -> float:
        """Odds movement indicating sharp money

        Large odds movements suggest informed betting (predictor of outcomes)

        Returns: -1.0 to +1.0 (movement direction)
        """
        try:
            opening_odds_home = float(match_data.get("opening_odds_home", 2.0))
            current_odds_home = float(match_data.get("current_odds_home", 2.0))

            # Calculate movement percentage
            if opening_odds_home > 0:
                odds_movement = (
                    opening_odds_home - current_odds_home
                ) / opening_odds_home
            else:
                odds_movement = 0.0

            # Clamp to -1 to +1
            return max(-1.0, min(odds_movement, 1.0))
        except (ValueError, TypeError):
            return 0.0  # Neutral if error

    # ========== OPTIMIZATION #3h: VENUE-SPECIFIC PERFORMANCE ==========
    def calculate_venue_performance(
        self, match_data: dict[str, Any], venue_history: dict | None = None,
    ) -> float:
        """Home team's performance at this specific stadium

        Some teams have strong records at certain venues

        Returns: -1.0 to +1.0 (positive if home strong at venue)
        """
        try:
            if not venue_history:
                return 0.0  # No data = neutral

            venue_id = match_data.get("venue_id")
            if not venue_id or venue_id not in venue_history:
                return 0.0  # No data = neutral

            venue_stats = venue_history[venue_id]

            # Home team win % at this venue
            home_team_id = match_data.get("home_team_id")
            if not home_team_id:
                return 0.0

            team_venue_stats = venue_stats.get(home_team_id, {})
            win_rate = team_venue_stats.get("win_rate", 0.45)

            # Convert to -1 to +1 scale (0.45 = neutral, 0.65 = +0.4)
            venue_advantage = (win_rate - 0.45) * 2.5

            return max(-1.0, min(venue_advantage, 1.0))
        except (ValueError, TypeError, KeyError):
            return 0.0  # Neutral if error

    # ========== PUBLIC API ==========
    def extract_all_features(
        self,
        match_data: dict[str, Any],
        historical_referee_data: dict | None = None,
        venue_history: dict | None = None,
    ) -> dict[str, float]:
        """Extract all advanced features

        Returns dict with 8 features (can be extended to 12+)
        """
        features = {
            "rest_differential": self.calculate_rest_differential(match_data),
            "injury_impact": self.calculate_injury_impact(match_data),
            "referee_bias": self.calculate_referee_bias(
                match_data, historical_referee_data,
            ),
            "set_piece_efficiency": self.calculate_set_piece_efficiency(match_data),
            "shot_accuracy": self.calculate_shot_accuracy(match_data),
            "weather_impact": self.calculate_weather_impact(
                match_data.get("weather_data", {}),
            ),
            "market_movement": self.calculate_market_movement(match_data),
            "venue_performance": self.calculate_venue_performance(
                match_data, venue_history,
            ),
        }

        return features

    def extract_as_array(
        self,
        match_data: dict[str, Any],
        historical_referee_data: dict | None = None,
        venue_history: dict | None = None,
    ) -> np.ndarray:
        """Extract features as numpy array (for ML models)"""
        features = self.extract_all_features(
            match_data, historical_referee_data, venue_history,
        )
        return np.array([features[k] for k in sorted(features.keys())])


# Convenience function for integration
def get_advanced_features_extractor() -> AdvancedFeatures:
    """Factory function to get features extractor"""
    return AdvancedFeatures()
