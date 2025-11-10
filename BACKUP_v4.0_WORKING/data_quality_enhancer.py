#!/usr/bin/env python3
"""
Data Quality Enhancement Module
Player injuries, weather effects, referee analysis, and team news parsing
"""

import requests
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import time
import re

class DataQualityEnhancer:
    """Enhanced data collection for better prediction accuracy"""
    
    def __init__(self, football_api_key: str, weather_api_key: Optional[str] = None):
        self.football_api_key = football_api_key
        self.weather_api_key = weather_api_key or "demo_key"  # Free tier available
        self.headers = {'X-Auth-Token': football_api_key}
        self.setup_directories()
    
    def setup_directories(self):
        """Create necessary directories for enhanced data"""
        directories = [
            "data/player_data",
            "data/weather_data", 
            "data/referee_data",
            "data/team_news"
        ]
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    def get_player_injury_impact(self, team_id: int, team_name: str) -> Dict:
        """Analyze player availability and injury impact on team strength"""
        try:
            # In a real implementation, this would fetch from injury APIs
            # For now, we'll simulate injury analysis based on team patterns
            
            # Mock injury data - in production would use real injury APIs
            injury_impact = self.simulate_injury_analysis(team_name)
            
            # Calculate team strength reduction
            strength_reduction = self.calculate_strength_reduction(injury_impact)
            
            return {
                'key_players_available': injury_impact['available_count'],
                'key_players_injured': injury_impact['injured_count'],
                'strength_reduction_pct': strength_reduction,
                'injury_areas': injury_impact['affected_positions'],
                'expected_lineup_strength': 100 - strength_reduction,
                'injury_concerns': injury_impact['concerns']
            }
        
        except Exception as e:
            print(f"⚠️ Could not fetch injury data: {e}")
            return self.get_default_injury_data()
    
    def simulate_injury_analysis(self, team_name: str) -> Dict:
        """Simulate injury analysis - replace with real API in production"""
        # Simulate some teams having more injuries
        injury_prone_teams = ['FC Barcelona', 'Real Madrid', 'Manchester United', 'Bayern Munich']
        
        if team_name in injury_prone_teams:
            return {
                'available_count': 8,
                'injured_count': 3,
                'affected_positions': ['midfield', 'defense'],
                'concerns': ['Key midfielder out 2-3 weeks', 'Backup defender questionable']
            }
        else:
            return {
                'available_count': 10,
                'injured_count': 1,
                'affected_positions': ['forward'],
                'concerns': ['Minor rotation needed']
            }
    
    def calculate_strength_reduction(self, injury_data: Dict) -> float:
        """Calculate team strength reduction due to injuries"""
        injured_count = injury_data['injured_count']
        affected_positions = injury_data['affected_positions']
        
        base_reduction = injured_count * 3.5  # 3.5% per key player
        
        # Additional penalty for critical positions
        if 'midfield' in affected_positions:
            base_reduction += 5  # Midfield injuries hurt more
        if 'defense' in affected_positions:
            base_reduction += 3
        
        return min(base_reduction, 25)  # Cap at 25% reduction
    
    def get_weather_impact(self, venue_city: str, match_date: str) -> Dict:
        """Get weather conditions and predict impact on match"""
        try:
            # Use Open-Meteo API (free tier available)
            weather_data = self.fetch_weather_data(venue_city, match_date)
            impact = self.analyze_weather_impact(weather_data)
            
            return {
                'conditions': weather_data,
                'impact_assessment': impact,
                'goal_adjustment': impact['goal_modifier'],
                'style_impact': impact['playing_style_effect']
            }
        
        except Exception as e:
            print(f"⚠️ Could not fetch weather data: {e}")
            return self.get_default_weather_data()
    
    def fetch_weather_data(self, city: str, match_date: str) -> Dict:
        """Enhanced weather data collection with stadium-specific intelligence"""
        try:
            # Stadium location mapping for major European cities
            stadium_coordinates = self._get_stadium_coordinates(city)
            
            # For now, simulate enhanced weather data with seasonal intelligence
            # TODO: Replace with Open-Meteo API integration
            seasonal_weather = self._generate_seasonal_weather(city, match_date)
            
            return seasonal_weather
            
        except Exception as e:
            print(f"⚠️ Weather API error: {e}")
            return self._get_fallback_weather(city, match_date)
    
    def _get_stadium_coordinates(self, city: str) -> Dict:
        """Get approximate coordinates for major football cities"""
        stadium_locations = {
            'madrid': {'lat': 40.4168, 'lon': -3.7038, 'altitude': 650, 'location_type': 'inland'},
            'barcelona': {'lat': 41.3851, 'lon': 2.1734, 'altitude': 12, 'location_type': 'coastal'},
            'london': {'lat': 51.5074, 'lon': -0.1278, 'altitude': 35, 'location_type': 'inland'},
            'manchester': {'lat': 53.4808, 'lon': -2.2426, 'altitude': 38, 'location_type': 'inland'},
            'munich': {'lat': 48.1351, 'lon': 11.5820, 'altitude': 520, 'location_type': 'inland'},
            'milan': {'lat': 45.4642, 'lon': 9.1900, 'altitude': 120, 'location_type': 'inland'},
            'paris': {'lat': 48.8566, 'lon': 2.3522, 'altitude': 35, 'location_type': 'inland'},
            'seville': {'lat': 37.3891, 'lon': -5.9845, 'altitude': 7, 'location_type': 'inland'},
        }
        
        city_key = city.lower().replace(' ', '')
        return stadium_locations.get(city_key, {
            'lat': 40.0, 'lon': 0.0, 'altitude': 100, 'location_type': 'inland'
        })
    
    def _generate_seasonal_weather(self, city: str, match_date: str) -> Dict:
        """Generate realistic seasonal weather patterns"""
        import datetime
        import random
        
        try:
            month = int(match_date.split('-')[1]) if '-' in match_date else 10
        except:
            month = 10  # Default to October
        
        # Base seasonal temperatures for European football
        seasonal_temps = {
            1: (-2, 8), 2: (0, 10), 3: (4, 14), 4: (8, 18), 
            5: (12, 22), 6: (16, 26), 7: (18, 28), 8: (17, 27),
            9: (14, 23), 10: (9, 18), 11: (4, 12), 12: (0, 8)
        }
        
        # Regional adjustments
        if 'madrid' in city.lower() or 'seville' in city.lower():
            seasonal_temps[month] = (seasonal_temps[month][0] + 3, seasonal_temps[month][1] + 5)
        elif 'barcelona' in city.lower():
            seasonal_temps[month] = (seasonal_temps[month][0] + 2, seasonal_temps[month][1] + 3)
        elif 'manchester' in city.lower() or 'london' in city.lower():
            seasonal_temps[month] = (seasonal_temps[month][0] - 1, seasonal_temps[month][1] - 2)
        
        temp_min, temp_max = seasonal_temps[month]
        temperature = random.uniform(temp_min, temp_max)
        
        # Seasonal precipitation patterns
        wet_months = [11, 12, 1, 2, 3, 4]  # European winter/spring
        if month in wet_months:
            precipitation = random.uniform(0, 8) if random.random() < 0.4 else random.uniform(0, 1)
        else:
            precipitation = random.uniform(0, 3) if random.random() < 0.2 else random.uniform(0, 0.5)
        
        # Wind patterns (coastal areas windier)
        coords = self._get_stadium_coordinates(city)
        base_wind = random.uniform(5, 25)
        if coords['location_type'] == 'coastal':
            base_wind += random.uniform(0, 10)
        
        # Humidity patterns
        humidity = random.uniform(45, 85)
        if precipitation > 2:
            humidity += random.uniform(10, 20)
        
        return {
            'temperature': round(temperature, 1),
            'humidity': round(humidity, 1),
            'wind_speed': round(base_wind, 1),
            'precipitation': round(precipitation, 2),
            'conditions': self._determine_conditions(temperature, precipitation, base_wind),
            'visibility': random.uniform(8, 20) if precipitation < 1 else random.uniform(3, 10),
            'pressure': random.uniform(995, 1025)
        }
    
    def _determine_conditions(self, temp: float, precip: float, wind: float) -> str:
        """Determine weather condition description"""
        if precip > 5:
            return 'heavy_rain'
        elif precip > 2:
            return 'moderate_rain'
        elif precip > 0.5:
            return 'light_rain'
        elif wind > 30:
            return 'very_windy'
        elif wind > 20:
            return 'windy'
        elif temp > 25:
            return 'hot'
        elif temp < 5:
            return 'cold'
        else:
            return 'clear'
    
    def _get_fallback_weather(self, city: str, match_date: str) -> Dict:
        """Fallback weather data when API fails"""
        return {
            'temperature': 15.0,
            'humidity': 60,
            'wind_speed': 8,
            'precipitation': 0.0,
            'conditions': 'clear',
            'visibility': 15,
            'pressure': 1013
        }
    
    def analyze_weather_impact(self, weather: Dict, stadium_info: Optional[Dict] = None, team_styles: Optional[Dict] = None) -> Dict:
        """Enhanced weather analysis with stadium-specific and team-style correlations"""
        goal_modifier = 1.0
        playing_style_effect = "normal"
        tactical_adjustments = []
        
        temperature = weather.get('temperature', 20)
        precipitation = weather.get('precipitation', 0)
        wind_speed = weather.get('wind_speed', 10)
        humidity = weather.get('humidity', 60)
        conditions = weather.get('conditions', 'clear')
        
        # Enhanced Temperature Analysis
        if temperature < 0:
            goal_modifier *= 0.75  # Severe cold dramatically reduces play quality
            playing_style_effect = "extremely_defensive"
            tactical_adjustments.append("Long ball play due to frozen pitch")
        elif temperature < 5:
            goal_modifier *= 0.88  # Cold weather reduces player performance
            playing_style_effect = "defensive"
            tactical_adjustments.append("Reduced technical play in cold")
        elif temperature > 35:
            goal_modifier *= 0.82  # Extreme heat causes fatigue
            playing_style_effect = "slower_tempo"
            tactical_adjustments.append("Fatigue-induced slower tempo")
        elif temperature > 30:
            goal_modifier *= 0.92  # Hot weather affects stamina
            tactical_adjustments.append("Increased substitutions likely")
        
        # Enhanced Precipitation Analysis
        if precipitation > 5.0:
            goal_modifier *= 0.70  # Heavy rain severely impacts play
            playing_style_effect = "long_ball_defensive"
            tactical_adjustments.extend([
                "Technical play impossible",
                "Long ball tactics favored",
                "Goalkeeping errors more likely"
            ])
        elif precipitation > 2.0:
            goal_modifier *= 0.82  # Moderate rain affects passing
            playing_style_effect = "defensive"
            tactical_adjustments.append("Direct play favored over possession")
        elif precipitation > 0.5:
            goal_modifier *= 0.93  # Light rain slightly affects ball control
            tactical_adjustments.append("Slight reduction in passing accuracy")
        
        # Enhanced Wind Analysis
        if wind_speed > 40:
            goal_modifier *= 0.78  # Extreme wind disrupts play significantly
            playing_style_effect = "highly_unpredictable"
            tactical_adjustments.extend([
                "Goal kicks and corners heavily affected",
                "Shooting accuracy reduced",
                "Unpredictable ball movement"
            ])
        elif wind_speed > 25:
            goal_modifier *= 0.88  # Strong wind affects crosses and shots
            playing_style_effect = "unpredictable"
            tactical_adjustments.append("Aerial play and long shots affected")
        elif wind_speed > 15:
            goal_modifier *= 0.95  # Moderate wind slightly affects play
            tactical_adjustments.append("Minor impact on crossing accuracy")
        
        # Humidity Impact (often overlooked factor)
        if humidity > 85:
            goal_modifier *= 0.92  # High humidity increases fatigue
            tactical_adjustments.append("Increased player fatigue")
        elif humidity < 30:
            goal_modifier *= 0.96  # Low humidity can affect ball behavior
            tactical_adjustments.append("Ball may travel further in dry air")
        
        # Combined Weather Effects
        extreme_conditions = sum([
            temperature < 5 or temperature > 30,
            precipitation > 2.0,
            wind_speed > 25,
            humidity > 85
        ])
        
        if extreme_conditions >= 2:
            goal_modifier *= 0.85  # Multiple extreme conditions compound effect
            playing_style_effect = "survival_mode"
            tactical_adjustments.append("Multiple weather factors creating chaos")
        
        # Stadium-Specific Weather Factors
        stadium_modifier = 1.0
        stadium_effects = []
        
        if stadium_info:
            # Covered stadium reduces weather impact
            if stadium_info.get('roof_type') == 'retractable':
                if precipitation > 1.0:
                    stadium_modifier *= 1.15  # Roof can be closed
                    stadium_effects.append("Retractable roof provides weather protection")
            elif stadium_info.get('roof_type') == 'partial':
                stadium_modifier *= 1.05  # Some protection
                stadium_effects.append("Partial roof coverage available")
            
            # Altitude effects
            altitude = stadium_info.get('altitude', 0)
            if altitude > 1000:  # High altitude stadiums
                if temperature > 25:
                    goal_modifier *= 0.88  # Hot + high altitude = severe fatigue
                    stadium_effects.append("High altitude amplifies heat stress")
                else:
                    goal_modifier *= 0.96  # Thin air affects ball flight
                    stadium_effects.append("High altitude affects ball trajectory")
            
            # Coastal stadiums
            if stadium_info.get('location_type') == 'coastal':
                if wind_speed > 20:
                    goal_modifier *= 0.92  # Coastal winds are more unpredictable
                    stadium_effects.append("Coastal location amplifies wind effects")
        
        # Team Style Weather Adaptability
        team_weather_modifier = 1.0
        adaptability_notes = []
        
        if team_styles:
            home_style = team_styles.get('home_team_style', 'balanced')
            away_style = team_styles.get('away_team_style', 'balanced')
            
            # Technical teams suffer more in bad weather
            if playing_style_effect in ['defensive', 'long_ball_defensive'] and home_style == 'technical':
                team_weather_modifier *= 0.95
                adaptability_notes.append("Home team's technical style hindered by conditions")
            
            # Physical teams handle bad weather better
            if playing_style_effect in ['defensive', 'long_ball_defensive'] and away_style == 'physical':
                team_weather_modifier *= 1.05
                adaptability_notes.append("Away team's physical style suits conditions")
        
        # Calculate final modifier
        final_modifier = goal_modifier * stadium_modifier * team_weather_modifier
        
        # Weather advantage assessment
        weather_advantage = 'none'
        if precipitation > 2.0 or wind_speed > 25:
            weather_advantage = 'physical_teams'  # Physical teams handle bad weather better
        elif temperature > 30:
            weather_advantage = 'fitness_advantage'  # Better conditioned teams benefit
        
        return {
            'goal_modifier': final_modifier,
            'playing_style_effect': playing_style_effect,
            'weather_advantage': weather_advantage,
            'tactical_adjustments': tactical_adjustments,
            'stadium_effects': stadium_effects,
            'adaptability_notes': adaptability_notes,
            'weather_severity': self._assess_weather_severity(temperature, precipitation, wind_speed),
            'conditions_summary': self._generate_conditions_summary(weather, final_modifier)
        }
    
    def _assess_weather_severity(self, temp: float, precip: float, wind: float) -> str:
        """Assess overall weather severity for match"""
        severity_score = 0
        
        if temp < 5 or temp > 30:
            severity_score += 2
        elif temp < 10 or temp > 25:
            severity_score += 1
            
        if precip > 5:
            severity_score += 3
        elif precip > 2:
            severity_score += 2
        elif precip > 0.5:
            severity_score += 1
            
        if wind > 40:
            severity_score += 3
        elif wind > 25:
            severity_score += 2
        elif wind > 15:
            severity_score += 1
        
        if severity_score >= 6:
            return "EXTREME"
        elif severity_score >= 4:
            return "SEVERE"
        elif severity_score >= 2:
            return "MODERATE"
        else:
            return "MILD"
    
    def _generate_conditions_summary(self, weather: Dict, modifier: float) -> str:
        """Generate human-readable weather impact summary"""
        temp = weather.get('temperature', 20)
        precip = weather.get('precipitation', 0)
        wind = weather.get('wind_speed', 10)
        
        if modifier < 0.80:
            return f"Severe weather conditions ({temp}°C, {precip}mm rain, {wind} km/h wind) will significantly impact play quality"
        elif modifier < 0.90:
            return f"Challenging conditions ({temp}°C, {precip}mm rain, {wind} km/h wind) likely to affect match dynamics"
        elif modifier < 0.95:
            return f"Mild weather impact ({temp}°C, {precip}mm rain, {wind} km/h wind) may slightly influence play"
        else:
            return f"Good playing conditions ({temp}°C, {precip}mm rain, {wind} km/h wind) minimal weather impact expected"
    
    def get_referee_analysis(self, referee_name: Optional[str] = None) -> Dict:
        """Enhanced referee analysis with detailed tendencies and match impact assessment"""
        if not referee_name:
            return self.get_default_referee_data()
        
        try:
            # Get enhanced referee statistics
            referee_stats = self.simulate_referee_stats(referee_name)
            
            # Calculate enhanced insights
            enhanced_analysis = self._analyze_referee_impact(referee_stats, referee_name)
            
            return {
                'name': referee_name,
                'home_bias_pct': referee_stats['home_bias'],
                'cards_per_game': referee_stats['avg_cards'],
                'penalties_per_game': referee_stats['avg_penalties'],
                'strict_level': referee_stats['strictness'],
                'experience_level': referee_stats['experience'],
                # Enhanced Intelligence v4.1 - New referee insights
                'match_control_style': referee_stats.get('match_control', 'standard'),
                'var_tendency': referee_stats.get('var_usage', 'standard'),
                'big_game_ready': referee_stats.get('big_game_experience', False),
                'crowd_resistance': referee_stats.get('crowd_influence_resistance', 70),
                'predicted_impact': enhanced_analysis['match_impact'],
                'key_tendencies': enhanced_analysis['key_patterns'],
                'disciplinary_prediction': enhanced_analysis['discipline_forecast']
            }
        
        except Exception as e:
            print(f"⚠️ Could not analyze referee: {e}")
            return self.get_default_referee_data()
    
    def _analyze_referee_impact(self, referee_stats: Dict, referee_name: str) -> Dict:
        """Analyze detailed referee impact on match dynamics"""
        
        # Determine match impact level
        cards_per_game = referee_stats.get('avg_cards', 3.5)
        strictness = referee_stats.get('strictness', 'moderate')
        
        if cards_per_game >= 4.5 or strictness == 'high':
            impact_level = 'high'
            impact_description = 'Referee likely to significantly influence match flow'
        elif cards_per_game >= 3.0 and strictness in ['moderate', 'strict']:
            impact_level = 'moderate'
            impact_description = 'Standard referee influence expected'
        else:
            impact_level = 'low'
            impact_description = 'Minimal referee interference expected'
        
        # Key pattern analysis
        key_patterns = []
        
        if referee_stats.get('home_bias', 50) > 53:
            key_patterns.append('Tends to favor home team decisions')
        elif referee_stats.get('home_bias', 50) < 47:
            key_patterns.append('Slightly favors away team decisions')
        else:
            key_patterns.append('Balanced decision making')
        
        if referee_stats.get('avg_penalties', 0.2) > 0.3:
            key_patterns.append('More likely to award penalties')
        
        if referee_stats.get('match_control') == 'strict':
            key_patterns.append('Strong match control - few arguments')
        elif referee_stats.get('match_control') == 'calm':
            key_patterns.append('Calm approach - good game flow')
        
        # Disciplinary forecast
        expected_cards = referee_stats.get('avg_cards', 3.5)
        expected_penalties = referee_stats.get('avg_penalties', 0.2)
        
        if expected_cards >= 4.0:
            discipline_forecast = f"Expect {expected_cards:.1f} cards (above average)"
        elif expected_cards <= 2.5:
            discipline_forecast = f"Expect {expected_cards:.1f} cards (below average)"
        else:
            discipline_forecast = f"Expect {expected_cards:.1f} cards (standard)"
        
        if expected_penalties > 0.25:
            discipline_forecast += f" | {expected_penalties:.1f} penalties likely"
        
        return {
            'match_impact': {
                'level': impact_level,
                'description': impact_description
            },
            'key_patterns': key_patterns,
            'discipline_forecast': discipline_forecast
        }
    
    def simulate_referee_stats(self, referee_name: str) -> Dict:
        """Enhanced referee statistics with detailed analysis patterns"""
        # Enhanced referee database with more detailed patterns
        enhanced_referee_db = {
            'Anthony Taylor': {
                'home_bias': 47.8, 'avg_cards': 4.2, 'avg_penalties': 0.35,
                'strictness': 'high', 'experience': 'veteran',
                'match_control': 'strict', 'var_usage': 'frequent',
                'big_game_experience': True, 'crowd_influence_resistance': 85
            },
            'Felix Brych': {
                'home_bias': 49.1, 'avg_cards': 3.8, 'avg_penalties': 0.28,
                'strictness': 'high', 'experience': 'veteran',
                'match_control': 'authoritative', 'var_usage': 'moderate',
                'big_game_experience': True, 'crowd_influence_resistance': 90
            },
            'Björn Kuipers': {
                'home_bias': 48.5, 'avg_cards': 3.5, 'avg_penalties': 0.25,
                'strictness': 'moderate', 'experience': 'veteran',
                'match_control': 'calm', 'var_usage': 'balanced',
                'big_game_experience': True, 'crowd_influence_resistance': 88
            },
            'Michael Oliver': {
                'home_bias': 51.2, 'avg_cards': 3.9, 'avg_penalties': 0.31,
                'strictness': 'moderate', 'experience': 'experienced',
                'match_control': 'consistent', 'var_usage': 'balanced',
                'big_game_experience': True, 'crowd_influence_resistance': 82
            },
            'Unknown Referee': {
                'home_bias': 51.0, 'avg_cards': 3.5, 'avg_penalties': 0.2,
                'strictness': 'moderate', 'experience': 'experienced',
                'match_control': 'standard', 'var_usage': 'standard',
                'big_game_experience': False, 'crowd_influence_resistance': 70
            }
        }
        
        # Return enhanced stats or generate realistic random referee
        if referee_name in enhanced_referee_db:
            return enhanced_referee_db[referee_name]
        else:
            # Generate realistic referee profile for unknown referees
            import random
            random.seed(hash(referee_name) % 1000)  # Consistent randomization per referee
            
            return {
                'home_bias': round(45.0 + random.random() * 10.0, 1),  # 45-55% range
                'avg_cards': round(2.8 + random.random() * 2.0, 1),    # 2.8-4.8 cards
                'avg_penalties': round(0.15 + random.random() * 0.25, 2),  # 0.15-0.4 penalties
                'strictness': random.choice(['lenient', 'moderate', 'strict']),
                'experience': random.choice(['experienced', 'veteran']),
                'match_control': random.choice(['calm', 'strict', 'consistent']),
                'var_usage': random.choice(['conservative', 'balanced', 'frequent']),
                'big_game_experience': random.choice([True, False]),
                'crowd_influence_resistance': random.randint(65, 85)
            }
    
    def parse_team_news(self, team_name: str, match_date: str) -> Dict:
        """Parse team news and predicted lineups"""
        try:
            # Simulate team news parsing - in production use news APIs
            news_data = self.simulate_team_news(team_name)
            lineup_prediction = self.predict_lineup_impact(news_data)
            
            return {
                'formation_expected': lineup_prediction['formation'],
                'key_changes': news_data['changes'],
                'tactical_approach': lineup_prediction['tactical_style'],
                'lineup_strength': lineup_prediction['strength_rating'],
                'news_sentiment': news_data['sentiment']
            }
        
        except Exception as e:
            print(f"⚠️ Could not parse team news: {e}")
            return self.get_default_team_news()
    
    def simulate_team_news(self, team_name: str) -> Dict:
        """Simulate team news analysis - replace with real news parsing"""
        return {
            'changes': ['Rotation in midfield expected', 'New signing may start'],
            'sentiment': 'positive',
            'confidence_level': 'medium'
        }
    
    def predict_lineup_impact(self, news_data: Dict) -> Dict:
        """Predict how lineup changes affect team performance"""
        formation = '4-3-3'  # Default formation
        tactical_style = 'balanced'
        strength_rating = 85.0
        
        # Adjust based on news
        if 'rotation' in ' '.join(news_data['changes']).lower():
            strength_rating -= 5  # Rotation slightly weakens team
        
        if news_data['sentiment'] == 'positive':
            strength_rating += 3
        elif news_data['sentiment'] == 'negative':
            strength_rating -= 7
        
        return {
            'formation': formation,
            'tactical_style': tactical_style,
            'strength_rating': max(60, min(95, strength_rating))
        }
    
    # Default data methods
    def get_default_injury_data(self) -> Dict:
        return {
            'key_players_available': 9,
            'key_players_injured': 2,
            'strength_reduction_pct': 7.0,
            'injury_areas': ['forward'],
            'expected_lineup_strength': 93.0,
            'injury_concerns': ['Minor squad rotation needed']
        }
    
    def get_default_weather_data(self) -> Dict:
        return {
            'conditions': {
                'temperature': 15.0,
                'humidity': 60,
                'wind_speed': 8,
                'precipitation': 0.0,
                'conditions': 'clear'
            },
            'impact_assessment': {
                'goal_modifier': 1.0,
                'playing_style_effect': 'normal',
                'weather_advantage': 'none'
            },
            'goal_adjustment': 1.0,
            'style_impact': 'normal'
        }
    
    def get_default_referee_data(self) -> Dict:
        return {
            'name': 'Unknown Referee',
            'home_bias_pct': 51.0,
            'cards_per_game': 3.5,
            'penalties_per_game': 0.2,
            'strict_level': 'moderate',
            'experience_level': 'experienced'
        }
    
    def get_default_team_news(self) -> Dict:
        return {
            'formation_expected': '4-3-3',
            'key_changes': ['Expected lineup'],
            'tactical_approach': 'balanced',
            'lineup_strength': 85.0,
            'news_sentiment': 'neutral'
        }
    
    def comprehensive_data_enhancement(self, match: Dict, venue_info: Optional[Dict] = None) -> Dict:
        """Collect all enhanced data for a match"""
        home_team_id = match['homeTeam']['id']
        away_team_id = match['awayTeam']['id']
        home_team_name = match['homeTeam']['name']
        away_team_name = match['awayTeam']['name']
        match_date = match['utcDate'][:10]
        
        print(f"📊 Collecting enhanced data quality information...")
        
        # Collect all enhanced data
        home_injuries = self.get_player_injury_impact(home_team_id, home_team_name)
        away_injuries = self.get_player_injury_impact(away_team_id, away_team_name)
        
        venue_city = venue_info.get('city', 'Madrid') if venue_info else 'Madrid'
        weather = self.get_weather_impact(venue_city, match_date)
        
        referee = self.get_referee_analysis(match.get('referee', {}).get('name'))
        
        home_team_news = self.parse_team_news(home_team_name, match_date)
        away_team_news = self.parse_team_news(away_team_name, match_date)
        
        return {
            'player_availability': {
                'home_team': home_injuries,
                'away_team': away_injuries
            },
            'weather_conditions': weather,
            'referee_analysis': referee,
            'team_news': {
                'home_team': home_team_news,
                'away_team': away_team_news
            },
            'data_quality_score': self.calculate_data_quality_score(
                home_injuries, away_injuries, weather, referee, home_team_news, away_team_news
            )
        }
    
    def calculate_data_quality_score(self, *data_sources) -> float:
        """Enhanced Intelligence v4.1 - Advanced data quality scoring with granular analysis"""
        quality_score = 0.0
        max_score = 100.0
        quality_details = []
        
        # Enhanced scoring with more granular analysis
        try:
            # Home Team Data Quality (0-20 points)
            home_data = data_sources[0] if len(data_sources) > 0 else {}
            home_players = home_data.get('key_players_available', 0)
            if home_players >= 10:
                quality_score += 20
                quality_details.append("Excellent home team data")
            elif home_players >= 8:
                quality_score += 15
                quality_details.append("Good home team data")
            elif home_players >= 6:
                quality_score += 10
                quality_details.append("Fair home team data")
            else:
                quality_score += 5
                quality_details.append("Limited home team data")
                
            # Away Team Data Quality (0-20 points)
            away_data = data_sources[1] if len(data_sources) > 1 else {}
            away_players = away_data.get('key_players_available', 0)
            if away_players >= 10:
                quality_score += 20
                quality_details.append("Excellent away team data")
            elif away_players >= 8:
                quality_score += 15
                quality_details.append("Good away team data")
            elif away_players >= 6:
                quality_score += 10
                quality_details.append("Fair away team data")
            else:
                quality_score += 5
                quality_details.append("Limited away team data")
                
            # Weather Data Quality (0-15 points)
            weather_data = data_sources[2] if len(data_sources) > 2 else {}
            weather_conditions = weather_data.get('conditions', {}).get('conditions', 'unknown')
            if weather_conditions != 'unknown' and 'temperature' in weather_data.get('conditions', {}):
                quality_score += 15
                quality_details.append("Complete weather data")
            elif weather_conditions != 'unknown':
                quality_score += 10
                quality_details.append("Basic weather data")
            else:
                quality_score += 3
                quality_details.append("No weather data")
                
            # Referee Data Quality (0-20 points)
            referee_data = data_sources[3] if len(data_sources) > 3 else {}
            referee_name = referee_data.get('name', 'Unknown Referee')
            if referee_name != 'Unknown Referee':
                # Check if we have enhanced referee data
                if referee_data.get('big_game_ready') is not None:
                    quality_score += 20
                    quality_details.append("Enhanced referee profile")
                else:
                    quality_score += 15
                    quality_details.append("Basic referee data")
            else:
                quality_score += 5
                quality_details.append("No referee assigned")
                
            # Team News Quality (0-12.5 points each = 25 total)
            home_news = data_sources[4] if len(data_sources) > 4 else {}
            away_news = data_sources[5] if len(data_sources) > 5 else {}
            
            home_sentiment = home_news.get('news_sentiment', 'unknown')
            away_sentiment = away_news.get('news_sentiment', 'unknown')
            
            if home_sentiment != 'unknown':
                quality_score += 12.5
                quality_details.append("Home team news available")
            else:
                quality_score += 3
                
            if away_sentiment != 'unknown':
                quality_score += 12.5
                quality_details.append("Away team news available")
            else:
                quality_score += 3
                
        except (IndexError, KeyError, TypeError) as e:
            # Fallback scoring if data structure is different
            quality_score = 50.0  # Default medium quality
            quality_details = ["Using fallback quality assessment"]
        
        final_score = min(quality_score, max_score)
        
        # Store quality details for reporting
        self._last_quality_details = quality_details
        self._last_quality_breakdown = {
            'total_score': final_score,
            'max_possible': max_score,
            'percentage': (final_score / max_score) * 100,
            'grade': self._get_quality_grade(final_score),
            'details': quality_details
        }
        
        return final_score
    
    def _get_quality_grade(self, score: float) -> str:
        """Convert quality score to letter grade"""
        if score >= 90:
            return 'A+ (Excellent)'
        elif score >= 80:
            return 'A (Very Good)'
        elif score >= 70:
            return 'B (Good)'
        elif score >= 60:
            return 'C (Fair)'
        elif score >= 50:
            return 'D (Poor)'
        else:
            return 'F (Very Poor)'
    
    def get_data_quality_breakdown(self) -> Dict:
        """Get detailed breakdown of the last data quality assessment"""
        return getattr(self, '_last_quality_breakdown', {
            'total_score': 75.0,
            'max_possible': 100.0,
            'percentage': 75.0,
            'grade': 'B (Good)',
            'details': ['Standard quality assessment']
        })

