"""
Data connectors for external APIs
"""

import asyncio
import aiohttp
import logging
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod
import pandas as pd
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class BaseDataConnector(ABC):
    """Base class for data connectors"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create session"""
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self.session
    
    @abstractmethod
    async def fetch_from_primary_api(self, league: str, data_type: str, season: Optional[str] = None,
                                    start_date: Optional[str] = None, end_date: Optional[str] = None) -> Optional[List[Dict]]:
        pass
    
    @abstractmethod
    async def fetch_from_secondary_api(self, league: str, data_type: str, season: Optional[str] = None,
                                      start_date: Optional[str] = None, end_date: Optional[str] = None) -> Optional[List[Dict]]:
        pass
    
    @abstractmethod
    async def fetch_from_backup_csv(self, league: str, data_type: str, season: Optional[str] = None,
                                   start_date: Optional[str] = None, end_date: Optional[str] = None) -> Optional[List[Dict]]:
        pass


class FootballDataConnector(BaseDataConnector):
    """Connector for football data sources"""
    
    async def fetch_from_primary_api(self, league: str, data_type: str, season: Optional[str] = None,
                                    start_date: Optional[str] = None, end_date: Optional[str] = None) -> Optional[List[Dict]]:
        """Fetch from Football-Data.org API"""
        try:
            logger.info(f"Fetching {data_type} data for {league} from Football-Data.org API")
            
            # Get API key from environment
            import os
            api_key = os.getenv('FOOTBALL_DATA_API_KEY')
            if not api_key:
                logger.error("FOOTBALL_DATA_API_KEY not found in environment")
                return None
            
            headers = {'X-Auth-Token': api_key}
            base_url = "https://api.football-data.org/v4"
            
            # Map league names to Football-Data.org competition codes
            league_codes = {
                'Premier League': 'PL',
                'La Liga': 'PD', 
                'Bundesliga': 'BL1',
                'Serie A': 'SA',
                'Ligue 1': 'FL1',
                'Champions League': 'CL',
                'Europa League': 'EL'
            }
            
            competition_code = league_codes.get(league)
            if not competition_code:
                logger.error(f"League '{league}' not supported by Football-Data.org")
                return None
            
            session = await self._get_session()
            
            if data_type == 'matches':
                # Get fixtures/matches
                url = f"{base_url}/competitions/{competition_code}/matches"
                params = {}
                if start_date:
                    params['dateFrom'] = start_date
                if end_date:
                    params['dateTo'] = end_date
                
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        matches = []
                        for match in data.get('matches', []):
                            matches.append({
                                "id": match['id'],
                                "home_team": match['homeTeam']['name'],
                                "away_team": match['awayTeam']['name'], 
                                "date": match['utcDate'][:10],  # Extract date part
                                "home_score": match['score']['fullTime']['home'],
                                "away_score": match['score']['fullTime']['away'],
                                "status": match['status'].lower(),
                                "matchday": match.get('matchday'),
                                "season": match.get('season', {}).get('id')
                            })
                        return matches
                    else:
                        logger.error(f"API request failed with status {response.status}")
                        return None
                        
            elif data_type == 'teams':
                # Get teams in competition
                url = f"{base_url}/competitions/{competition_code}/teams"
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        teams = []
                        for team in data.get('teams', []):
                            teams.append({
                                "id": team['id'],
                                "name": team['name'],
                                "league": league,
                                "short_name": team.get('shortName'),
                                "tla": team.get('tla'),  # Three letter abbreviation
                                "founded": team.get('founded'),
                                "venue": team.get('venue')
                            })
                        return teams
                    else:
                        logger.error(f"API request failed with status {response.status}")
                        return None
            
            elif data_type == 'standings':
                # Get league table/standings
                url = f"{base_url}/competitions/{competition_code}/standings"
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        standings = []
                        for table in data.get('standings', []):
                            if table['type'] == 'TOTAL':
                                for team in table['table']:
                                    standings.append({
                                        "position": team['position'],
                                        "team_id": team['team']['id'],
                                        "team_name": team['team']['name'],
                                        "played": team['playedGames'],
                                        "won": team['won'],
                                        "drawn": team['draw'], 
                                        "lost": team['lost'],
                                        "goals_for": team['goalsFor'],
                                        "goals_against": team['goalsAgainst'],
                                        "goal_difference": team['goalDifference'],
                                        "points": team['points'],
                                        "form": team.get('form')
                                    })
                        return standings
                    else:
                        logger.error(f"API request failed with status {response.status}")
                        return None
            
            return []
            
        except Exception as e:
            logger.error(f"Error fetching from Football-Data.org API: {e}")
            return None
    
    async def fetch_from_secondary_api(self, league: str, data_type: str, season: Optional[str] = None,
                                      start_date: Optional[str] = None, end_date: Optional[str] = None) -> Optional[List[Dict]]:
        """Fetch from API-Football"""
        try:
            logger.info(f"Fetching {data_type} data for {league} from API-Football")
            
            # Get API key from environment
            import os
            api_key = os.getenv('API_FOOTBALL_KEY')
            if not api_key:
                logger.error("API_FOOTBALL_KEY not found in environment")
                return None
            
            headers = {
                'X-RapidAPI-Key': api_key,
                'X-RapidAPI-Host': 'api-football-v1.p.rapidapi.com'
            }
            base_url = "https://api-football-v1.p.rapidapi.com/v3"
            
            # Map league names to API-Football league IDs
            league_ids = {
                'Premier League': 39,
                'La Liga': 140,
                'Bundesliga': 78,
                'Serie A': 135,
                'Ligue 1': 61,
                'Champions League': 2,
                'Europa League': 3
            }
            
            league_id = league_ids.get(league)
            if not league_id:
                logger.error(f"League '{league}' not supported by API-Football")
                return None
            
            current_season = season or str(datetime.now().year)
            session = await self._get_session()
            
            if data_type == 'matches':
                # Get fixtures
                url = f"{base_url}/fixtures"
                params = {'league': league_id, 'season': current_season}
                if start_date:
                    params['from'] = start_date
                if end_date:
                    params['to'] = end_date
                
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        matches = []
                        for fixture in data.get('response', []):
                            matches.append({
                                "id": fixture['fixture']['id'],
                                "home_team": fixture['teams']['home']['name'],
                                "away_team": fixture['teams']['away']['name'],
                                "date": fixture['fixture']['date'][:10],
                                "home_score": fixture['goals']['home'],
                                "away_score": fixture['goals']['away'],
                                "status": fixture['fixture']['status']['short'].lower(),
                                "venue": fixture['fixture']['venue']['name'],
                                "referee": fixture['fixture']['referee']
                            })
                        return matches
                    else:
                        logger.error(f"API-Football request failed with status {response.status}")
                        return None
                        
            elif data_type == 'teams':
                # Get teams in league
                url = f"{base_url}/teams"
                params = {'league': league_id, 'season': current_season}
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        teams = []
                        for team_data in data.get('response', []):
                            team = team_data['team']
                            teams.append({
                                "id": team['id'],
                                "name": team['name'],
                                "league": league,
                                "founded": team.get('founded'),
                                "country": team.get('country'),
                                "logo": team.get('logo')
                            })
                        return teams
                    else:
                        logger.error(f"API-Football request failed with status {response.status}")
                        return None
            
            elif data_type == 'standings':
                # Get league standings
                url = f"{base_url}/standings"
                params = {'league': league_id, 'season': current_season}
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        standings = []
                        for league_data in data.get('response', []):
                            for standing in league_data['league']['standings'][0]:
                                standings.append({
                                    "position": standing['rank'],
                                    "team_id": standing['team']['id'],
                                    "team_name": standing['team']['name'],
                                    "played": standing['all']['played'],
                                    "won": standing['all']['win'],
                                    "drawn": standing['all']['draw'],
                                    "lost": standing['all']['lose'],
                                    "goals_for": standing['all']['goals']['for'],
                                    "goals_against": standing['all']['goals']['against'],
                                    "goal_difference": standing['goalsDiff'],
                                    "points": standing['points'],
                                    "form": standing.get('form')
                                })
                        return standings
                    else:
                        logger.error(f"API-Football request failed with status {response.status}")
                        return None
            
            return []
            
        except Exception as e:
            logger.error(f"Error fetching from API-Football: {e}")
            return None
    
    async def fetch_from_backup_csv(self, league: str, data_type: str, season: Optional[str] = None,
                                   start_date: Optional[str] = None, end_date: Optional[str] = None) -> Optional[List[Dict]]:
        """Fetch from CSV backup"""
        try:
            logger.info(f"Fetching {data_type} data for {league} from CSV backup")
            
            # Define CSV file paths based on league and data type
            csv_mapping = {
                'Premier League': {
                    'matches': 'data/backup/premier_league_matches.csv',
                    'teams': 'data/backup/premier_league_teams.csv',
                    'standings': 'data/backup/premier_league_standings.csv'
                },
                'La Liga': {
                    'matches': 'data/backup/la_liga_matches.csv', 
                    'teams': 'data/backup/la_liga_teams.csv',
                    'standings': 'data/backup/la_liga_standings.csv'
                }
            }
            
            if league not in csv_mapping or data_type not in csv_mapping[league]:
                logger.error(f"No CSV backup available for {league} {data_type}")
                return None
            
            csv_path = csv_mapping[league][data_type]
            
            try:
                df = pd.read_csv(csv_path)
                # Filter by date if provided
                if start_date and 'date' in df.columns:
                    df = df[df['date'] >= start_date]
                if end_date and 'date' in df.columns:
                    df = df[df['date'] <= end_date]
                
                return df.to_dict('records')
                
            except FileNotFoundError:
                logger.error(f"CSV backup file not found: {csv_path}")
                return None
            except Exception as e:
                logger.error(f"Error reading CSV backup: {e}")
                return None
                
        except Exception as e:
            logger.error(f"Error in CSV backup fetch: {e}")
            return None


