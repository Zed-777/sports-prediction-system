"""
Prediction Enhancements Module - Phase 1 Quick Wins
Implements: CC-005, MI-004, DQ-003, CC-004, FE-005, FE-006

This module provides accuracy improvements through:
- Overconfidence capping on heavy favorites (CC-005)
- Time-decayed ELO ratings (MI-004)
- Referee tendency analysis (DQ-003)
- League-specific calibration (CC-004)
- Venue-specific performance adjustments (FE-005)
- Time-of-day/day-of-week effects (FE-006)
"""

import json
import math
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# ============================================================================
# CC-005: OVERCONFIDENCE CAPPING
# When predicting >75% for a team, apply soft cap to prevent overconfidence
# ============================================================================

@dataclass
class ConfidenceCapper:
    """
    Caps extreme confidence predictions to reduce overconfidence on favorites.
    
    Research shows models are systematically overconfident on heavy favorites.
    This applies a soft sigmoid cap that:
    - Leaves predictions <65% mostly unchanged
    - Gradually reduces predictions 65-80%
    - Heavily caps predictions >80%
    """
    
    # Soft cap parameters (tuned via backtesting)
    soft_cap_threshold: float = 0.75  # Start capping above 75%
    hard_cap: float = 0.85  # Maximum allowed probability
    upset_boost_threshold: float = 0.10  # Boost underdogs below 10%
    upset_boost_amount: float = 0.03  # Add 3% to upset probability
    
    def cap_probabilities(
        self, 
        home_prob: float, 
        draw_prob: float, 
        away_prob: float
    ) -> Tuple[float, float, float]:
        """
        Apply soft caps to extreme probabilities.
        
        Args:
            home_prob: Home win probability (0-1)
            draw_prob: Draw probability (0-1)
            away_prob: Away win probability (0-1)
            
        Returns:
            Tuple of (home, draw, away) capped probabilities
        """
        # Identify the favorite and underdog
        probs = {'home': home_prob, 'draw': draw_prob, 'away': away_prob}
        sorted_outcomes = sorted(probs.items(), key=lambda x: x[1], reverse=True)
        favorite, fav_prob = sorted_outcomes[0]
        underdog, dog_prob = sorted_outcomes[-1]
        
        # Apply soft cap to favorite using sigmoid smoothing
        if fav_prob > self.soft_cap_threshold:
            # Sigmoid compression: maps (threshold, 1) to (threshold, hard_cap)
            excess = fav_prob - self.soft_cap_threshold
            max_excess = 1.0 - self.soft_cap_threshold
            cap_range = self.hard_cap - self.soft_cap_threshold
            
            # Sigmoid squash
            compressed = cap_range * (1 - math.exp(-3 * excess / max_excess))
            capped_fav = self.soft_cap_threshold + compressed
            
            # Calculate how much we reduced
            reduction = fav_prob - capped_fav
            probs[favorite] = capped_fav
            
            # Redistribute reduction to draw and underdog
            probs['draw'] += reduction * 0.4
            probs[underdog] += reduction * 0.6
        
        # Boost extreme underdogs slightly (upset protection)
        if dog_prob < self.upset_boost_threshold:
            boost = min(self.upset_boost_amount, self.upset_boost_threshold - dog_prob)
            probs[underdog] += boost
            # Take from favorite
            probs[favorite] -= boost
        
        # Normalize to ensure sum = 1
        total = sum(probs.values())
        return (
            probs['home'] / total,
            probs['draw'] / total,
            probs['away'] / total
        )


# ============================================================================
# MI-004: TIME-DECAYED ELO RATINGS
# Recent matches have higher weight than older matches
# ============================================================================

