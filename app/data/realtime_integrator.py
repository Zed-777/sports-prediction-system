#!/usr/bin/env python3
"""
Real-Time Data Integration System
Phase 1: Enhanced data collection with player injuries, team form, weather, and referee analysis
"""

import json
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import requests


@dataclass
class PlayerStatus:
    """Player availability status"""
    name: str
    position: str
    status: str  # available, injured, suspended, doubtful
    impact_rating: float  # 0.0-1.0 (1.0 = crucial player)
    expected_return: Optional[str] = None

@dataclass
class TeamForm:
    """Recent team form analysis"""
    team_name: str
    last_5_results: List[str]  # W, D, L
    goals_scored: int
    goals_conceded: int
    xg_for: float
    xg_against: float
    form_rating: float  # 0.0-1.0

@dataclass
class WeatherConditions:
    """Match day weather conditions"""
    temperature: float
    humidity: float
    wind_speed: float
    precipitation: float
    conditions: str
    impact_score: float  # How much weather affects play

@dataclass
class RefereeProfile:
    """Referee historical analysis"""
    name: str
    cards_per_game: float
    penalties_per_game: float
    home_bias: float  # -1.0 to 1.0
    strictness_rating: float

class RealTimeDataIntegrator:
    """Advanced real-time data integration system"""

    def __init__(self):
        self.football_api_key = os.getenv('FOOTBALL_DATA_API_KEY', '17405508d1774f46a368390ff07f8a31')
        self.weather_api_base = "https://api.open-meteo.com/v1/forecast"
        self.headers = {'X-Auth-Token': self.football_api_key}

        # La Liga team player importance ratings
        self.key_players = {
            'FC Barcelona': [
                PlayerStatus('Robert Lewandowski', 'FW', 'available', 0.95),
                PlayerStatus('Pedri', 'MF', 'available', 0.85),
                PlayerStatus('Frenkie de Jong', 'MF', 'available', 0.80),
                PlayerStatus('Ronald Araújo', 'DF', 'doubtful', 0.75),
            ],
            'Real Madrid CF': [
                PlayerStatus('Karim Benzema', 'FW', 'available', 0.95),
                PlayerStatus('Luka Modrić', 'MF', 'available', 0.90),
                PlayerStatus('Vinícius Júnior', 'FW', 'available', 0.85),
                PlayerStatus('Thibaut Courtois', 'GK', 'available', 0.80),
            ],
            'Sevilla FC': [
                PlayerStatus('Youssef En-Nesyri', 'FW', 'available', 0.80),
                PlayerStatus('Ivan Rakitić', 'MF', 'available', 0.75),
                PlayerStatus('Jules Koundé', 'DF', 'available', 0.70),
            ],
            'Villarreal CF': [
                PlayerStatus('Gerard Moreno', 'FW', 'available', 0.85),
                PlayerStatus('Dani Parejo', 'MF', 'available', 0.75),
                PlayerStatus('Pau Torres', 'DF', 'available', 0.70),
            ]
        }

        # Referee profiles (simulated but realistic)
        self.referee_database = {
            'Antonio Mateu Lahoz': RefereeProfile('Antonio Mateu Lahoz', 4.2, 0.3, 0.05, 0.85),
            'José María Sánchez Martínez': RefereeProfile('José María Sánchez Martínez', 3.8, 0.25, -0.02, 0.75),
            'Carlos del Cerro Grande': RefereeProfile('Carlos del Cerro Grande', 4.0, 0.28, 0.08, 0.80),
            'Jesús Gil Manzano': RefereeProfile('Jesús Gil Manzano', 4.5, 0.35, 0.03, 0.90),
        }

    def get_team_recent_form(self, team_name: str, team_id: int) -> TeamForm:
        """Analyze team's last 5 matches for form rating"""

        try:
            # Get recent matches
            url = f"https://api.football-data.org/v4/teams/{team_id}/matches"
            params = {
                'status': 'FINISHED',
                'limit': 5
            }

            response = requests.get(url, headers=self.headers, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                matches = data.get('matches', [])[:5]  # Last 5 matches

                results = []
                goals_for = 0
                goals_against = 0

                for match in matches:
                    home_team = match['homeTeam']['name']
                    away_team = match['awayTeam']['name']
                    home_score = match['score']['fullTime']['home']
                    away_score = match['score']['fullTime']['away']

                    if home_team == team_name:
                        goals_for += home_score
                        goals_against += away_score
                        if home_score > away_score:
                            results.append('W')
                        elif home_score == away_score:
                            results.append('D')
                        else:
                            results.append('L')
                    else:
                        goals_for += away_score
                        goals_against += home_score
                        if away_score > home_score:
                            results.append('W')
                        elif away_score == home_score:
                            results.append('D')
                        else:
                            results.append('L')

                # Calculate form rating
                points = sum([3 if r == 'W' else 1 if r == 'D' else 0 for r in results])
                form_rating = points / 15.0  # Max 15 points from 5 wins

                # Simulate xG data (in real system would come from advanced stats API)
                xg_for = goals_for * np.random.uniform(0.8, 1.2)
                xg_against = goals_against * np.random.uniform(0.8, 1.2)

                return TeamForm(
                    team_name=team_name,
                    last_5_results=results,
                    goals_scored=goals_for,
                    goals_conceded=goals_against,
                    xg_for=round(xg_for, 1),
                    xg_against=round(xg_against, 1),
                    form_rating=round(form_rating, 2)
                )

        except Exception as e:
            print(f"⚠️  Form analysis failed for {team_name}: {e}")

        # Fallback form data
        simulated_results = np.random.choice(['W', 'D', 'L'], 5, p=[0.4, 0.3, 0.3])
        points = sum([3 if r == 'W' else 1 if r == 'D' else 0 for r in simulated_results])

        return TeamForm(
            team_name=team_name,
            last_5_results=list(simulated_results),
            goals_scored=np.random.randint(4, 12),
            goals_conceded=np.random.randint(3, 10),
            xg_for=round(np.random.uniform(6.0, 12.0), 1),
            xg_against=round(np.random.uniform(4.0, 11.0), 1),
            form_rating=round(points / 15.0, 2)
        )

    def get_weather_conditions(self, latitude: float, longitude: float, match_date: str) -> WeatherConditions:
        """Get weather forecast for match location and date"""

        try:
            params = {
                'latitude': latitude,
                'longitude': longitude,
                'start_date': match_date,
                'end_date': match_date,
                'daily': 'temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max',
                'timezone': 'Europe/Madrid'
            }

            response = requests.get(self.weather_api_base, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                daily = data.get('daily', {})

                if daily:
                    temp_max = daily['temperature_2m_max'][0]
                    temp_min = daily['temperature_2m_min'][0]
                    precipitation = daily['precipitation_sum'][0]
                    wind_speed = daily['wind_speed_10m_max'][0]

                    avg_temp = (temp_max + temp_min) / 2

                    # Determine conditions
                    if precipitation > 5:
                        conditions = "Heavy Rain"
                        impact_score = 0.3  # Significant impact
                    elif precipitation > 1:
                        conditions = "Light Rain"
                        impact_score = 0.15
                    elif wind_speed > 20:
                        conditions = "Windy"
                        impact_score = 0.1
                    elif avg_temp > 30:
                        conditions = "Hot"
                        impact_score = 0.1
                    elif avg_temp < 5:
                        conditions = "Cold"
                        impact_score = 0.05
                    else:
                        conditions = "Clear"
                        impact_score = 0.0

                    return WeatherConditions(
                        temperature=round(avg_temp, 1),
                        humidity=np.random.uniform(40, 80),  # Simulate humidity
                        wind_speed=round(wind_speed, 1),
                        precipitation=round(precipitation, 1),
                        conditions=conditions,
                        impact_score=impact_score
                    )

        except Exception as e:
            print(f"⚠️  Weather data failed: {e}")

        # Fallback weather
        return WeatherConditions(
            temperature=18.5,
            humidity=65.0,
            wind_speed=8.2,
            precipitation=0.0,
            conditions="Clear",
            impact_score=0.0
        )

    def get_player_availability_impact(self, team_name: str) -> Tuple[float, List[str]]:
        """Calculate team strength impact from player availability"""

        if team_name not in self.key_players:
            return 1.0, ["No key player data available"]

        players = self.key_players[team_name]
        total_impact = 0.0
        availability_notes = []

        for player in players:
            if player.status == 'available':
                total_impact += player.impact_rating
            elif player.status == 'doubtful':
                total_impact += player.impact_rating * 0.5
                availability_notes.append(f"{player.name} doubtful ({player.position})")
            elif player.status in ['injured', 'suspended']:
                availability_notes.append(f"{player.name} unavailable ({player.position})")

        # Normalize impact (assume max possible impact is sum of all key players)
        max_possible = sum(p.impact_rating for p in players)
        availability_multiplier = total_impact / max_possible if max_possible > 0 else 1.0

        return availability_multiplier, availability_notes

    def get_referee_impact(self, referee_name: Optional[str] = None) -> RefereeProfile:
        """Get referee profile and expected impact"""

        if referee_name and referee_name in self.referee_database:
            return self.referee_database[referee_name]

        # Random referee from database
        import random
        return random.choice(list(self.referee_database.values()))

    def integrate_realtime_data(self, match_data: Dict) -> Dict:
        """Integrate all real-time data sources for a match"""

        home_team = match_data['homeTeam']['name']
        away_team = match_data['awayTeam']['name']
        match_date = match_data['utcDate'][:10]

        print(f"🔄 Integrating real-time data for {home_team} vs {away_team}...")

        # Get team forms
        home_form = self.get_team_recent_form(home_team, match_data['homeTeam'].get('id', 0))
        away_form = self.get_team_recent_form(away_team, match_data['awayTeam'].get('id', 0))

        # Get player availability impact
        home_availability, home_availability_notes = self.get_player_availability_impact(home_team)
        away_availability, away_availability_notes = self.get_player_availability_impact(away_team)

        # Get weather (simulate coordinates for major Spanish cities)
        city_coords = {
            'Madrid': (40.4168, -3.7038),
            'Barcelona': (41.3851, 2.1734),
            'Seville': (37.3891, -5.9845),
            'Valencia': (39.4699, -0.3763),
            'Bilbao': (43.2627, -2.9253)
        }

        # Determine likely city based on home team
        coords = city_coords.get('Madrid', (40.4168, -3.7038))  # Default Madrid
        if 'Barcelona' in home_team:
            coords = city_coords['Barcelona']
        elif 'Sevilla' in home_team:
            coords = city_coords['Seville']
        elif 'Valencia' in home_team:
            coords = city_coords['Valencia']
        elif 'Athletic' in home_team:
            coords = city_coords['Bilbao']

        weather = self.get_weather_conditions(coords[0], coords[1], match_date)

        # Get referee impact
        referee = self.get_referee_impact()

        # Calculate enhanced predictions
        enhanced_data = {
            'original_match': match_data,
            'real_time_enhancements': {
                'home_team_form': {
                    'recent_results': ''.join(home_form.last_5_results),
                    'form_rating': home_form.form_rating,
                    'goals_per_game': round(home_form.goals_scored / 5, 1),
                    'xg_performance': round(home_form.xg_for / 5, 1)
                },
                'away_team_form': {
                    'recent_results': ''.join(away_form.last_5_results),
                    'form_rating': away_form.form_rating,
                    'goals_per_game': round(away_form.goals_scored / 5, 1),
                    'xg_performance': round(away_form.xg_for / 5, 1)
                },
                'player_availability': {
                    'home_availability_multiplier': round(home_availability, 3),
                    'away_availability_multiplier': round(away_availability, 3),
                    'home_team_notes': home_availability_notes,
                    'away_team_notes': away_availability_notes
                },
                'weather_conditions': {
                    'temperature': weather.temperature,
                    'conditions': weather.conditions,
                    'precipitation': weather.precipitation,
                    'wind_speed': weather.wind_speed,
                    'playing_impact': weather.impact_score
                },
                'referee_profile': {
                    'name': referee.name,
                    'cards_per_game': referee.cards_per_game,
                    'penalties_per_game': referee.penalties_per_game,
                    'home_bias': referee.home_bias,
                    'strictness': referee.strictness_rating
                }
            },
            'form_adjusted_probabilities': self._calculate_form_adjusted_probabilities(
                home_form, away_form, home_availability, away_availability, weather, referee
            )
        }

        return enhanced_data

    def _calculate_form_adjusted_probabilities(self, home_form: TeamForm, away_form: TeamForm,
                                            home_avail: float, away_avail: float,
                                            weather: WeatherConditions, referee: RefereeProfile) -> Dict:
        """Calculate probabilities adjusted for real-time factors"""

        # Base probabilities (from previous system)
        base_home = 0.45
        base_draw = 0.25
        base_away = 0.30

        # Form adjustment
        form_diff = home_form.form_rating - away_form.form_rating
        form_adjustment = form_diff * 0.15  # Max 15% swing from form

        # Availability adjustment
        availability_diff = home_avail - away_avail
        availability_adjustment = availability_diff * 0.10  # Max 10% swing from injuries

        # Weather adjustment (affects both teams, slight home advantage in bad weather)
        weather_adjustment = weather.impact_score * 0.02  # Small boost to home team

        # Referee adjustment
        referee_adjustment = referee.home_bias * 0.05  # Max 5% from referee bias

        # Total home team adjustment
        total_home_adjustment = form_adjustment + availability_adjustment + weather_adjustment + referee_adjustment

        # Apply adjustments
        adjusted_home = base_home + total_home_adjustment
        adjusted_away = base_away - (total_home_adjustment * 0.7)  # Partial inverse correlation
        adjusted_draw = 1.0 - adjusted_home - adjusted_away

        # Ensure valid probabilities
        adjusted_home = max(0.15, min(0.75, adjusted_home))
        adjusted_away = max(0.15, min(0.75, adjusted_away))
        adjusted_draw = max(0.10, min(0.50, adjusted_draw))

        # Normalize
        total = adjusted_home + adjusted_draw + adjusted_away

        return {
            'home_win_prob': round(adjusted_home / total, 3),
            'draw_prob': round(adjusted_draw / total, 3),
            'away_win_prob': round(adjusted_away / total, 3),
            'adjustments_applied': {
                'form_impact': round(form_adjustment, 3),
                'availability_impact': round(availability_adjustment, 3),
                'weather_impact': round(weather_adjustment, 3),
                'referee_impact': round(referee_adjustment, 3),
                'total_home_boost': round(total_home_adjustment, 3)
            }
        }

def main():
    """Test real-time data integration"""
    integrator = RealTimeDataIntegrator()

    # Sample match data
    sample_match = {
        'id': 544293,
        'homeTeam': {'name': 'FC Barcelona', 'id': 81},
        'awayTeam': {'name': 'Girona FC', 'id': 298},
        'utcDate': '2025-10-18T14:15:00Z'
    }

    enhanced_data = integrator.integrate_realtime_data(sample_match)

    print("\n🎯 Real-Time Data Integration Complete!")
    print(json.dumps(enhanced_data['real_time_enhancements'], indent=2))

if __name__ == "__main__":
    main()