class BasketballDataConnector(BaseDataConnector):
    """Connector for basketball data sources"""
    
    async def fetch_from_primary_api(self, league: str, data_type: str, season: Optional[str] = None,
                                    start_date: Optional[str] = None, end_date: Optional[str] = None) -> Optional[List[Dict]]:
        """Fetch from Ball Don't Lie API"""
        try:
            logger.info(f"Fetching {data_type} data for {league} from Ball Don't Lie API")
            
            # Ball Don't Lie API is free but has rate limits
            base_url = "https://www.balldontlie.io/api/v1"
            session = await self._get_session()
            
            if data_type == 'matches':
                # Get games
                url = f"{base_url}/games"
                params = {}
                if start_date:
                    params['start_date'] = start_date
                if end_date:
                    params['end_date'] = end_date
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        matches = []
                        for game in data.get('data', []):
                            matches.append({
                                "id": game['id'],
                                "home_team": game['home_team']['full_name'],
                                "away_team": game['visitor_team']['full_name'],
                                "date": game['date'][:10],
                                "home_score": game['home_team_score'],
                                "away_score": game['visitor_team_score'],
                                "status": "finished" if game['home_team_score'] else "scheduled",
                                "season": game['season']
                            })
                        return matches
                    else:
                        logger.error(f"Ball Don't Lie API request failed: {response.status}")
                        return None
                        
            elif data_type == 'teams':
                # Get teams
                url = f"{base_url}/teams"
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        teams = []
                        for team in data.get('data', []):
                            teams.append({
                                "id": team['id'],
                                "name": team['full_name'],
                                "league": league,
                                "abbreviation": team['abbreviation'],
                                "city": team['city'],
                                "conference": team['conference'],
                                "division": team['division']
                            })
                        return teams
                    else:
                        logger.error(f"Ball Don't Lie API request failed: {response.status}")
                        return None
            
            return []
            
        except Exception as e:
            logger.error(f"Error fetching from Ball Don't Lie API: {e}")
            return None
    
    async def fetch_from_secondary_api(self, league: str, data_type: str, season: Optional[str] = None,
                                      start_date: Optional[str] = None, end_date: Optional[str] = None) -> Optional[List[Dict]]:
        """Fetch from SportsData.io NBA API"""
        try:
            logger.info(f"Fetching {data_type} data for {league} from SportsData.io")
            
            import os
            api_key = os.getenv('SPORTSDATA_API_KEY')
            if not api_key:
                logger.error("SPORTSDATA_API_KEY not found in environment")
                return None
            
            base_url = "https://api.sportsdata.io/v3/nba/scores/json"
            params = {'key': api_key}
            session = await self._get_session()
            
            if data_type == 'matches':
                current_season = season or str(datetime.now().year)
                url = f"{base_url}/Games/{current_season}"
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        matches = []
                        for game in data:
                            if start_date and game['Day'] < start_date:
                                continue
                            if end_date and game['Day'] > end_date:
                                continue
                                
                            matches.append({
                                "id": game['GameID'],
                                "home_team": game['HomeTeam'],
                                "away_team": game['AwayTeam'],
                                "date": game['Day'],
                                "home_score": game['HomeTeamScore'],
                                "away_score": game['AwayTeamScore'],
                                "status": game['Status'].lower(),
                                "season": game['Season']
                            })
                        return matches
                    else:
                        logger.error(f"SportsData.io request failed: {response.status}")
                        return None
            
            return []
            
        except Exception as e:
            logger.error(f"Error fetching from SportsData.io: {e}")
            return None
    
    async def fetch_from_backup_csv(self, league: str, data_type: str, season: Optional[str] = None,
                                   start_date: Optional[str] = None, end_date: Optional[str] = None) -> Optional[List[Dict]]:
        """Fetch from CSV backup for basketball"""
        try:
            logger.info(f"Fetching {data_type} data for {league} from CSV backup")
            
            csv_mapping = {
                'NBA': {
                    'matches': 'data/backup/nba_games.csv',
                    'teams': 'data/backup/nba_teams.csv'
                }
            }
            
            if league not in csv_mapping or data_type not in csv_mapping[league]:
                logger.error(f"No CSV backup available for {league} {data_type}")
                return None
            
            csv_path = csv_mapping[league][data_type]
            
            try:
                df = pd.read_csv(csv_path)
                if start_date and 'date' in df.columns:
                    df = df[df['date'] >= start_date]
                if end_date and 'date' in df.columns:
                    df = df[df['date'] <= end_date]
                
                return df.to_dict('records')
                
            except FileNotFoundError:
                logger.error(f"CSV backup file not found: {csv_path}")
                return None
                
        except Exception as e:
            logger.error(f"Error in basketball CSV backup fetch: {e}")
            return None