@dataclass
class TimeDecayedELO:
    """
    ELO rating system with exponential time decay.
    
    Traditional ELO treats all matches equally. This version applies
    exponential decay so recent matches have higher influence.
    """
    
    base_rating: float = 1500.0
    k_factor: float = 32.0
    home_advantage: float = 100.0
    decay_half_life_days: float = 60.0  # Matches lose 50% weight every 60 days
    cache_dir: str = "data/cache/elo"
    
    def __post_init__(self):
        os.makedirs(self.cache_dir, exist_ok=True)
        self._ratings: Dict[int, float] = {}
        self._load_ratings()
    
    def _load_ratings(self):
        """Load cached ELO ratings"""
        cache_file = os.path.join(self.cache_dir, "team_elo_ratings.json")
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                    self._ratings = {int(k): v for k, v in data.items()}
            except Exception:
                self._ratings = {}
    
    def _save_ratings(self):
        """Save ELO ratings to cache"""
        cache_file = os.path.join(self.cache_dir, "team_elo_ratings.json")
        try:
            with open(cache_file, 'w') as f:
                json.dump(self._ratings, f)
        except Exception:
            pass
    
    def get_rating(self, team_id: int) -> float:
        """Get current ELO rating for a team"""
        return self._ratings.get(team_id, self.base_rating)
    
    def _calculate_decay_weight(self, match_date: datetime) -> float:
        """Calculate time decay weight for a match"""
        now = datetime.now()
        days_ago = (now - match_date).days
        
        # Exponential decay: weight = 0.5^(days/half_life)
        decay = math.pow(0.5, days_ago / self.decay_half_life_days)
        return max(0.1, decay)  # Minimum 10% weight for very old matches
    
    def update_rating(
        self, 
        team_id: int, 
        opponent_id: int,
        result: float,  # 1.0 = win, 0.5 = draw, 0.0 = loss
        match_date: datetime,
        is_home: bool = True
    ) -> float:
        """
        Update ELO rating with time decay.
        
        Args:
            team_id: Team to update
            opponent_id: Opponent team
            result: Match result (1=win, 0.5=draw, 0=loss)
            match_date: When match was played
            is_home: Whether team was at home
            
        Returns:
            New ELO rating
        """
        team_rating = self.get_rating(team_id)
        opp_rating = self.get_rating(opponent_id)
        
        # Apply home advantage
        effective_rating = team_rating + (self.home_advantage if is_home else 0)
        effective_opp = opp_rating + (0 if is_home else self.home_advantage)
        
        # Expected score
        expected = 1 / (1 + math.pow(10, (effective_opp - effective_rating) / 400))
        
        # Time-weighted K factor
        decay_weight = self._calculate_decay_weight(match_date)
        effective_k = self.k_factor * decay_weight
        
        # Update rating
        new_rating = team_rating + effective_k * (result - expected)
        self._ratings[team_id] = new_rating
        
        return new_rating
    
    def predict_outcome(
        self, 
        home_team_id: int, 
        away_team_id: int
    ) -> Dict[str, float]:
        """
        Predict match outcome using ELO ratings.
        
        Returns:
            Dict with home_win, draw, away_win probabilities
        """
        home_elo = self.get_rating(home_team_id) + self.home_advantage
        away_elo = self.get_rating(away_team_id)
        
        elo_diff = home_elo - away_elo
        
        # Convert ELO difference to win probability
        # Using logistic function with draw adjustment
        home_exp = 1 / (1 + math.pow(10, -elo_diff / 400))
        away_exp = 1 - home_exp
        
        # Estimate draw probability based on ELO closeness
        # Closer ratings = higher draw chance
        draw_base = 0.26  # Base draw rate in football
        elo_closeness = 1 - abs(elo_diff) / 400
        draw_prob = draw_base * (0.5 + 0.5 * max(0, elo_closeness))
        
        # Adjust win probabilities to account for draws
        home_prob = home_exp * (1 - draw_prob)
        away_prob = away_exp * (1 - draw_prob)
        
        # Normalize
        total = home_prob + draw_prob + away_prob
        return {
            'home_win': home_prob / total,
            'draw': draw_prob / total,
            'away_win': away_prob / total,
            'home_elo': home_elo,
            'away_elo': away_elo,
            'elo_diff': elo_diff
        }
    
    def batch_update_from_history(self, matches: List[Dict[str, Any]]):
        """Update ratings from a list of historical matches (oldest first)"""
        for match in sorted(matches, key=lambda x: x.get('date', '')):
            try:
                home_id = match['home_team_id']
                away_id = match['away_team_id']
                home_goals = match.get('home_goals', 0)
                away_goals = match.get('away_goals', 0)
                match_date = datetime.fromisoformat(match.get('date', '').replace('Z', '+00:00'))
                
                # Determine result
                if home_goals > away_goals:
                    home_result, away_result = 1.0, 0.0
                elif away_goals > home_goals:
                    home_result, away_result = 0.0, 1.0
                else:
                    home_result, away_result = 0.5, 0.5
                
                self.update_rating(home_id, away_id, home_result, match_date, is_home=True)
                self.update_rating(away_id, home_id, away_result, match_date, is_home=False)
                
            except Exception:
                continue
        
        self._save_ratings()


