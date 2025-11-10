#!/usr/bin/env python3
"""
Data Quality Enhancement Module
Player injuries, weather effects, referee analysis, and team news parsing
"""

import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import requests

# Import FlashScore integration
try:
    from flashscore_scraper import AdvancedDataIntegrator, FlashScoreScraper
    FLASHSCORE_AVAILABLE = True
except ImportError:
    FLASHSCORE_AVAILABLE = False

class DataQualityEnhancer:
    """Enhanced data collection for better prediction accuracy with FlashScore integration"""

    def __init__(self, football_api_key: str, weather_api_key: Optional[str] = None):
        self.football_api_key = football_api_key
        self.weather_api_key = weather_api_key or "demo_key"  # Free tier available
        self.headers = {'X-Auth-Token': football_api_key}
        self._open_meteo_forecast = "https://api.open-meteo.com/v1/forecast"
        self._open_meteo_archive = "https://archive-api.open-meteo.com/v1/archive"
        self._weather_cache: Dict[str, Dict[str, Any]] = {}
        # Load centralized settings if available
        self._settings = {}
        try:
            import yaml
            from pathlib import Path
            cfg_path = Path(__file__).parent / 'config' / 'settings.yaml'
            if cfg_path.exists():
                with open(cfg_path, 'r', encoding='utf-8') as _f:
                    self._settings = yaml.safe_load(_f) or {}
        except Exception:
            self._settings = {}
        self.setup_directories()

        # Initialize FlashScore integration
        if FLASHSCORE_AVAILABLE:
            self.flashscore_scraper = FlashScoreScraper()  # type: ignore
            self.flashscore_integrator = AdvancedDataIntegrator(self.flashscore_scraper)  # type: ignore
            print("FlashScore.es integration active - enhanced data collection enabled!")
        else:
            self.flashscore_scraper = None
            self.flashscore_integrator = None

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
        # First, try a dedicated injury data provider (API-Football via RapidAPI)
        try:
            injury_data = self._fetch_injury_data_api_football(team_id)
            if injury_data:
                return self._analyze_injury_data(injury_data, team_name)
        except Exception as e:
            print(f"Could not fetch injury data from API-Football for {team_name}: {e}")

        # Next, fall back to squad list analysis (Football-Data.org) for basic insights
        try:
            squad_data = self._fetch_squad_data(team_id)
            if squad_data:
                return self._analyze_squad_availability(squad_data, team_name)
        except Exception as e:
            print(f"Could not fetch squad data for {team_name}: {e}")

        # Final fallback - no real injury API configured
        print(f"Player injury data not available for {team_name} - need injury tracking API")

        return {
            'data_available': False,
            'team_name': team_name,
            'key_players_available': None,
            'key_players_injured': None,
            'strength_reduction_pct': 0.0,  # No adjustment without real data
            'injury_areas': [],
            'expected_lineup_strength': None,
            'injury_concerns': ['Injury data unavailable - requires external injury API'],
            'squad_size': None,
            'recommendation': 'Integrate with API-Football (recommended) or Transfermarkt/PhysioRoom',
            'provenance': {
                'injury_clamped': False,
                'clamped_fields': {}
            }
        }

    def _fetch_squad_data(self, team_id: int) -> Optional[Dict]:
        """Fetch squad data from Football-Data.org"""
        try:
            url = f"https://api.football-data.org/v4/teams/{team_id}"
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"   Could not fetch squad data: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            print(f"   Error fetching squad data: {e}")
            return None

    def _fetch_injury_data_api_football(self, team_id: int) -> Optional[Dict]:
        """Fetch injury / availability data from API-Football (RapidAPI) if available.

        NOTE: API-Football offers injury endpoints on RapidAPI; this method attempts a
        safe request and gracefully returns None if the endpoint or key is missing.
        """
        import os
        try:
            api_key = os.getenv('API_FOOTBALL_KEY')
            if not api_key:
                # API key not configured
                return None

            base_url = 'https://api-football-v1.p.rapidapi.com/v3'
            headers = {
                'X-RapidAPI-Key': api_key,
                'X-RapidAPI-Host': 'api-football-v1.p.rapidapi.com'
            }

            # Season default to current year
            season = str(datetime.now().year)

            # Attempt the injuries endpoint. If unavailable, the request will fail
            url = f"{base_url}/injuries"
            params = {'team': team_id, 'season': season}

            response = requests.get(url, headers=headers, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                # API-Football wraps payload in 'response' normally
                return data.get('response') or data
            else:
                # Non-200 (including 404) - treat as unavailable
                print(f"   API-Football injuries endpoint returned {response.status_code}")
                return None

        except Exception as e:
            print(f"   Error contacting API-Football injuries endpoint: {e}")
            return None

    def _analyze_injury_data(self, injury_payload: Dict, team_name: str) -> Dict:
        """Convert API-Football injury payload into our internal injury report format."""
        if not injury_payload:
            return self._get_empty_injury_data(team_name)

        # injury_payload might be a list of injuries or a wrapper dict
        injuries = injury_payload if isinstance(injury_payload, list) else injury_payload.get('injuries', [])

        injured_players = []
        for item in injuries:
            # Different API versions may structure data differently; try common keys
            player = item.get('player') or item.get('player_name') or {}
            name = player.get('name') if isinstance(player, dict) else player
            reason = item.get('reason') or item.get('type') or 'injury'
            status = item.get('status') or item.get('note') or 'unknown'
            estimated_return = item.get('return_date') or item.get('estimated_return')

            injured_players.append({
                'name': name or item.get('player_name') or 'Unknown',
                'reason': reason,
                'status': status,
                'estimated_return': estimated_return
            })

        # Simple impact heuristic
        injured_count = len(injured_players)
        strength_reduction_pct = min(40.0, injured_count * 8.0)  # 8% per injured key player (heuristic)

        return {
            'data_available': True,
            'team_name': team_name,
            'injured_players': injured_players,
            'injured_count': injured_count,
            'strength_reduction_pct': round(strength_reduction_pct, 1),
            'expected_lineup_strength': round(max(0.0, 100.0 - strength_reduction_pct), 1),
            'injury_areas': list({p.get('reason') for p in injured_players if p.get('reason')}),
            'key_players_available': None,
            'key_players_injured': [p['name'] for p in injured_players],
            'injury_concerns': [f"{p['name']}: {p['reason']} ({p['status']})" for p in injured_players],
            'data_source': 'API-Football (RapidAPI)',
            'recommendation': 'Verify player availability with club announcements',
            'provenance': {
                'injury_clamped': False,
                'clamped_fields': {},
                'source_hits': len(injured_players)
            }
        }

    def _analyze_squad_availability(self, squad_data: Dict, team_name: str) -> Dict:
        """Analyze squad data for basic availability information"""
        
        squad = squad_data.get('squad', [])
        if not squad:
            return self._get_empty_injury_data(team_name)
            
        # Basic squad analysis
        players_by_position = {
            'Goalkeeper': [],
            'Defender': [],
            'Midfielder': [],
            'Attacker': []
        }
        
        for player in squad:
            position = player.get('position', 'Unknown')
            players_by_position.setdefault(position, []).append(player)
            
        # Calculate basic squad strength indicators
        total_players = len(squad)
        goalkeepers = len(players_by_position.get('Goalkeeper', []))
        defenders = len(players_by_position.get('Defender', []))
        midfielders = len(players_by_position.get('Midfielder', []))
        attackers = len(players_by_position.get('Attacker', []))
        
        # Basic availability assessment (since we have no injury data)
        squad_insights = []
        if total_players >= 23:
            squad_insights.append("Full squad available in Football-Data.org")
        else:
            squad_insights.append(f"Squad size: {total_players} players registered")
            
        if goalkeepers < 2:
            squad_insights.append("Limited goalkeeper options")
        if defenders < 6:
            squad_insights.append("Thin defensive options")
        if midfielders < 6:
            squad_insights.append("Limited midfield depth")
        if attackers < 4:
            squad_insights.append("Few attacking options")
            
        return {
            'data_available': True,
            'team_name': team_name,
            'squad_size': total_players,
            'positions': {
                'goalkeepers': goalkeepers,
                'defenders': defenders,
                'midfielders': midfielders,
                'attackers': attackers
            },
            'squad_insights': squad_insights,
            'key_players_available': f"All {total_players} registered players (no injury data)",
            'key_players_injured': "Unknown - no injury API configured",
            'strength_reduction_pct': 0.0,  # Cannot calculate without injury data
            'injury_areas': [],
            'expected_lineup_strength': 100.0,  # Assume full strength without injury data
            'injury_concerns': squad_insights,
            'data_source': 'Football-Data.org squad list (no injury status)',
            'recommendation': 'Add injury tracking API for availability data',
            'provenance': {
                'injury_clamped': False,
                'clamped_fields': {}
            }
        }

    def _get_empty_injury_data(self, team_name: str) -> Dict:
        """Return empty injury data structure"""
        return {
            'data_available': False,
            'team_name': team_name,
            'key_players_available': None,
            'key_players_injured': None,
            'strength_reduction_pct': 0.0,
            'injury_areas': [],
            'expected_lineup_strength': None,
            'injury_concerns': ['Squad data unavailable'],
            'squad_size': None,
            'recommendation': 'Check Football-Data.org API connectivity',
            'provenance': {
                'injury_clamped': False,
                'clamped_fields': {}
            }
        }

    # REMOVED: simulate_injury_analysis - no more synthetic injury data

    def calculate_strength_reduction(self, injury_data: Dict) -> float:
        """Calculate team strength reduction due to injuries"""
        injured_count = injury_data['injured_count']
        affected_positions = injury_data['affected_positions']

        per_player = self._settings.get('constants', {}).get('injury', {}).get('per_player_pct', 3.5)
        midfield_penalty = self._settings.get('constants', {}).get('injury', {}).get('midfield_penalty', 5)
        defense_penalty = self._settings.get('constants', {}).get('injury', {}).get('defense_penalty', 3)
        max_reduction = self._settings.get('constants', {}).get('injury', {}).get('max_reduction_pct', 25)

        base_reduction = injured_count * per_player

        # Additional penalty for critical positions
        if 'midfield' in affected_positions:
            base_reduction += midfield_penalty
        if 'defense' in affected_positions:
            base_reduction += defense_penalty

        # Apply cap only when enforce_caps is enabled in settings
        enforce_caps = self._settings.get('constants', {}).get('enforce_caps', True)
        if enforce_caps:
            final_reduction = min(base_reduction, max_reduction)
            # Record what we clamped for provenance/audit
            if final_reduction != base_reduction:
                self._last_injury_clamps = {
                    'strength_reduction': {
                        'original': base_reduction,
                        'clamped_to': final_reduction,
                        'max_reduction_pct': max_reduction
                    }
                }
            else:
                self._last_injury_clamps = {}
            return final_reduction
        else:
            # No clamping, clear any previous clamp record
            self._last_injury_clamps = {}
            return base_reduction

    def get_weather_impact(self, venue_city: str, match_date: str) -> Dict:
        """Get weather conditions and predict impact on match"""
        try:
            # Use Open-Meteo API (free tier available)
            weather_data = self.fetch_weather_data(venue_city, match_date)
            impact = self.analyze_weather_impact(weather_data)

            # Optionally include provenance/clamp info if configured
            provenance = {}
            if self._settings.get('constants', {}).get('provenance', {}).get('record_clamps', True):
                provenance = {
                    'weather_clamped': impact.get('weather_clamped', False),
                    'clamped_fields': impact.get('clamped_fields', {})
                }

            return {
                'conditions': weather_data,
                'impact_assessment': impact,
                'goal_adjustment': impact['goal_modifier'],
                'style_impact': impact['playing_style_effect'],
                'provenance': provenance
            }

        except Exception as e:
            print(f"⚠️ Could not fetch weather data: {e}")
            return self.get_default_weather_data()

    def fetch_weather_data(self, city: str, match_date: str) -> Dict:
        """Enhanced weather data collection with stadium-specific intelligence"""
        cache_key = f"{city.lower()}::{match_date}"
        cached = self._weather_cache.get(cache_key)
        if cached:
            return cached

        try:
            stadium_coordinates = self._get_stadium_coordinates(city)
            resolved = self._fetch_open_meteo_weather(stadium_coordinates, match_date)
            if resolved:
                self._weather_cache[cache_key] = resolved
                return resolved
        except Exception as e:
            print(f"⚠️ Weather API error: {e}")

        fallback = self._generate_seasonal_weather(city, match_date)
        self._weather_cache[cache_key] = fallback
        return fallback

    def _fetch_open_meteo_weather(self, coords: Dict[str, Any], match_date: str) -> Optional[Dict[str, Any]]:
        """Call Open-Meteo forecast/archive endpoints and summarise the response."""
        try:
            match_day = datetime.strptime(match_date[:10], "%Y-%m-%d").date()
        except ValueError:
            return None

        today = datetime.utcnow().date()
        use_archive = match_day < today - timedelta(days=1)
        base_url = self._open_meteo_archive if use_archive else self._open_meteo_forecast

        params = {
            "latitude": coords.get('lat', 40.0),
            "longitude": coords.get('lon', 0.0),
            "start_date": match_day.isoformat(),
            "end_date": match_day.isoformat(),
            "hourly": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m",
            "timezone": "UTC",
        }

        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()

        payload = response.json()
        hourly = payload.get("hourly", {})
        if not hourly:
            return None

        def _avg(series: Any) -> Optional[float]:
            values = [float(v) for v in series if isinstance(v, (int, float))]
            return sum(values) / len(values) if values else None

        temperature = _avg(hourly.get("temperature_2m", []))
        wind_speed = _avg(hourly.get("wind_speed_10m", []))
        humidity = _avg(hourly.get("relative_humidity_2m", []))
        precipitation_series = [float(v) for v in hourly.get("precipitation", []) if isinstance(v, (int, float))]
        precipitation = sum(max(v, 0.0) for v in precipitation_series)

        if temperature is None or wind_speed is None:
            return None

        humidity = humidity if humidity is not None else 60.0
        precipitation = round(precipitation, 2)
        wind_speed = round(wind_speed, 1)
        temperature = round(temperature, 1)

        visibility = 18.0
        if precipitation > 5:
            visibility = 6.0
        elif precipitation > 2:
            visibility = 10.0
        elif precipitation > 0.5:
            visibility = 14.0
        elif wind_speed > 25:
            visibility = 12.0

        conditions = self._determine_conditions(temperature, precipitation, wind_speed)

        return {
            "temperature": temperature,
            "humidity": round(humidity, 1),
            "wind_speed": wind_speed,
            "precipitation": precipitation,
            "conditions": conditions,
            "visibility": round(visibility, 1),
            "pressure": 1013,
            "source": "open-meteo",
        }

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

        # Extract raw values
        temperature = weather.get('temperature', 20)
        precipitation = weather.get('precipitation', 0)
        wind_speed = weather.get('wind_speed', 10)
        humidity = weather.get('humidity', 60)
        conditions = weather.get('conditions', 'clear')

        # Clamping / caps provenance
        clamped = False
        clamped_fields = {}
        enforce_caps = self._settings.get('constants', {}).get('enforce_caps', True)
        caps = self._settings.get('constants', {}).get('caps', {}) if enforce_caps else {}

        if enforce_caps and caps:
            # Temperature
            tmin = caps.get('temperature', {}).get('min', -100)
            tmax = caps.get('temperature', {}).get('max', 100)
            if temperature < tmin:
                clamped = True
                clamped_fields['temperature'] = {'original': temperature, 'clamped_to': tmin}
                temperature = tmin
            elif temperature > tmax:
                clamped = True
                clamped_fields['temperature'] = {'original': temperature, 'clamped_to': tmax}
                temperature = tmax

            # Precipitation
            pmin = caps.get('precipitation', {}).get('min', 0.0)
            pmax = caps.get('precipitation', {}).get('max', 100.0)
            if precipitation < pmin:
                clamped = True
                clamped_fields['precipitation'] = {'original': precipitation, 'clamped_to': pmin}
                precipitation = pmin
            elif precipitation > pmax:
                clamped = True
                clamped_fields['precipitation'] = {'original': precipitation, 'clamped_to': pmax}
                precipitation = pmax

            # Wind
            wmin = caps.get('wind_speed', {}).get('min', 0.0)
            wmax = caps.get('wind_speed', {}).get('max', 100.0)
            if wind_speed < wmin:
                clamped = True
                clamped_fields['wind_speed'] = {'original': wind_speed, 'clamped_to': wmin}
                wind_speed = wmin
            elif wind_speed > wmax:
                clamped = True
                clamped_fields['wind_speed'] = {'original': wind_speed, 'clamped_to': wmax}
                wind_speed = wmax

            # Humidity
            hmin = caps.get('humidity', {}).get('min', 0.0)
            hmax = caps.get('humidity', {}).get('max', 100.0)
            if humidity < hmin:
                clamped = True
                clamped_fields['humidity'] = {'original': humidity, 'clamped_to': hmin}
                humidity = hmin
            elif humidity > hmax:
                clamped = True
                clamped_fields['humidity'] = {'original': humidity, 'clamped_to': hmax}
                humidity = hmax

        # Store last clamps for external provenance use
        self._last_weather_clamps = clamped_fields if clamped else {}

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

        result = {
            'goal_modifier': final_modifier,
            'playing_style_effect': playing_style_effect,
            'weather_advantage': weather_advantage,
            'tactical_adjustments': tactical_adjustments,
            'stadium_effects': stadium_effects,
            'adaptability_notes': adaptability_notes,
            'weather_severity': self._assess_weather_severity(temperature, precipitation, wind_speed),
            'conditions_summary': self._generate_conditions_summary(weather, final_modifier)
        }

        # Attach provenance if requested
        if self._settings.get('constants', {}).get('provenance', {}).get('record_clamps', True):
            result['weather_clamped'] = bool(self._last_weather_clamps)
            result['clamped_fields'] = self._last_weather_clamps

        return result

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
        """Get referee analysis with real Football-Data.org referee information"""
        if not referee_name or referee_name in ['TBD', 'Unknown Referee', 'Referee TBD']:
            print(f"Referee not yet assigned for match")
            return self.get_default_referee_data()

        # Try to get real referee statistics from Football-Data.org historical data
        try:
            referee_stats = self._fetch_real_referee_stats(referee_name)
            if referee_stats and referee_stats.get('matches_analyzed', 0) > 0:
                print(f"Using real referee data for {referee_name}")
                return self._build_referee_analysis(referee_stats, referee_name)
        except Exception as e:
            print(f"Could not fetch referee stats for {referee_name}: {e}")
        
        # Fallback: at least return the referee name from API
        print(f"Limited referee data for {referee_name} - using basic info only")
        result = self.get_default_referee_data()
        result['name'] = referee_name  # At least store the actual referee name from API
        result['data_available'] = True  # We do have the referee name from Football-Data.org
        return result

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

    def _fetch_real_referee_stats(self, referee_name: str) -> Optional[Dict]:
        """Fetch real referee statistics from Football-Data.org historical matches"""
        try:
            # Get recent finished matches from multiple competitions to find this referee's history
            competitions = ['PD', 'PL', 'SA', 'BL1', 'FL1']  # La Liga, Premier League, Serie A, Bundesliga, Ligue 1
            referee_matches = []
            
            for comp in competitions:
                if len(referee_matches) >= 20:  # Stop if we have enough data
                    break
                    
                try:
                    url = f"https://api.football-data.org/v4/competitions/{comp}/matches"
                    params = {"status": "FINISHED", "limit": 50}
                    
                    response = requests.get(url, headers=self.headers, params=params, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Find matches refereed by this referee
                        for match in data.get('matches', []):
                            referees = match.get('referees', [])
                            for ref in referees:
                                if (ref.get('name', '').lower() == referee_name.lower() and 
                                    ref.get('type') == 'REFEREE'):
                                    referee_matches.append(match)
                                    break
                                    
                except Exception as e:
                    print(f"   Could not check {comp} for referee {referee_name}: {e}")
                    continue
                    
            if not referee_matches:
                return None
                
            # Analyze referee patterns from real matches
            return self._analyze_real_referee_data(referee_name, referee_matches)
            
        except Exception as e:
            print(f"   Error fetching referee stats: {e}")
            return None

    def _analyze_real_referee_data(self, referee_name: str, matches: List[Dict]) -> Dict:
        """Analyze real referee performance data from match history"""
        if not matches:
            return None
            
        total_matches = len(matches)
        home_wins = 0
        away_wins = 0
        draws = 0
        total_home_goals = 0
        total_away_goals = 0
        
        # Analyze match outcomes
        for match in matches:
            score = match.get('score', {}).get('fullTime', {})
            home_score = score.get('home')
            away_score = score.get('away')
            
            if home_score is not None and away_score is not None:
                total_home_goals += home_score
                total_away_goals += away_score
                
                if home_score > away_score:
                    home_wins += 1
                elif away_score > home_score:
                    away_wins += 1
                else:
                    draws += 1
        
        # Calculate referee bias
        if total_matches > 0:
            home_win_pct = (home_wins / total_matches) * 100
            draw_pct = (draws / total_matches) * 100
            away_win_pct = (away_wins / total_matches) * 100
            
            # Home bias calculation (normal home advantage is ~45-50%)
            home_bias_pct = home_win_pct
            if home_bias_pct > 55:
                bias_description = "Tends to favor home team"
            elif home_bias_pct < 40:
                bias_description = "Slightly favors away team"
            else:
                bias_description = "Balanced officiating"
        else:
            home_bias_pct = 50
            bias_description = "Insufficient data"
            
        # Estimate cards based on match intensity (goals as proxy)
        avg_goals_per_match = (total_home_goals + total_away_goals) / max(total_matches, 1)
        estimated_cards = min(2.0 + (avg_goals_per_match * 0.3), 6.0)  # Estimate based on match intensity
        
        return {
            'matches_analyzed': total_matches,
            'home_bias_pct': round(home_bias_pct, 1),
            'bias_description': bias_description,
            'home_wins': home_wins,
            'away_wins': away_wins,
            'draws': draws,
            'avg_goals_per_match': round(avg_goals_per_match, 2),
            'estimated_cards_per_match': round(estimated_cards, 1),
            'data_quality_score': min(85, 60 + (total_matches * 2))  # Higher score with more matches
        }

    def _build_referee_analysis(self, stats: Dict, referee_name: str = 'Unknown') -> Dict:
        """Build comprehensive referee analysis from real statistics"""
        bias_pct = stats.get('home_bias_pct', 50)
        matches_count = stats.get('matches_analyzed', 0)
        
        # Determine experience level
        if matches_count >= 15:
            experience = 'experienced'
            confidence = 'high'
        elif matches_count >= 8:
            experience = 'moderate'
            confidence = 'medium'
        else:
            experience = 'limited_data'
            confidence = 'low'
            
        return {
            'name': referee_name,  # Use the referee name passed to the function
            'data_available': True,
            'experience_level': experience,
            'matches_analyzed': matches_count,
            'home_bias_pct': bias_pct,
            'bias_description': stats.get('bias_description', 'Balanced'),
            'estimated_cards': stats.get('estimated_cards_per_match', 3.5),
            'key_tendencies': [
                f"Analyzed {matches_count} recent matches",
                stats.get('bias_description', 'Balanced officiating'),
                f"Estimated {stats.get('estimated_cards_per_match', 3.5):.1f} cards per match"
            ],
            'data_quality_score': stats.get('data_quality_score', 75),
            'confidence_level': confidence,
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

    # REMOVED: simulate_referee_stats - no more synthetic referee data

    def parse_team_news(self, team_name: str, match_date: str) -> Dict:
        """Parse team news and predicted lineups with available data sources"""
        
        # Try to get team news from available sources
        try:
            team_news = self._fetch_team_news_data(team_name, match_date)
            if team_news and team_news.get('news_items'):
                print(f"Found {len(team_news.get('news_items', []))} news items for {team_name}")
                return self._analyze_team_news(team_news, team_name)
        except Exception as e:
            print(f"Could not fetch team news for {team_name}: {e}")
        
        # Fallback
        print(f"Team news unavailable for {team_name} - using basic data only")
        result = self.get_default_team_news()
        result['team_name'] = team_name
        return result

    def _fetch_team_news_data(self, team_name: str, match_date: str) -> Optional[Dict]:
        """Fetch real team news data using NewsAPI (if `NEWSAPI_KEY` present).

        Returns None if no key configured or an error occurs. The function makes a
        conservative request (last 3 days) and returns the JSON payload from NewsAPI.
        """
        import os
        try:
            newsapi_key = os.getenv('NEWSAPI_KEY')
            if not newsapi_key:
                return None

            # Build a focused query for lineup/injury mentions
            query = f'"{team_name}" AND (lineup OR injury OR suspended OR formation OR starting XI)'
            url = "https://newsapi.org/v2/everything"
            params = {
                'q': query,
                'language': 'en',
                'sortBy': 'publishedAt',
                'from': (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d'),
                'pageSize': 20,
                'apiKey': newsapi_key
            }

            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"   NewsAPI responded with status {response.status_code}")
                return None

        except Exception as e:
            print(f"   Error fetching NewsAPI data: {e}")
            return None

    def _analyze_team_news(self, news_data: Dict, team_name: str) -> Dict:
        """Analyze team news articles for lineup and tactical insights"""
        
        articles = news_data.get('articles', [])
        if not articles:
            return self.get_default_team_news()
        
        # Analyze news articles for team insights
        lineup_mentions = 0
        injury_mentions = 0
        tactical_mentions = 0
        sentiment_positive = 0
        sentiment_negative = 0
        
        key_findings = []
        
        for article in articles[:10]:  # Analyze up to 10 recent articles
            title = article.get('title', '').lower()
            description = article.get('description', '').lower()
            content = f"{title} {description}"
            
            # Check for lineup/formation mentions
            if any(word in content for word in ['lineup', 'formation', 'starting', 'xi']):
                lineup_mentions += 1
                
            # Check for injury mentions
            if any(word in content for word in ['injury', 'injured', 'suspended', 'doubtful', 'fitness']):
                injury_mentions += 1
                key_findings.append(f"Injury concerns mentioned in recent news")
                
            # Check for tactical mentions
            if any(word in content for word in ['tactics', 'strategy', 'formation', 'approach']):
                tactical_mentions += 1
                
            # Basic sentiment analysis
            if any(word in content for word in ['confident', 'ready', 'strong', 'optimistic']):
                sentiment_positive += 1
            if any(word in content for word in ['concerns', 'worried', 'problems', 'doubtful']):
                sentiment_negative += 1
        
        # Determine overall insights
        if lineup_mentions > 0:
            key_findings.append(f"Lineup discussions in {lineup_mentions} recent articles")
        if tactical_mentions > 0:
            key_findings.append(f"Tactical analysis in {tactical_mentions} articles")
            
        # Determine sentiment
        if sentiment_positive > sentiment_negative:
            news_sentiment = 'positive'
        elif sentiment_negative > sentiment_positive:
            news_sentiment = 'negative'
        else:
            news_sentiment = 'neutral'
            
        return {
            'data_available': True,
            'team_name': team_name,
            'articles_analyzed': len(articles),
            'key_changes': key_findings or ['No significant team news found'],
            'injury_mentions': injury_mentions,
            'lineup_mentions': lineup_mentions,
            'news_sentiment': news_sentiment,
            'confidence_level': 'medium' if len(articles) >= 5 else 'low',
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

    # REMOVED: simulate_team_news and predict_lineup_impact - no more synthetic team news

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
            'data_available': False,
            'key_players_available': None,
            'key_players_injured': None,
            'strength_reduction_pct': 0.0,
            'injury_areas': [],
            'expected_lineup_strength': None,
            'injury_concerns': ['⚠️ Injury data unavailable'],
            'warning': 'Real injury data requires API integration'
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
            'data_available': False,
            'name': 'Referee TBD',
            'home_bias_pct': None,
            'cards_per_game': None,
            'penalties_per_game': None,
            'strict_level': 'unknown',
            'experience_level': 'unknown',
            'warning': 'Referee data unavailable - appointment not announced'
        }

    def get_default_team_news(self) -> Dict:
        return {
            'data_available': False,
            'formation_expected': 'TBD',
            'key_changes': ['Team news unavailable'],
            'tactical_approach': 'unknown',
            'lineup_strength': None,
            'news_sentiment': 'unknown',
            'warning': 'Team news requires press conference/lineup API integration'
        }

    def comprehensive_data_enhancement(self, match: Dict, venue_info: Optional[Dict] = None) -> Dict:
        """Collect all enhanced data for a match with FlashScore integration"""

        # Accept flexible match formats: support both 'homeTeam' (API) and 'home_team' (normalized)
        def _get_field(m, *keys, default=None):
            if not isinstance(m, dict):
                return default
            for k in keys:
                try:
                    if k in m:
                        return m[k]
                except Exception:
                    continue
            return default

        # Normalize match structure defensively
        normalized_match: Dict[str, Any] = {}
        if isinstance(match, dict):
            normalized_match.update(match)

        home_team_obj = _get_field(normalized_match, 'homeTeam', 'home_team', default={}) or {}
        away_team_obj = _get_field(normalized_match, 'awayTeam', 'away_team', default={}) or {}

        # Defensive normalization: allow string names or nested dicts
        if isinstance(home_team_obj, str):
            home_team_obj = {'name': home_team_obj}
        if isinstance(away_team_obj, str):
            away_team_obj = {'name': away_team_obj}

        # Defensive extraction and normalization for IDs and names
        home_team_id = _get_field(home_team_obj, 'id', 'team_id')
        away_team_id = _get_field(away_team_obj, 'id', 'team_id')
        # Coerce IDs to int when possible, else use 0 as placeholder
        try:
            if isinstance(home_team_id, str) and home_team_id.isdigit():
                home_team_id = int(home_team_id)
            elif not isinstance(home_team_id, int):
                home_team_id = int(home_team_id) if isinstance(home_team_id, (float,)) else 0
        except Exception:
            home_team_id = 0
        try:
            if isinstance(away_team_id, str) and away_team_id.isdigit():
                away_team_id = int(away_team_id)
            elif not isinstance(away_team_id, int):
                away_team_id = int(away_team_id) if isinstance(away_team_id, (float,)) else 0
        except Exception:
            away_team_id = 0

        home_team_name = _get_field(home_team_obj, 'name', 'team_name', default='') or ''
        away_team_name = _get_field(away_team_obj, 'name', 'team_name', default='') or ''

        match_date_raw = _get_field(normalized_match, 'utcDate', 'date', default='') or ''
        match_date = match_date_raw[:10]

        # Ensure normalized match contains common keys used downstream (FlashScore integrator, logging)
        if home_team_name and not isinstance(normalized_match.get('home_team'), str):
            normalized_match['home_team'] = home_team_name
        if away_team_name and not isinstance(normalized_match.get('away_team'), str):
            normalized_match['away_team'] = away_team_name
        if 'homeTeam' not in normalized_match and home_team_obj:
            normalized_match['homeTeam'] = home_team_obj
        if 'awayTeam' not in normalized_match and away_team_obj:
            normalized_match['awayTeam'] = away_team_obj

        print("📊 Collecting enhanced data quality information...")

        # Collect all enhanced data (defensive)
        try:
            home_injuries = self.get_player_injury_impact(home_team_id or 0, home_team_name or '')
        except Exception:
            home_injuries = self.get_default_injury_data()
        try:
            away_injuries = self.get_player_injury_impact(away_team_id or 0, away_team_name or '')
        except Exception:
            away_injuries = self.get_default_injury_data()

        venue_city = venue_info.get('city', 'Madrid') if venue_info else 'Madrid'
        weather = self.get_weather_impact(venue_city, match_date)

        referee_name = None
        referee_obj = _get_field(match, 'referee', None) or {}
        if isinstance(referee_obj, dict):
            referee_name = _get_field(referee_obj, 'name', 'referee_name')
        referee = self.get_referee_analysis(referee_name)

        home_team_news = self.parse_team_news(home_team_name, match_date)
        away_team_news = self.parse_team_news(away_team_name, match_date)

        # FlashScore enhanced data
        flashscore_data = {}
        if self.flashscore_integrator:
            try:
                league_key = self._get_league_key_from_match(normalized_match)
                enhanced_match = self.flashscore_integrator.enhance_match_data(normalized_match, league_key) or {}
                flashscore_data = {
                    'flashscore_enhanced': bool(enhanced_match),
                    'team_statistics': {
                        'home': enhanced_match.get('home_team_stats', {}),
                        'away': enhanced_match.get('away_team_stats', {})
                    },
                    'advanced_metrics': enhanced_match.get('advanced_metrics', {}),
                    'odds_data': enhanced_match.get('odds_data', {}),
                    'flashscore_quality_score': enhanced_match.get('data_quality_score', 75)
                }
                print("FlashScore data integrated successfully!")
            except Exception as e:
                print(f"⚠️ FlashScore integration failed: {e}")
                flashscore_data = {'flashscore_enhanced': False}

        # Build provenance summary (concise) for the enhanced data package
        home_prov = home_injuries.get('provenance', {}) if isinstance(home_injuries, dict) else {}
        away_prov = away_injuries.get('provenance', {}) if isinstance(away_injuries, dict) else {}
        weather_prov = weather.get('provenance', {}) if isinstance(weather, dict) else {}

        data_provenance = {
            'home_injury_clamped': bool(home_prov.get('injury_clamped')),
            'home_injury_clamped_fields': home_prov.get('clamped_fields', {}),
            'away_injury_clamped': bool(away_prov.get('injury_clamped')),
            'away_injury_clamped_fields': away_prov.get('clamped_fields', {}),
            'weather_clamped': bool(weather_prov.get('weather_clamped')),
            'weather_clamped_fields': weather_prov.get('clamped_fields', {})
        }

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
            'flashscore_data': flashscore_data,
            'data_quality_score': self.calculate_data_quality_score(
                home_injuries, away_injuries, weather, referee, home_team_news, away_team_news, flashscore_data
            ),
            'data_provenance': data_provenance
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

            # FlashScore Data Quality (0-15 points)
            flashscore_data = data_sources[6] if len(data_sources) > 6 else {}
            if flashscore_data.get('flashscore_enhanced'):
                flashscore_quality = flashscore_data.get('flashscore_quality_score', 75)
                if flashscore_quality >= 80:
                    quality_score += 15
                    quality_details.append("Excellent FlashScore data integration")
                elif flashscore_quality >= 65:
                    quality_score += 10
                    quality_details.append("Good FlashScore data integration")
                else:
                    quality_score += 5
                    quality_details.append("Basic FlashScore data integration")
            else:
                quality_score += 2
                quality_details.append("No FlashScore data available")

        except (IndexError, KeyError, TypeError):
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

    def _get_league_key_from_match(self, match: Dict) -> str:
        """Extract league key from match data for FlashScore integration"""
        # Try to determine league from match data
        # This is a simplified mapping - in production would use more sophisticated detection
        league_indicators = {
            'la-liga': ['Real Madrid', 'FC Barcelona', 'Atletico Madrid', 'Sevilla', 'Valencia'],
            'premier-league': ['Manchester United', 'Manchester City', 'Liverpool', 'Chelsea', 'Arsenal'],
            'bundesliga': ['Bayern Munich', 'Borussia Dortmund', 'RB Leipzig', 'Bayer Leverkusen'],
            'serie-a': ['Juventus', 'AC Milan', 'Inter Milan', 'AS Roma', 'Napoli'],
            'ligue-1': ['PSG', 'Marseille', 'Lyon', 'Monaco', 'Lille']
        }

        if not isinstance(match, dict):
            return 'la-liga'

        def _extract_team_name(team_obj: Any) -> str:
            if isinstance(team_obj, dict):
                return team_obj.get('name') or team_obj.get('team_name') or ''
            if isinstance(team_obj, str):
                return team_obj
            return ''

        home_team = _extract_team_name(match.get('homeTeam')) or _extract_team_name(match.get('home_team'))
        away_team = _extract_team_name(match.get('awayTeam')) or _extract_team_name(match.get('away_team'))

        for league_key, teams in league_indicators.items():
            if any(team in home_team or team in away_team for team in teams):
                return league_key

        # Default fallback
        return 'la-liga'

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

    print("\n📊 Data Quality Analysis:")
    print(f"   Home Team Availability: {enhanced_data['player_availability']['home_team']['expected_lineup_strength']:.1f}%")
    print(f"   Away Team Availability: {enhanced_data['player_availability']['away_team']['expected_lineup_strength']:.1f}%")
    print(f"   Weather Impact: {enhanced_data['weather_conditions']['impact_assessment']['playing_style_effect']}")
    print(f"   Referee Bias: {enhanced_data['referee_analysis']['home_bias_pct']:.1f}% home bias")
    print(f"   Overall Data Quality: {enhanced_data['data_quality_score']:.1f}%")
