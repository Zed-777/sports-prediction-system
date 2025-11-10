#!/usr/bin/env python3
"""
Advanced Analytics Engine
Phase 3: Expected Threat (xT), pressing intensity, formation analysis, and market sentiment
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import json
from datetime import datetime
import requests
from pathlib import Path

@dataclass
class ExpectedThreat:
    """Expected Threat (xT) model for field positions"""
    position_x: float  # 0-100 (penalty box to penalty box)
    position_y: float  # 0-100 (touchline to touchline)
    xt_value: float    # Expected threat value (0-1)
    action_type: str   # pass, shot, cross, dribble

@dataclass
class FormationAnalysis:
    """Formation matchup analysis"""
    home_formation: str
    away_formation: str
    tactical_advantage: str  # home, away, neutral
    key_battles: List[str]
    predicted_style: str
    control_probability: float

@dataclass
class PressingMetrics:
    """Team pressing intensity metrics"""
    team_name: str
    pressing_intensity: float  # 0-1 (1 = very high press)
    defensive_line_height: float  # 0-1 (1 = very high line)
    counter_press_efficiency: float
    press_resistance: float  # How well team handles pressure

@dataclass
class MarketSentiment:
    """Betting market sentiment analysis"""
    home_odds: float
    draw_odds: float
    away_odds: float
    market_confidence: float
    public_sentiment: str  # bullish_home, neutral, bullish_away
    sharp_money_indicator: float

class AdvancedAnalyticsEngine:
    """Sophisticated analytics with xT modeling, tactical analysis, and market data"""
    
    def __init__(self):
        self.analytics_dir = Path("data/analytics")
        self.analytics_dir.mkdir(parents=True, exist_ok=True)
        
        # Expected Threat model (simplified grid-based)
        self.xt_model = self._initialize_xt_model()
        
        # Formation tactical database
        self.formation_database = self._initialize_formation_database()
        
        # Team pressing profiles
        self.pressing_profiles = self._initialize_pressing_profiles()
        
        # Market data sources (simulated)
        self.market_sources = ['Bet365', 'Pinnacle', 'William Hill', 'Betfair']
        
    def _initialize_xt_model(self) -> np.ndarray:
        """Initialize Expected Threat model grid"""
        
        # Create 20x13 grid (pitch divided into zones)
        xt_grid = np.zeros((20, 13))
        
        # Fill grid with realistic xT values
        # Higher values closer to goal, especially central areas
        for i in range(20):
            for j in range(13):
                # Distance from goal (0 = goal line, 1 = halfway line)
                goal_distance = i / 20.0
                
                # Central bias (center of pitch more valuable)
                center_distance = abs(j - 6) / 6.0
                
                # Base xT calculation
                base_xt = (1 - goal_distance) ** 2  # Exponential decay from goal
                central_bonus = (1 - center_distance) * 0.3  # Central areas bonus
                
                # Special zones
                if i <= 2 and 4 <= j <= 8:  # Penalty area
                    base_xt *= 2.0
                elif i <= 4 and 3 <= j <= 9:  # Extended box
                    base_xt *= 1.5
                elif i >= 18:  # Own half
                    base_xt *= 0.1
                
                xt_grid[i, j] = min(1.0, base_xt + central_bonus)
        
        return xt_grid
    
    def _initialize_formation_database(self) -> Dict:
        """Initialize formation tactical database"""
        
        return {
            '4-3-3': {
                'attacking_width': 0.8,
                'defensive_solidity': 0.6,
                'midfield_control': 0.7,
                'counter_attack_speed': 0.9,
                'vulnerable_to': ['4-2-3-1', '3-5-2'],
                'strong_against': ['4-4-2', '3-4-3']
            },
            '4-2-3-1': {
                'attacking_width': 0.6,
                'defensive_solidity': 0.8,
                'midfield_control': 0.9,
                'counter_attack_speed': 0.6,
                'vulnerable_to': ['4-3-3', '4-1-4-1'],
                'strong_against': ['4-4-2', '3-5-2']
            },
            '4-4-2': {
                'attacking_width': 0.5,
                'defensive_solidity': 0.9,
                'midfield_control': 0.5,
                'counter_attack_speed': 0.7,
                'vulnerable_to': ['4-2-3-1', '4-3-3'],
                'strong_against': ['3-5-2', '5-3-2']
            },
            '3-5-2': {
                'attacking_width': 0.9,
                'defensive_solidity': 0.7,
                'midfield_control': 0.8,
                'counter_attack_speed': 0.5,
                'vulnerable_to': ['4-3-3', '4-2-3-1'],
                'strong_against': ['4-4-2', '5-4-1']
            },
            '5-3-2': {
                'attacking_width': 0.4,
                'defensive_solidity': 0.95,
                'midfield_control': 0.4,
                'counter_attack_speed': 0.8,
                'vulnerable_to': ['4-2-3-1', '4-1-4-1'],
                'strong_against': ['4-3-3', '3-4-3']
            }
        }
    
    def _initialize_pressing_profiles(self) -> Dict:
        """Initialize team pressing intensity profiles"""
        
        return {
            'FC Barcelona': PressingMetrics(
                'FC Barcelona', 0.85, 0.80, 0.90, 0.85
            ),
            'Real Madrid CF': PressingMetrics(
                'Real Madrid CF', 0.75, 0.70, 0.80, 0.90
            ),
            'Atlético Madrid': PressingMetrics(
                'Atlético Madrid', 0.90, 0.75, 0.95, 0.85
            ),
            'Sevilla FC': PressingMetrics(
                'Sevilla FC', 0.80, 0.65, 0.85, 0.80
            ),
            'Villarreal CF': PressingMetrics(
                'Villarreal CF', 0.70, 0.60, 0.75, 0.85
            ),
            'Real Betis Balompié': PressingMetrics(
                'Real Betis Balompié', 0.65, 0.55, 0.70, 0.75
            ),
            'Athletic Bilbao': PressingMetrics(
                'Athletic Bilbao', 0.85, 0.70, 0.90, 0.80
            ),
            'Real Sociedad': PressingMetrics(
                'Real Sociedad', 0.75, 0.65, 0.80, 0.85
            ),
            'Valencia CF': PressingMetrics(
                'Valencia CF', 0.60, 0.50, 0.65, 0.70
            ),
            'RCD Mallorca': PressingMetrics(
                'RCD Mallorca', 0.70, 0.60, 0.75, 0.75
            ),
            'Girona FC': PressingMetrics(
                'Girona FC', 0.75, 0.65, 0.80, 0.70
            ),
            'RCD Espanyol de Barcelona': PressingMetrics(
                'RCD Espanyol de Barcelona', 0.65, 0.55, 0.70, 0.65
            ),
            'Real Oviedo': PressingMetrics(
                'Real Oviedo', 0.70, 0.60, 0.75, 0.70
            )
        }
    
    def calculate_expected_threat_advantage(self, home_team: str, away_team: str, 
                                         formation_home: str = '4-3-3', 
                                         formation_away: str = '4-2-3-1') -> Dict:
        """Calculate Expected Threat (xT) advantage between teams"""
        
        # Get team pressing profiles
        home_pressing = self.pressing_profiles.get(home_team, PressingMetrics(home_team, 0.6, 0.5, 0.6, 0.7))
        away_pressing = self.pressing_profiles.get(away_team, PressingMetrics(away_team, 0.6, 0.5, 0.6, 0.7))
        
        # Calculate xT generation capacity
        home_xt_generation = self._calculate_team_xt_generation(home_team, formation_home, home_pressing)
        away_xt_generation = self._calculate_team_xt_generation(away_team, formation_away, away_pressing)
        
        # Calculate xT prevention capacity
        home_xt_prevention = self._calculate_team_xt_prevention(home_team, formation_home, home_pressing)
        away_xt_prevention = self._calculate_team_xt_prevention(away_team, formation_away, away_pressing)
        
        # Net xT advantage
        home_net_xt = home_xt_generation - away_xt_prevention
        away_net_xt = away_xt_generation - home_xt_prevention
        
        # Territory control prediction
        possession_prediction = self._predict_possession_control(
            home_pressing, away_pressing, formation_home, formation_away
        )
        
        return {
            'home_xt_generation': round(home_xt_generation, 3),
            'away_xt_generation': round(away_xt_generation, 3),
            'home_xt_prevention': round(home_xt_prevention, 3),
            'away_xt_prevention': round(away_xt_prevention, 3),
            'home_net_xt_advantage': round(home_net_xt, 3),
            'away_net_xt_advantage': round(away_net_xt, 3),
            'predicted_possession_split': possession_prediction,
            'dominant_team': 'home' if home_net_xt > away_net_xt else 'away',
            'xt_differential': round(abs(home_net_xt - away_net_xt), 3)
        }
    
    def _calculate_team_xt_generation(self, team_name: str, formation: str, 
                                    pressing: PressingMetrics) -> float:
        """Calculate team's Expected Threat generation capacity"""
        
        formation_data = self.formation_database.get(formation, self.formation_database['4-3-3'])
        
        # Base xT generation from formation
        base_xt = formation_data['attacking_width'] * 0.4 + formation_data['counter_attack_speed'] * 0.3
        
        # Team quality multiplier (simplified)
        quality_multipliers = {
            'FC Barcelona': 0.95, 'Real Madrid CF': 0.98, 'Atlético Madrid': 0.80,
            'Sevilla FC': 0.75, 'Villarreal CF': 0.78, 'Real Betis Balompié': 0.70,
            'Athletic Bilbao': 0.72, 'Real Sociedad': 0.76, 'Valencia CF': 0.68,
            'RCD Mallorca': 0.60, 'Girona FC': 0.65, 'RCD Espanyol de Barcelona': 0.58,
            'Real Oviedo': 0.60
        }
        
        quality_mult = quality_multipliers.get(team_name, 0.65)
        
        # Pressing contribution to xT generation
        pressing_boost = pressing.counter_press_efficiency * 0.2
        
        total_xt_generation = (base_xt + pressing_boost) * quality_mult
        
        return min(1.0, total_xt_generation)
    
    def _calculate_team_xt_prevention(self, team_name: str, formation: str,
                                    pressing: PressingMetrics) -> float:
        """Calculate team's Expected Threat prevention capacity"""
        
        formation_data = self.formation_database.get(formation, self.formation_database['4-3-3'])
        
        # Base xT prevention from formation
        base_prevention = formation_data['defensive_solidity'] * 0.5 + formation_data['midfield_control'] * 0.3
        
        # Pressing contribution
        pressing_contribution = (
            pressing.pressing_intensity * 0.3 +
            pressing.defensive_line_height * 0.1 +
            pressing.press_resistance * 0.2
        )
        
        total_prevention = base_prevention + pressing_contribution
        
        return min(1.0, total_prevention)
    
    def _predict_possession_control(self, home_pressing: PressingMetrics, away_pressing: PressingMetrics,
                                  home_formation: str, away_formation: str) -> Dict:
        """Predict possession split between teams"""
        
        home_form_data = self.formation_database.get(home_formation, self.formation_database['4-3-3'])
        away_form_data = self.formation_database.get(away_formation, self.formation_database['4-3-3'])
        
        # Midfield control battle
        home_midfield_strength = (
            home_form_data['midfield_control'] * 0.6 +
            home_pressing.press_resistance * 0.4
        )
        
        away_midfield_strength = (
            away_form_data['midfield_control'] * 0.6 +
            away_pressing.press_resistance * 0.4
        )
        
        # Normalize to possession percentages
        total_strength = home_midfield_strength + away_midfield_strength
        
        if total_strength > 0:
            home_possession = (home_midfield_strength / total_strength) * 100
            away_possession = 100 - home_possession
        else:
            home_possession = away_possession = 50.0
        
        # Add home advantage
        home_possession += 3  # Slight home advantage
        away_possession -= 3
        
        return {
            'home_possession_percent': round(max(35, min(65, home_possession)), 1),
            'away_possession_percent': round(max(35, min(65, away_possession)), 1),
            'control_type': self._determine_control_type(home_possession)
        }
    
    def _determine_control_type(self, home_possession: float) -> str:
        """Determine the type of match control"""
        if home_possession >= 58:
            return 'home_controlled'
        elif home_possession <= 42:
            return 'away_controlled'
        else:
            return 'balanced'
    
    def analyze_formation_matchup(self, home_formation: str, away_formation: str) -> FormationAnalysis:
        """Detailed formation vs formation analysis"""
        
        home_data = self.formation_database.get(home_formation, self.formation_database['4-3-3'])
        away_data = self.formation_database.get(away_formation, self.formation_database['4-3-3'])
        
        # Tactical advantage calculation
        home_advantages = 0
        away_advantages = 0
        key_battles = []
        
        # Check formation strengths vs weaknesses
        if away_formation in home_data.get('strong_against', []):
            home_advantages += 1
            key_battles.append(f"{home_formation} tactically favored vs {away_formation}")
        
        if home_formation in away_data.get('strong_against', []):
            away_advantages += 1
            key_battles.append(f"{away_formation} tactically favored vs {home_formation}")
        
        # Determine overall advantage
        if home_advantages > away_advantages:
            tactical_advantage = 'home'
        elif away_advantages > home_advantages:
            tactical_advantage = 'away'
        else:
            tactical_advantage = 'neutral'
        
        # Predict playing style
        combined_attacking = (home_data['attacking_width'] + away_data['attacking_width']) / 2
        combined_defensive = (home_data['defensive_solidity'] + away_data['defensive_solidity']) / 2
        
        if combined_attacking > 0.7:
            predicted_style = 'open_attacking'
        elif combined_defensive > 0.8:
            predicted_style = 'tactical_defensive'
        else:
            predicted_style = 'balanced'
        
        # Control probability
        midfield_battle = abs(home_data['midfield_control'] - away_data['midfield_control'])
        control_probability = 0.5 + (midfield_battle * 0.3)
        
        # Add key tactical battles
        if not key_battles:
            key_battles = [
                f"Midfield battle: {home_formation} midfield vs {away_formation} midfield",
                f"Width vs solidity: {home_data['attacking_width']:.1f} vs {away_data['defensive_solidity']:.1f}"
            ]
        
        return FormationAnalysis(
            home_formation=home_formation,
            away_formation=away_formation,
            tactical_advantage=tactical_advantage,
            key_battles=key_battles,
            predicted_style=predicted_style,
            control_probability=round(control_probability, 3)
        )
    
    def get_market_sentiment(self, home_team: str, away_team: str) -> MarketSentiment:
        """Analyze betting market sentiment (simulated realistic data)"""
        
        # Simulate realistic odds based on team strength
        team_strengths = {
            'FC Barcelona': 0.90, 'Real Madrid CF': 0.92, 'Atlético Madrid': 0.78,
            'Sevilla FC': 0.75, 'Villarreal CF': 0.78, 'Real Betis Balompié': 0.70,
            'Athletic Bilbao': 0.72, 'Real Sociedad': 0.76, 'Valencia CF': 0.68,
            'RCD Mallorca': 0.60, 'Girona FC': 0.65, 'RCD Espanyol de Barcelona': 0.58,
            'Real Oviedo': 0.60
        }
        
        home_strength = team_strengths.get(home_team, 0.65)
        away_strength = team_strengths.get(away_team, 0.65)
        
        # Calculate implied probabilities with home advantage
        home_prob = (home_strength / (home_strength + away_strength)) * 0.45 + 0.15  # Home advantage
        away_prob = (away_strength / (home_strength + away_strength)) * 0.45 + 0.10
        draw_prob = 1.0 - home_prob - away_prob
        
        # Convert to odds (with bookmaker margin)
        margin = 1.08  # 8% bookmaker margin
        home_odds = round((1 / home_prob) * margin, 2)
        draw_odds = round((1 / draw_prob) * margin, 2)
        away_odds = round((1 / away_prob) * margin, 2)
        
        # Market confidence (inverse of variance in odds)
        strength_diff = abs(home_strength - away_strength)
        market_confidence = min(0.9, 0.5 + strength_diff)
        
        # Public sentiment
        if home_odds < 1.8:
            public_sentiment = 'bullish_home'
        elif away_odds < 2.2:
            public_sentiment = 'bullish_away'
        else:
            public_sentiment = 'neutral'
        
        # Sharp money indicator (how much the odds have moved)
        sharp_money = np.random.uniform(-0.2, 0.2)  # Simulate market movement
        
        return MarketSentiment(
            home_odds=home_odds,
            draw_odds=draw_odds,
            away_odds=away_odds,
            market_confidence=round(market_confidence, 3),
            public_sentiment=public_sentiment,
            sharp_money_indicator=round(sharp_money, 3)
        )
    
    def generate_comprehensive_analytics(self, home_team: str, away_team: str,
                                       home_formation: str = '4-3-3',
                                       away_formation: str = '4-2-3-1') -> Dict:
        """Generate complete advanced analytics package"""
        
        print(f"🔬 Generating advanced analytics for {home_team} vs {away_team}...")
        
        # Expected Threat analysis
        xt_analysis = self.calculate_expected_threat_advantage(
            home_team, away_team, home_formation, away_formation
        )
        
        # Formation analysis
        formation_analysis = self.analyze_formation_matchup(home_formation, away_formation)
        
        # Market sentiment
        market_analysis = self.get_market_sentiment(home_team, away_team)
        
        # Pressing battle analysis
        home_pressing = self.pressing_profiles.get(home_team, PressingMetrics(home_team, 0.6, 0.5, 0.6, 0.7))
        away_pressing = self.pressing_profiles.get(away_team, PressingMetrics(away_team, 0.6, 0.5, 0.6, 0.7))
        
        pressing_battle = self._analyze_pressing_battle(home_pressing, away_pressing)
        
        # Generate key insights
        key_insights = self._generate_tactical_insights(
            xt_analysis, formation_analysis, pressing_battle, market_analysis
        )
        
        return {
            'expected_threat_analysis': xt_analysis,
            'formation_matchup': {
                'home_formation': formation_analysis.home_formation,
                'away_formation': formation_analysis.away_formation,
                'tactical_advantage': formation_analysis.tactical_advantage,
                'key_battles': formation_analysis.key_battles,
                'predicted_style': formation_analysis.predicted_style,
                'control_probability': formation_analysis.control_probability
            },
            'pressing_intensity_battle': pressing_battle,
            'market_sentiment': {
                'home_odds': market_analysis.home_odds,
                'draw_odds': market_analysis.draw_odds,
                'away_odds': market_analysis.away_odds,
                'market_confidence': market_analysis.market_confidence,
                'public_sentiment': market_analysis.public_sentiment,
                'sharp_money_movement': market_analysis.sharp_money_indicator
            },
            'tactical_insights': key_insights,
            'analytics_confidence': self._calculate_analytics_confidence(
                xt_analysis, formation_analysis, market_analysis
            )
        }
    
    def _analyze_pressing_battle(self, home_pressing: PressingMetrics, 
                               away_pressing: PressingMetrics) -> Dict:
        """Analyze the pressing battle between teams"""
        
        # Pressing vs press resistance matchup
        home_press_success = home_pressing.pressing_intensity * (1 - away_pressing.press_resistance)
        away_press_success = away_pressing.pressing_intensity * (1 - home_pressing.press_resistance)
        
        # Transition opportunities
        home_transition_prob = home_pressing.counter_press_efficiency * away_press_success
        away_transition_prob = away_pressing.counter_press_efficiency * home_press_success
        
        return {
            'home_pressing_intensity': home_pressing.pressing_intensity,
            'away_pressing_intensity': away_pressing.pressing_intensity,
            'home_press_success_rate': round(home_press_success, 3),
            'away_press_success_rate': round(away_press_success, 3),
            'home_transition_opportunities': round(home_transition_prob, 3),
            'away_transition_opportunities': round(away_transition_prob, 3),
            'pressing_advantage': 'home' if home_press_success > away_press_success else 'away',
            'transition_advantage': 'home' if home_transition_prob > away_transition_prob else 'away'
        }
    
    def _generate_tactical_insights(self, xt_analysis: Dict, formation_analysis: FormationAnalysis,
                                  pressing_battle: Dict, market_analysis: MarketSentiment) -> List[str]:
        """Generate key tactical insights from all analyses"""
        
        insights = []
        
        # xT insights
        if xt_analysis['xt_differential'] > 0.1:
            dominant = xt_analysis['dominant_team']
            insights.append(f"Expected Threat model favors {dominant} team significantly (Δ{xt_analysis['xt_differential']:.3f})")
        
        # Formation insights
        if formation_analysis.tactical_advantage != 'neutral':
            insights.append(f"Formation advantage: {formation_analysis.tactical_advantage} team ({formation_analysis.home_formation} vs {formation_analysis.away_formation})")
        
        # Pressing insights
        press_adv = pressing_battle['pressing_advantage']
        trans_adv = pressing_battle['transition_advantage']
        if press_adv == trans_adv:
            insights.append(f"Complete pressing dominance expected from {press_adv} team")
        else:
            insights.append(f"Complex pressing battle: {press_adv} team wins pressure, {trans_adv} team wins transitions")
        
        # Market insights
        if market_analysis.market_confidence > 0.8:
            insights.append(f"Market shows high confidence (confidence: {market_analysis.market_confidence:.1%})")
        
        if abs(market_analysis.sharp_money_indicator) > 0.1:
            direction = "towards home" if market_analysis.sharp_money_indicator > 0 else "towards away"
            insights.append(f"Sharp money movement detected {direction}")
        
        # Style prediction
        if formation_analysis.predicted_style == 'open_attacking':
            insights.append("High-scoring match expected from tactical setup")
        elif formation_analysis.predicted_style == 'tactical_defensive':
            insights.append("Low-scoring tactical battle anticipated")
        
        return insights
    
    def _calculate_analytics_confidence(self, xt_analysis: Dict, formation_analysis: FormationAnalysis,
                                      market_analysis: MarketSentiment) -> float:
        """Calculate confidence in analytics predictions"""
        
        confidence_factors = []
        
        # xT model confidence
        if xt_analysis['xt_differential'] > 0.05:
            confidence_factors.append(0.3)
        else:
            confidence_factors.append(0.15)
        
        # Formation analysis confidence
        if formation_analysis.tactical_advantage != 'neutral':
            confidence_factors.append(0.25)
        else:
            confidence_factors.append(0.15)
        
        # Market confidence
        confidence_factors.append(market_analysis.market_confidence * 0.2)
        
        # Base analytics confidence
        confidence_factors.append(0.25)
        
        return round(sum(confidence_factors), 3)

def main():
    """Test advanced analytics engine"""
    engine = AdvancedAnalyticsEngine()
    
    # Test comprehensive analytics
    analytics = engine.generate_comprehensive_analytics(
        'FC Barcelona', 'Girona FC', '4-3-3', '4-2-3-1'
    )
    
    print("🔬 Advanced Analytics Complete!")
    print(json.dumps(analytics, indent=2))

if __name__ == "__main__":
    main()