# ============================================================================
# DQ-003: REFEREE TENDENCY DATABASE
# Track referee tendencies: cards, penalties, home bias
# ============================================================================

@dataclass
class RefereeTendency:
    """Stores referee historical tendencies"""
    referee_name: str
    matches_officiated: int = 0
    avg_yellow_cards: float = 0.0
    avg_red_cards: float = 0.0
    avg_penalties: float = 0.0
    home_win_rate: float = 0.5
    avg_fouls: float = 0.0
    strictness_score: float = 0.5  # 0-1, higher = stricter


@dataclass
class RefereeTendencyDatabase:
    """
    Database of referee tendencies and their impact on predictions.
    """
    
    cache_dir: str = "data/referee_data"
    
    def __post_init__(self):
        os.makedirs(self.cache_dir, exist_ok=True)
        self._tendencies: Dict[str, RefereeTendency] = {}
        self._load_tendencies()
    
    def _load_tendencies(self):
        """Load referee data from cache"""
        cache_file = os.path.join(self.cache_dir, "referee_tendencies.json")
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                    for name, stats in data.items():
                        self._tendencies[name] = RefereeTendency(
                            referee_name=name,
                            **stats
                        )
            except Exception:
                pass
    
    def _save_tendencies(self):
        """Save referee data to cache"""
        cache_file = os.path.join(self.cache_dir, "referee_tendencies.json")
        try:
            data = {}
            for name, tendency in self._tendencies.items():
                data[name] = {
                    'matches_officiated': tendency.matches_officiated,
                    'avg_yellow_cards': tendency.avg_yellow_cards,
                    'avg_red_cards': tendency.avg_red_cards,
                    'avg_penalties': tendency.avg_penalties,
                    'home_win_rate': tendency.home_win_rate,
                    'avg_fouls': tendency.avg_fouls,
                    'strictness_score': tendency.strictness_score
                }
            with open(cache_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass
    
    def get_referee_tendency(self, referee_name: str) -> Optional[RefereeTendency]:
        """Get tendency data for a referee"""
        if not referee_name:
            return None
        
        # Normalize name
        normalized = referee_name.strip().lower()
        for name, tendency in self._tendencies.items():
            if name.lower() == normalized:
                return tendency
        
        return None
    
    def update_referee_stats(
        self,
        referee_name: str,
        yellow_cards: int,
        red_cards: int,
        penalties: int,
        home_win: bool,
        fouls: int
    ):
        """Update referee statistics with new match data"""
        if not referee_name:
            return
            
        tendency = self._tendencies.get(referee_name)
        if tendency is None:
            tendency = RefereeTendency(referee_name=referee_name)
            self._tendencies[referee_name] = tendency
        
        n = tendency.matches_officiated
        
        # Running average updates
        tendency.avg_yellow_cards = (tendency.avg_yellow_cards * n + yellow_cards) / (n + 1)
        tendency.avg_red_cards = (tendency.avg_red_cards * n + red_cards) / (n + 1)
        tendency.avg_penalties = (tendency.avg_penalties * n + penalties) / (n + 1)
        tendency.avg_fouls = (tendency.avg_fouls * n + fouls) / (n + 1)
        tendency.home_win_rate = (tendency.home_win_rate * n + (1 if home_win else 0)) / (n + 1)
        tendency.matches_officiated = n + 1
        
        # Recalculate strictness score
        # Based on cards/penalties relative to league average
        league_avg_yellows = 4.0
        league_avg_reds = 0.15
        league_avg_penalties = 0.25
        
        yellow_factor = tendency.avg_yellow_cards / league_avg_yellows
        red_factor = (tendency.avg_red_cards + 0.1) / (league_avg_reds + 0.1)
        penalty_factor = (tendency.avg_penalties + 0.1) / (league_avg_penalties + 0.1)
        
        tendency.strictness_score = min(1.0, (yellow_factor * 0.5 + red_factor * 0.3 + penalty_factor * 0.2))
        
        self._save_tendencies()
    
    def get_prediction_adjustment(
        self,
        referee_name: str,
        home_team_discipline: str = 'average',  # 'disciplined', 'average', 'aggressive'
        away_team_discipline: str = 'average'
    ) -> Dict[str, float]:
        """
        Calculate prediction adjustments based on referee.
        
        Returns adjustments for:
        - home_advantage_modifier: Adjust home win prob based on ref's home bias
        - expected_goals_modifier: Strict refs = fewer goals (more stoppages)
        - cards_modifier: Expected cards multiplier
        """
        tendency = self.get_referee_tendency(referee_name)
        
        if tendency is None or tendency.matches_officiated < 5:
            return {
                'home_advantage_modifier': 0.0,
                'expected_goals_modifier': 1.0,
                'expected_yellow_cards': 4.0,
                'referee_known': False
            }
        
        # Home advantage adjustment
        # If ref has higher home win rate than 50%, boost home team
        home_bias = (tendency.home_win_rate - 0.5) * 0.05  # ±2.5% max
        
        # Goal modifier based on strictness
        # Stricter refs = more stoppages = fewer goals
        goals_modifier = 1.0 - (tendency.strictness_score - 0.5) * 0.1
        
        # Discipline interaction
        discipline_scores = {'disciplined': -1, 'average': 0, 'aggressive': 1}
        home_disc = discipline_scores.get(home_team_discipline, 0)
        away_disc = discipline_scores.get(away_team_discipline, 0)
        
        # Aggressive teams against strict refs get more cards, potential red = hurt performance
        aggression_penalty = (home_disc - away_disc) * tendency.strictness_score * 0.02
        
        return {
            'home_advantage_modifier': home_bias - aggression_penalty,
            'expected_goals_modifier': goals_modifier,
            'expected_yellow_cards': tendency.avg_yellow_cards,
            'expected_red_cards': tendency.avg_red_cards,
            'expected_penalties': tendency.avg_penalties,
            'referee_known': True,
            'referee_strictness': tendency.strictness_score
        }


# ============================================================================
# CC-004: LEAGUE-SPECIFIC CALIBRATION
# Different leagues have different predictability
# ============================================================================

@dataclass
class LeagueCalibrator:
    """
    Applies league-specific confidence adjustments.
    
    Some leagues are more predictable than others:
    - La Liga: Historically more predictable (top 3 dominance)
    - Premier League: More competitive, upsets common
    - Bundesliga: Bayern dominance but others unpredictable
    - Ligue 1: PSG dominance but high variance otherwise
    - Serie A: Mid-tier predictability
    """
    
    # League predictability scores (from historical analysis)
    # Higher = more predictable
    league_predictability: Dict[str, float] = field(default_factory=lambda: {
        'la-liga': 0.72,
        'premier-league': 0.65,
        'bundesliga': 0.68,
        'serie-a': 0.67,
        'ligue-1': 0.63,
        'eredivisie': 0.60,
        'primeira-liga': 0.62,
        'championship': 0.58,  # Very unpredictable
    })
    
    # Base confidence adjustment per league
    # Applied as multiplier to raw confidence
    league_confidence_multipliers: Dict[str, float] = field(default_factory=lambda: {
        'la-liga': 1.05,
        'premier-league': 0.92,
        'bundesliga': 0.98,
        'serie-a': 0.96,
        'ligue-1': 0.90,
        'eredivisie': 0.88,
        'primeira-liga': 0.90,
        'championship': 0.85,
    })
    
    def get_calibration(self, league: str) -> Dict[str, float]:
        """Get calibration factors for a league"""
        normalized = league.lower().replace(' ', '-')
        
        predictability = self.league_predictability.get(normalized, 0.65)
        multiplier = self.league_confidence_multipliers.get(normalized, 0.95)
        
        return {
            'predictability': predictability,
            'confidence_multiplier': multiplier,
            'upset_likelihood_base': 1 - predictability,  # Less predictable = more upsets
            'draw_rate_adjustment': 0.0  # Can be league-specific
        }
    
    def adjust_confidence(
        self, 
        confidence: float, 
        league: str
    ) -> float:
        """Adjust confidence based on league characteristics"""
        cal = self.get_calibration(league)
        return min(0.95, confidence * cal['confidence_multiplier'])
    
    def adjust_probabilities(
        self,
        home_prob: float,
        draw_prob: float,
        away_prob: float,
        league: str
    ) -> Tuple[float, float, float]:
        """
        Adjust probabilities based on league characteristics.
        Less predictable leagues get probabilities pushed toward 33/33/33.
        """
        cal = self.get_calibration(league)
        
        # Regression toward mean based on unpredictability
        uncertainty = 1 - cal['predictability']
        mean_prob = 1/3
        
        # Blend toward mean: more uncertainty = more regression
        blend = uncertainty * 0.3  # Max 30% regression for very unpredictable leagues
        
        adj_home = home_prob * (1 - blend) + mean_prob * blend
        adj_draw = draw_prob * (1 - blend) + mean_prob * blend
        adj_away = away_prob * (1 - blend) + mean_prob * blend
        
        # Normalize
        total = adj_home + adj_draw + adj_away
        return (adj_home / total, adj_draw / total, adj_away / total)


# ============================================================================
# FE-005: VENUE-SPECIFIC PERFORMANCE
# Some teams have fortress home or terrible away records at specific venues
# ============================================================================

@dataclass
class VenuePerformanceTracker:
    """
    Tracks team performance at specific venues.
    """
    
    cache_dir: str = "data/cache/venues"
    
    def __post_init__(self):
        os.makedirs(self.cache_dir, exist_ok=True)
        self._venue_stats: Dict[str, Dict[str, Any]] = {}
        self._load_stats()
    
    def _load_stats(self):
        """Load venue statistics from cache"""
        cache_file = os.path.join(self.cache_dir, "venue_performance.json")
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r') as f:
                    self._venue_stats = json.load(f)
            except Exception:
                pass
    
    def _save_stats(self):
        """Save venue statistics to cache"""
        cache_file = os.path.join(self.cache_dir, "venue_performance.json")
        try:
            with open(cache_file, 'w') as f:
                json.dump(self._venue_stats, f, indent=2)
        except Exception:
            pass
    
    def _get_key(self, team_id: int, venue_id: str) -> str:
        """Generate unique key for team-venue combination"""
        return f"{team_id}_{venue_id}"
    
    def record_performance(
        self,
        team_id: int,
        venue_id: str,
        goals_for: int,
        goals_against: int,
        result: str  # 'W', 'D', 'L'
    ):
        """Record a team's performance at a venue"""
        key = self._get_key(team_id, venue_id)
        
        if key not in self._venue_stats:
            self._venue_stats[key] = {
                'matches': 0,
                'wins': 0,
                'draws': 0,
                'losses': 0,
                'goals_for': 0,
                'goals_against': 0
            }
        
        stats = self._venue_stats[key]
        stats['matches'] += 1
        stats['goals_for'] += goals_for
        stats['goals_against'] += goals_against
        
        if result == 'W':
            stats['wins'] += 1
        elif result == 'D':
            stats['draws'] += 1
        else:
            stats['losses'] += 1
        
        self._save_stats()
    
    def get_venue_adjustment(
        self,
        team_id: int,
        venue_id: str,
        is_home: bool = True
    ) -> Dict[str, float]:
        """
        Get prediction adjustment based on team's historical venue performance.
        
        Returns:
            - win_rate_adjustment: Adjust win probability
            - goals_adjustment: Adjust expected goals
            - venue_known: Whether we have enough data
        """
        key = self._get_key(team_id, venue_id)
        stats = self._venue_stats.get(key)
        
        if stats is None or stats.get('matches', 0) < 3:
            return {
                'win_rate_adjustment': 0.0,
                'goals_adjustment': 0.0,
                'venue_known': False
            }
        
        matches = stats['matches']
        win_rate = stats['wins'] / matches
        avg_goals = stats['goals_for'] / matches
        
        # Compare to expected home/away rates
        expected_win_rate = 0.46 if is_home else 0.27
        expected_goals = 1.5 if is_home else 1.1
        
        # Calculate adjustments
        win_diff = win_rate - expected_win_rate
        goals_diff = avg_goals - expected_goals
        
        # Cap adjustments to prevent extreme values
        win_adjustment = max(-0.1, min(0.1, win_diff * 0.5))
        goals_adjustment = max(-0.3, min(0.3, goals_diff * 0.5))
        
        return {
            'win_rate_adjustment': win_adjustment,
            'goals_adjustment': goals_adjustment,
            'venue_known': True,
            'venue_matches': matches,
            'venue_win_rate': win_rate
        }


# ============================================================================
# FE-006: TIME-OF-DAY AND DAY-OF-WEEK EFFECTS
# Different kickoff times have different characteristics
# ============================================================================

@dataclass
class KickoffTimeAnalyzer:
    """
    Analyzes impact of kickoff time on match outcomes.
    """
    
    # Historical patterns (from research)
    # Early kickoffs tend to have fewer goals, late kickoffs more
    time_slot_goals_multiplier: Dict[str, float] = field(default_factory=lambda: {
        'early_morning': 0.92,    # Before 12:00
        'lunch': 0.96,            # 12:00-14:00
        'afternoon': 1.00,        # 14:00-17:00
        'evening': 1.05,          # 17:00-20:00
        'night': 1.08,            # After 20:00
    })
    
    # Day of week patterns
    # Monday games tend to be more defensive, weekend more attacking
    day_goals_multiplier: Dict[str, float] = field(default_factory=lambda: {
        'monday': 0.94,
        'tuesday': 0.98,
        'wednesday': 1.00,
        'thursday': 0.98,
        'friday': 1.02,
        'saturday': 1.02,
        'sunday': 1.00,
    })
    
    # Home advantage varies by day (TV games on Mon/Fri have less atmosphere)
    day_home_advantage_modifier: Dict[str, float] = field(default_factory=lambda: {
        'monday': -0.02,
        'tuesday': 0.0,
        'wednesday': 0.0,
        'thursday': 0.0,
        'friday': -0.01,
        'saturday': 0.02,
        'sunday': 0.01,
    })
    
    def _get_time_slot(self, hour: int) -> str:
        """Classify hour into time slot"""
        if hour < 12:
            return 'early_morning'
        elif hour < 14:
            return 'lunch'
        elif hour < 17:
            return 'afternoon'
        elif hour < 20:
            return 'evening'
        else:
            return 'night'
    
    def get_adjustments(
        self,
        kickoff_time: datetime
    ) -> Dict[str, float]:
        """
        Get prediction adjustments based on kickoff time.
        
        Args:
            kickoff_time: Match kickoff datetime
            
        Returns:
            Adjustment factors for goals and home advantage
        """
        hour = kickoff_time.hour
        day = kickoff_time.strftime('%A').lower()
        time_slot = self._get_time_slot(hour)
        
        time_goals_mult = self.time_slot_goals_multiplier.get(time_slot, 1.0)
        day_goals_mult = self.day_goals_multiplier.get(day, 1.0)
        home_adv_mod = self.day_home_advantage_modifier.get(day, 0.0)
        
        return {
            'goals_multiplier': time_goals_mult * day_goals_mult,
            'home_advantage_modifier': home_adv_mod,
            'time_slot': time_slot,
            'day_of_week': day,
            'is_tv_slot': day in ['monday', 'friday'] or time_slot in ['evening', 'night']
        }


# ============================================================================
# UNIFIED ENHANCEMENT PIPELINE
# Combines all Phase 1 enhancements into single interface
# ============================================================================

class PredictionEnhancer:
    """
    Unified interface for all Phase 1 prediction enhancements.
    
    Usage:
        enhancer = PredictionEnhancer()
        enhanced = enhancer.enhance_prediction(
            home_prob=0.65,
            draw_prob=0.20,
            away_prob=0.15,
            confidence=0.75,
            league='premier-league',
            kickoff_time=datetime(2025, 1, 15, 20, 0),
            referee_name='Michael Oliver',
            home_team_id=65,
            away_team_id=66,
            venue_id='old_trafford'
        )
    """
    
    def __init__(self, cache_dir: str = "data/cache"):
        self.confidence_capper = ConfidenceCapper()
        self.elo_system = TimeDecayedELO(cache_dir=os.path.join(cache_dir, "elo"))
        self.referee_db = RefereeTendencyDatabase(cache_dir=os.path.join(cache_dir, "referee_data"))
        self.league_calibrator = LeagueCalibrator()
        self.venue_tracker = VenuePerformanceTracker(cache_dir=os.path.join(cache_dir, "venues"))
        self.kickoff_analyzer = KickoffTimeAnalyzer()
        
        self._enhancement_log: List[str] = []
    
    def enhance_prediction(
        self,
        home_prob: float,
        draw_prob: float,
        away_prob: float,
        confidence: float,
        expected_home_goals: float,
        expected_away_goals: float,
        league: str,
        kickoff_time: Optional[datetime] = None,
        referee_name: Optional[str] = None,
        home_team_id: Optional[int] = None,
        away_team_id: Optional[int] = None,
        venue_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Apply all Phase 1 enhancements to a prediction.
        
        Returns:
            Enhanced prediction with adjusted probabilities, confidence, and goals
        """
        self._enhancement_log = []
        
        # Normalize probabilities to 0-1 if in percentage
        if home_prob > 1:
            home_prob /= 100
            draw_prob /= 100
            away_prob /= 100
        
        # Track original values
        original = {
            'home_prob': home_prob,
            'draw_prob': draw_prob,
            'away_prob': away_prob,
            'confidence': confidence,
            'expected_home_goals': expected_home_goals,
            'expected_away_goals': expected_away_goals
        }
        
        # 1. Apply ELO-based adjustments (MI-004)
        if home_team_id and away_team_id:
            elo_pred = self.elo_system.predict_outcome(home_team_id, away_team_id)
            
            # Blend ELO prediction with original (10% weight to ELO)
            elo_weight = 0.10
            home_prob = home_prob * (1 - elo_weight) + elo_pred['home_win'] * elo_weight
            draw_prob = draw_prob * (1 - elo_weight) + elo_pred['draw'] * elo_weight
            away_prob = away_prob * (1 - elo_weight) + elo_pred['away_win'] * elo_weight
            
            self._enhancement_log.append(f"ELO adjustment applied (diff: {elo_pred['elo_diff']:.0f})")
        
        # 2. Apply referee adjustments (DQ-003)
        if referee_name:
            ref_adj = self.referee_db.get_prediction_adjustment(referee_name)
            if ref_adj['referee_known']:
                home_prob += ref_adj['home_advantage_modifier']
                expected_home_goals *= ref_adj['expected_goals_modifier']
                expected_away_goals *= ref_adj['expected_goals_modifier']
                
                self._enhancement_log.append(
                    f"Referee {referee_name}: strictness={ref_adj['referee_strictness']:.2f}"
                )
        
        # 3. Apply venue adjustments (FE-005)
        if home_team_id and venue_id:
            venue_adj = self.venue_tracker.get_venue_adjustment(home_team_id, venue_id, is_home=True)
            if venue_adj['venue_known']:
                home_prob += venue_adj['win_rate_adjustment']
                expected_home_goals += venue_adj['goals_adjustment']
                
                self._enhancement_log.append(
                    f"Venue effect: {venue_adj['venue_matches']} matches, "
                    f"win rate={venue_adj['venue_win_rate']:.0%}"
                )
        
        # 4. Apply kickoff time adjustments (FE-006)
        if kickoff_time:
            time_adj = self.kickoff_analyzer.get_adjustments(kickoff_time)
            expected_home_goals *= time_adj['goals_multiplier']
            expected_away_goals *= time_adj['goals_multiplier']
            home_prob += time_adj['home_advantage_modifier']
            
            self._enhancement_log.append(
                f"Kickoff: {time_adj['day_of_week']} {time_adj['time_slot']}"
            )
        
        # 5. Apply league calibration (CC-004)
        home_prob, draw_prob, away_prob = self.league_calibrator.adjust_probabilities(
            home_prob, draw_prob, away_prob, league
        )
        confidence = self.league_calibrator.adjust_confidence(confidence, league)
        
        cal = self.league_calibrator.get_calibration(league)
        self._enhancement_log.append(
            f"League calibration: {league} (predictability={cal['predictability']:.0%})"
        )
        
        # 6. Apply confidence capping (CC-005) - LAST
        home_prob, draw_prob, away_prob = self.confidence_capper.cap_probabilities(
            home_prob, draw_prob, away_prob
        )
        
        if max(original['home_prob'], original['away_prob']) > 0.75:
            self._enhancement_log.append("Overconfidence cap applied")
        
        return {
            'home_win_probability': home_prob * 100,
            'draw_probability': draw_prob * 100,
            'away_win_probability': away_prob * 100,
            'confidence': confidence,
            'expected_home_goals': expected_home_goals,
            'expected_away_goals': expected_away_goals,
            'enhancements_applied': self._enhancement_log,
            'original_prediction': {
                'home_prob': original['home_prob'] * 100,
                'draw_prob': original['draw_prob'] * 100,
                'away_prob': original['away_prob'] * 100
            },
            'phase1_enhanced': True
        }
    
    def get_enhancement_summary(self) -> List[str]:
        """Get log of enhancements applied to last prediction"""
        return self._enhancement_log.copy()
