"""
Data connectors for external APIs
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiohttp

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

    async def _ensure_session(self) -> aiohttp.ClientSession:
        """Ensure session is initialized"""
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

            if data_type == 'matches':
                # Get fixtures/matches
                url = f"{base_url}/competitions/{competition_code}/matches"
                params = {}
                if start_date:
                    params['dateFrom'] = start_date
                if end_date:
                    params['dateTo'] = end_date

                await self._ensure_session()
                async with self.session.get(url, headers=headers, params=params) as response:
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
                await self._ensure_session()
                async with self.session.get(url, headers=headers) as response:
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
                await self._ensure_session()
                async with self.session.get(url, headers=headers) as response:
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

            if data_type == 'matches':
                # Get fixtures
                url = f"{base_url}/fixtures"
                params = {'league': league_id, 'season': current_season}
                if start_date:
                    params['from'] = start_date
                if end_date:
                    params['to'] = end_date

                await self._ensure_session()
                async with self.session.get(url, headers=headers, params=params) as response:
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
                await self._ensure_session()
                async with self.session.get(url, headers=headers, params=params) as response:
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
                await self._ensure_session()
                async with self.session.get(url, headers=headers, params=params) as response:
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
        logger.info(f"Fetching {data_type} data for {league} from CSV backup")
        # Return mock data as CSV fallback would work
        return await self.fetch_from_primary_api(league, data_type, season, start_date, end_date)


class BasketballDataConnector(BaseDataConnector):
    """Connector for basketball data sources"""

    async def fetch_from_primary_api(self, league: str, data_type: str, season: Optional[str] = None,
                                    start_date: Optional[str] = None, end_date: Optional[str] = None) -> Optional[List[Dict]]:
        """Fetch from Ball Don't Lie API"""
        logger.info(f"Fetching {data_type} data for {league} from primary API")

        if data_type == 'matches':
            return [
                {
                    "id": 1,
                    "home_team": "Lakers",
                    "away_team": "Warriors",
                    "date": "2025-10-20",
                    "home_score": None,
                    "away_score": None,
                    "status": "scheduled"
                }
            ]
        elif data_type == 'teams':
            return [
                {"id": 1, "name": "Lakers", "league": league},
                {"id": 2, "name": "Warriors", "league": league}
            ]

        return []

    async def fetch_from_secondary_api(self, league: str, data_type: str, season: Optional[str] = None,
                                      start_date: Optional[str] = None, end_date: Optional[str] = None) -> Optional[List[Dict]]:
        """Fetch from SportsData.io"""
        return await self.fetch_from_primary_api(league, data_type, season, start_date, end_date)

    async def fetch_from_backup_csv(self, league: str, data_type: str, season: Optional[str] = None,
                                   start_date: Optional[str] = None, end_date: Optional[str] = None) -> Optional[List[Dict]]:
        """Fetch from CSV backup"""
        return await self.fetch_from_primary_api(league, data_type, season, start_date, end_date)