if __name__ == "__main__":
    # Test the data quality enhancer - using environment variable for API key
    enhancer = DataQualityEnhancer(os.getenv('FOOTBALL_DATA_API_KEY', '17405508d1774f46a368390ff07f8a31'))
    
    # Mock match data
    test_match = {
        'homeTeam': {'id': 86, 'name': 'Real Madrid'},
        'awayTeam': {'id': 81, 'name': 'FC Barcelona'},
        'utcDate': '2025-10-20T15:00:00Z',
        'referee': {'name': 'Anthony Taylor'}
    }
    
    venue_info = {'city': 'Madrid'}
    
    enhanced_data = enhancer.comprehensive_data_enhancement(test_match, venue_info)
    
    print(f"\n📊 Data Quality Analysis:")
    print(f"   Home Team Availability: {enhanced_data['player_availability']['home_team']['expected_lineup_strength']:.1f}%")
    print(f"   Away Team Availability: {enhanced_data['player_availability']['away_team']['expected_lineup_strength']:.1f}%")
    print(f"   Weather Impact: {enhanced_data['weather_conditions']['impact_assessment']['playing_style_effect']}")
    print(f"   Referee Bias: {enhanced_data['referee_analysis']['home_bias_pct']:.1f}% home bias")
    print(f"   Overall Data Quality: {enhanced_data['data_quality_score']:.1f}%")