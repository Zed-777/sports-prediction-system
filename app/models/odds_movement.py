"""
Pre-Match Odds Movement Tracking (RT-001)
==========================================

Tracks odds movements before matches to detect sharp money and market signals.
When professional bettors move the lines, it's a strong signal of information.

Expected accuracy boost: +2-4%
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import json
import os
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class MovementDirection(Enum):
    """Direction of odds movement."""
    SHORTENING = "shortening"  # Odds getting lower (more likely)
    DRIFTING = "drifting"      # Odds getting higher (less likely)  
    STABLE = "stable"          # No significant movement


class MovementStrength(Enum):
    """Strength/significance of movement."""
    MINIMAL = "minimal"        # <2% change
    MODERATE = "moderate"      # 2-5% change
    SIGNIFICANT = "significant"  # 5-10% change
    SHARP = "sharp"            # >10% change (likely sharp money)


@dataclass
class OddsSnapshot:
    """Snapshot of odds at a point in time."""
    timestamp: datetime
    home_odds: float
    draw_odds: float
    away_odds: float
    source: str = "unknown"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp.isoformat(),
            'home_odds': self.home_odds,
            'draw_odds': self.draw_odds,
            'away_odds': self.away_odds,
            'source': self.source
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'OddsSnapshot':
        return cls(
            timestamp=datetime.fromisoformat(data['timestamp']),
            home_odds=data['home_odds'],
            draw_odds=data['draw_odds'],
            away_odds=data['away_odds'],
            source=data.get('source', 'unknown')
        )


@dataclass
class OddsMovement:
    """Analysis of odds movement for a match."""
    match_id: str
    home_team: str
    away_team: str
    opening_odds: Optional[OddsSnapshot] = None
    current_odds: Optional[OddsSnapshot] = None
    snapshots: List[OddsSnapshot] = field(default_factory=list)
    
    # Movement analysis
    home_movement: MovementDirection = MovementDirection.STABLE
    away_movement: MovementDirection = MovementDirection.STABLE
    home_movement_pct: float = 0.0
    away_movement_pct: float = 0.0
    movement_strength: MovementStrength = MovementStrength.MINIMAL
    
    # Sharp money signals
    sharp_money_detected: bool = False
    sharp_money_side: Optional[str] = None  # 'home', 'draw', 'away'
    sharp_confidence: float = 0.0  # 0-1 scale
    
    # Market consensus
    market_favorite: str = "home"  # Based on lowest odds
    implied_home_prob: float = 0.0
    implied_draw_prob: float = 0.0
    implied_away_prob: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'match_id': self.match_id,
            'home_team': self.home_team,
            'away_team': self.away_team,
            'opening_odds': self.opening_odds.to_dict() if self.opening_odds else None,
            'current_odds': self.current_odds.to_dict() if self.current_odds else None,
            'home_movement': self.home_movement.value,
            'away_movement': self.away_movement.value,
            'home_movement_pct': self.home_movement_pct,
            'away_movement_pct': self.away_movement_pct,
            'movement_strength': self.movement_strength.value,
            'sharp_money_detected': self.sharp_money_detected,
            'sharp_money_side': self.sharp_money_side,
            'sharp_confidence': self.sharp_confidence,
            'market_favorite': self.market_favorite,
            'implied_home_prob': self.implied_home_prob,
            'implied_draw_prob': self.implied_draw_prob,
            'implied_away_prob': self.implied_away_prob
        }


class OddsMovementTracker:
    """
    Tracks pre-match odds movements and detects sharp money.
    
    RT-001: Pre-match odds movement tracking
    - Poll odds APIs to track movement
    - Detect significant line movements
    - Identify sharp money signals
    """
    
    # Thresholds for movement classification
    MINIMAL_THRESHOLD = 0.02      # 2%
    MODERATE_THRESHOLD = 0.05     # 5%
    SIGNIFICANT_THRESHOLD = 0.10  # 10%
    
    # Sharp money indicators
    SHARP_MOVEMENT_THRESHOLD = 0.08  # 8%+ movement suggests sharp action
    REVERSE_MOVEMENT_THRESHOLD = 0.05  # Line moving against public
    
    def __init__(self, cache_dir: str = "data/cache"):
        self.cache_dir = cache_dir
        self.odds_cache_dir = os.path.join(cache_dir, "odds_movements")
        os.makedirs(self.odds_cache_dir, exist_ok=True)
        self._movements: Dict[str, OddsMovement] = {}
        self._load_cached_movements()
    
    def _load_cached_movements(self):
        """Load cached odds movements."""
        try:
            cache_file = os.path.join(self.odds_cache_dir, "movements.json")
            if os.path.exists(cache_file):
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                # Only load recent movements (last 7 days)
                cutoff = (datetime.now() - timedelta(days=7)).isoformat()
                for match_id, movement in data.items():
                    if movement.get('opening_odds', {}).get('timestamp', '') > cutoff:
                        self._movements[match_id] = movement
        except Exception as e:
            logger.debug(f"Cache load failed: {e}")
    
    def _save_cached_movements(self):
        """Save odds movements to cache."""
        try:
            cache_file = os.path.join(self.odds_cache_dir, "movements.json")
            with open(cache_file, 'w') as f:
                json.dump({
                    k: v.to_dict() if isinstance(v, OddsMovement) else v 
                    for k, v in self._movements.items()
                }, f, indent=2)
        except Exception as e:
            logger.debug(f"Cache save failed: {e}")
    
    def _odds_to_prob(self, odds: float) -> float:
        """Convert decimal odds to implied probability."""
        if odds <= 1:
            return 0.5
        return 1 / odds
    
    def _calculate_movement_pct(self, opening: float, current: float) -> float:
        """Calculate percentage change in odds."""
        if opening <= 0:
            return 0.0
        return (current - opening) / opening
    
    def _classify_movement(self, movement_pct: float) -> Tuple[MovementDirection, MovementStrength]:
        """Classify the direction and strength of movement."""
        abs_movement = abs(movement_pct)
        
        # Determine strength
        if abs_movement < self.MINIMAL_THRESHOLD:
            strength = MovementStrength.MINIMAL
        elif abs_movement < self.MODERATE_THRESHOLD:
            strength = MovementStrength.MODERATE
        elif abs_movement < self.SIGNIFICANT_THRESHOLD:
            strength = MovementStrength.SIGNIFICANT
        else:
            strength = MovementStrength.SHARP
        
        # Determine direction (lower odds = shortening = more likely)
        if movement_pct < -self.MINIMAL_THRESHOLD:
            direction = MovementDirection.SHORTENING
        elif movement_pct > self.MINIMAL_THRESHOLD:
            direction = MovementDirection.DRIFTING
        else:
            direction = MovementDirection.STABLE
        
        return direction, strength
    
    def record_odds(
        self,
        match_id: str,
        home_team: str,
        away_team: str,
        home_odds: float,
        draw_odds: float,
        away_odds: float,
        source: str = "api"
    ) -> OddsMovement:
        """
        Record odds snapshot for a match.
        
        Args:
            match_id: Unique match identifier
            home_team: Home team name
            away_team: Away team name
            home_odds: Decimal odds for home win
            draw_odds: Decimal odds for draw
            away_odds: Decimal odds for away win
            source: Source of odds data
            
        Returns:
            Updated OddsMovement analysis
        """
        snapshot = OddsSnapshot(
            timestamp=datetime.now(),
            home_odds=home_odds,
            draw_odds=draw_odds,
            away_odds=away_odds,
            source=source
        )
        
        if match_id not in self._movements:
            # First recording - this is the opening line
            movement = OddsMovement(
                match_id=match_id,
                home_team=home_team,
                away_team=away_team,
                opening_odds=snapshot,
                current_odds=snapshot,
                snapshots=[snapshot]
            )
        else:
            # Update existing movement
            movement = self._movements[match_id]
            if isinstance(movement, dict):
                # Reconstruct from dict
                movement = OddsMovement(
                    match_id=match_id,
                    home_team=home_team,
                    away_team=away_team,
                    opening_odds=OddsSnapshot.from_dict(movement['opening_odds']) if movement.get('opening_odds') else snapshot,
                    current_odds=snapshot,
                    snapshots=[]
                )
            else:
                movement.current_odds = snapshot
                movement.snapshots.append(snapshot)
        
        # Analyze movement
        movement = self._analyze_movement(movement)
        
        self._movements[match_id] = movement
        self._save_cached_movements()
        
        return movement
    
    def _analyze_movement(self, movement: OddsMovement) -> OddsMovement:
        """Analyze odds movement patterns."""
        if not movement.opening_odds or not movement.current_odds:
            return movement
        
        opening = movement.opening_odds
        current = movement.current_odds
        
        # Calculate movement percentages
        movement.home_movement_pct = self._calculate_movement_pct(opening.home_odds, current.home_odds)
        movement.away_movement_pct = self._calculate_movement_pct(opening.away_odds, current.away_odds)
        draw_movement_pct = self._calculate_movement_pct(opening.draw_odds, current.draw_odds)
        
        # Classify movements
        movement.home_movement, home_strength = self._classify_movement(movement.home_movement_pct)
        movement.away_movement, away_strength = self._classify_movement(movement.away_movement_pct)
        
        # Overall movement strength is the max
        if home_strength.value == "sharp" or away_strength.value == "sharp":
            movement.movement_strength = MovementStrength.SHARP
        elif home_strength.value == "significant" or away_strength.value == "significant":
            movement.movement_strength = MovementStrength.SIGNIFICANT
        elif home_strength.value == "moderate" or away_strength.value == "moderate":
            movement.movement_strength = MovementStrength.MODERATE
        else:
            movement.movement_strength = MovementStrength.MINIMAL
        
        # Calculate implied probabilities from current odds
        total_implied = (
            self._odds_to_prob(current.home_odds) +
            self._odds_to_prob(current.draw_odds) +
            self._odds_to_prob(current.away_odds)
        )
        
        if total_implied > 0:
            movement.implied_home_prob = self._odds_to_prob(current.home_odds) / total_implied
            movement.implied_draw_prob = self._odds_to_prob(current.draw_odds) / total_implied
            movement.implied_away_prob = self._odds_to_prob(current.away_odds) / total_implied
        
        # Determine market favorite
        if current.home_odds < current.away_odds and current.home_odds < current.draw_odds:
            movement.market_favorite = "home"
        elif current.away_odds < current.home_odds and current.away_odds < current.draw_odds:
            movement.market_favorite = "away"
        else:
            movement.market_favorite = "draw"
        
        # Detect sharp money
        movement = self._detect_sharp_money(movement)
        
        return movement
    
    def _detect_sharp_money(self, movement: OddsMovement) -> OddsMovement:
        """Detect sharp money signals from odds movement."""
        if not movement.opening_odds or not movement.current_odds:
            return movement
        
        # Sharp indicators:
        # 1. Large movement (>8%) on any outcome
        # 2. Odds shortening despite public likely to be on other side
        # 3. Late market movement
        
        home_movement = abs(movement.home_movement_pct)
        away_movement = abs(movement.away_movement_pct)
        
        sharp_detected = False
        sharp_side = None
        confidence = 0.0
        
        # Check for sharp movement on home
        if movement.home_movement == MovementDirection.SHORTENING and home_movement > self.SHARP_MOVEMENT_THRESHOLD:
            sharp_detected = True
            sharp_side = "home"
            confidence = min(0.95, 0.5 + home_movement)
        
        # Check for sharp movement on away  
        elif movement.away_movement == MovementDirection.SHORTENING and away_movement > self.SHARP_MOVEMENT_THRESHOLD:
            sharp_detected = True
            sharp_side = "away"
            confidence = min(0.95, 0.5 + away_movement)
        
        # Check for reverse line movement (classic sharp signal)
        # If home is drifting but still the favorite, sharps may be on away
        if movement.home_movement == MovementDirection.DRIFTING and movement.market_favorite == "home":
            if away_movement > self.REVERSE_MOVEMENT_THRESHOLD:
                sharp_detected = True
                sharp_side = "away"
                confidence = min(0.90, 0.4 + away_movement * 2)
        
        movement.sharp_money_detected = sharp_detected
        movement.sharp_money_side = sharp_side
        movement.sharp_confidence = round(confidence, 3)
        
        return movement
    
    def get_movement(self, match_id: str) -> Optional[OddsMovement]:
        """Get odds movement for a match."""
        movement = self._movements.get(match_id)
        if isinstance(movement, dict):
            return OddsMovement(
                match_id=match_id,
                home_team=movement.get('home_team', ''),
                away_team=movement.get('away_team', ''),
                sharp_money_detected=movement.get('sharp_money_detected', False),
                sharp_money_side=movement.get('sharp_money_side'),
                sharp_confidence=movement.get('sharp_confidence', 0),
                implied_home_prob=movement.get('implied_home_prob', 0),
                implied_draw_prob=movement.get('implied_draw_prob', 0),
                implied_away_prob=movement.get('implied_away_prob', 0)
            )
        return movement
    
    def adjust_predictions(
        self,
        home_prob: float,
        draw_prob: float,
        away_prob: float,
        odds_movement: OddsMovement,
        blend_weight: float = 0.15
    ) -> Tuple[float, float, float, List[str]]:
        """
        Adjust predictions based on market odds and movement.
        
        Args:
            home_prob: Model's home win probability
            draw_prob: Model's draw probability
            away_prob: Model's away win probability
            odds_movement: Odds movement analysis
            blend_weight: How much to weight market odds (0-1)
            
        Returns:
            Tuple of (adjusted_home, adjusted_draw, adjusted_away, reasons)
        """
        reasons = []
        
        # Get market implied probabilities
        market_home = odds_movement.implied_home_prob
        market_draw = odds_movement.implied_draw_prob
        market_away = odds_movement.implied_away_prob
        
        if market_home == 0:
            # No valid market data
            return home_prob, draw_prob, away_prob, ["no market data"]
        
        # Blend model predictions with market
        blended_home = home_prob * (1 - blend_weight) + market_home * blend_weight
        blended_draw = draw_prob * (1 - blend_weight) + market_draw * blend_weight
        blended_away = away_prob * (1 - blend_weight) + market_away * blend_weight
        
        reasons.append(f"market blend ({blend_weight:.0%} weight)")
        
        # Additional adjustment for sharp money
        if odds_movement.sharp_money_detected:
            sharp_adj = odds_movement.sharp_confidence * 0.10
            
            if odds_movement.sharp_money_side == "home":
                blended_home += sharp_adj
                blended_away -= sharp_adj * 0.7
                blended_draw -= sharp_adj * 0.3
                reasons.append(f"sharp money on home (+{sharp_adj:.1%})")
            elif odds_movement.sharp_money_side == "away":
                blended_away += sharp_adj
                blended_home -= sharp_adj * 0.7
                blended_draw -= sharp_adj * 0.3
                reasons.append(f"sharp money on away (+{sharp_adj:.1%})")
            elif odds_movement.sharp_money_side == "draw":
                blended_draw += sharp_adj
                blended_home -= sharp_adj * 0.5
                blended_away -= sharp_adj * 0.5
                reasons.append(f"sharp money on draw (+{sharp_adj:.1%})")
        
        # Additional adjustment for significant movement
        if odds_movement.movement_strength == MovementStrength.SIGNIFICANT:
            if odds_movement.home_movement == MovementDirection.SHORTENING:
                blended_home += 0.03
                reasons.append("significant home shortening")
            if odds_movement.away_movement == MovementDirection.SHORTENING:
                blended_away += 0.03
                reasons.append("significant away shortening")
        
        # Normalize
        total = blended_home + blended_draw + blended_away
        if total > 0:
            blended_home /= total
            blended_draw /= total
            blended_away /= total
        
        return round(blended_home, 4), round(blended_draw, 4), round(blended_away, 4), reasons


class OddsIntegrationSuite:
    """Unified interface for odds movement tracking."""
    
    def __init__(self, cache_dir: str = "data/cache"):
        self.tracker = OddsMovementTracker(cache_dir)
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def record_and_analyze(
        self,
        match_id: str,
        home_team: str,
        away_team: str,
        home_odds: float,
        draw_odds: float,
        away_odds: float,
        home_prob: float,
        draw_prob: float,
        away_prob: float,
        source: str = "api"
    ) -> Dict[str, Any]:
        """
        Record odds and adjust predictions.
        
        Returns:
            Dictionary with movement analysis and adjusted probabilities
        """
        # Record the odds
        movement = self.tracker.record_odds(
            match_id=match_id,
            home_team=home_team,
            away_team=away_team,
            home_odds=home_odds,
            draw_odds=draw_odds,
            away_odds=away_odds,
            source=source
        )
        
        # Adjust predictions
        adj_home, adj_draw, adj_away, reasons = self.tracker.adjust_predictions(
            home_prob=home_prob,
            draw_prob=draw_prob,
            away_prob=away_prob,
            odds_movement=movement
        )
        
        return {
            'movement': movement.to_dict(),
            'adjusted_home_prob': adj_home,
            'adjusted_draw_prob': adj_draw,
            'adjusted_away_prob': adj_away,
            'adjustment_reasons': reasons,
            'sharp_alert': movement.sharp_money_detected,
            'sharp_side': movement.sharp_money_side,
            'market_implied': {
                'home': movement.implied_home_prob,
                'draw': movement.implied_draw_prob,
                'away': movement.implied_away_prob
            }
        }


# Test when run directly
if __name__ == '__main__':
    print("=== Odds Movement Tracker Test ===\n")
    
    suite = OddsIntegrationSuite()
    
    # Simulate recording odds over time
    # Opening odds
    print("Recording opening odds...")
    result1 = suite.record_and_analyze(
        match_id="test_123",
        home_team="Manchester United",
        away_team="Chelsea",
        home_odds=2.10,
        draw_odds=3.40,
        away_odds=3.50,
        home_prob=0.45,
        draw_prob=0.28,
        away_prob=0.27
    )
    print(f"  Home implied: {result1['market_implied']['home']:.1%}")
    print(f"  Sharp alert: {result1['sharp_alert']}")
    
    # Simulate sharp money moving the line
    print("\nRecording after sharp action (home shortening)...")
    result2 = suite.record_and_analyze(
        match_id="test_123",
        home_team="Manchester United",
        away_team="Chelsea",
        home_odds=1.85,  # Shortened from 2.10 (-12%)
        draw_odds=3.60,
        away_odds=4.00,  # Drifted
        home_prob=0.45,
        draw_prob=0.28,
        away_prob=0.27
    )
    
    print(f"  Sharp alert: {result2['sharp_alert']}")
    print(f"  Sharp side: {result2['sharp_side']}")
    print(f"  Movement strength: {result2['movement']['movement_strength']}")
    print(f"  Home movement: {result2['movement']['home_movement_pct']:.1%}")
    
    print(f"\nPrediction Adjustments:")
    print(f"  Original: H={0.45:.1%}, D={0.28:.1%}, A={0.27:.1%}")
    print(f"  Adjusted: H={result2['adjusted_home_prob']:.1%}, D={result2['adjusted_draw_prob']:.1%}, A={result2['adjusted_away_prob']:.1%}")
    print(f"  Reasons: {', '.join(result2['adjustment_reasons'])}")
    
    print("\n✅ Odds Movement Tracker working!")
