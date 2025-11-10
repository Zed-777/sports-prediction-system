"""
Data ingestion pipeline for sports data from multiple sources
"""

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from app.data.connectors import BasketballDataConnector, FootballDataConnector
from app.data.schemas import validate_raw_data
from app.utils.caching import CacheManager
from app.utils.retry import retry_with_backoff

logger = logging.getLogger(__name__)


@dataclass
class DataIngestionResult:
    """Result of data ingestion operation"""
    success: bool
    source: str
    records_count: int
    data_hash: str
    timestamp: datetime
    error_message: Optional[str] = None


class DataIngestionPipeline:
    """
    Main data ingestion pipeline that orchestrates data collection
    from multiple sources with fallback mechanisms.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.cache_manager = CacheManager(config.get('data_engineering', {}).get('caching', {}))

        # Initialize connectors
        self.football_connector = FootballDataConnector(config['data_sources']['football'])
        self.basketball_connector = BasketballDataConnector(config['data_sources']['basketball'])

        # Setup directories
        self.raw_data_dir = Path("data/raw")
        self.processed_data_dir = Path("data/processed")
        self.snapshots_dir = Path("data/snapshots")

        for directory in [self.raw_data_dir, self.processed_data_dir, self.snapshots_dir]:
            directory.mkdir(parents=True, exist_ok=True)

    async def ingest_league_data(
        self,
        league: str,
        season: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        force_refresh: bool = False
    ) -> List[DataIngestionResult]:
        """
        Ingest data for a specific league and time period.
        
        Args:
            league: League name (e.g., "La Liga", "Premier League")
            season: Season string (e.g., "2023-24")
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            force_refresh: Force re-download even if cached data exists
            
        Returns:
            List of ingestion results for each data source
        """
        logger.info(f"Starting data ingestion for {league}")

        results = []

        # Determine sport type from league
        sport_type = self._get_sport_type(league)

        if sport_type == 'football':
            connector = self.football_connector
        elif sport_type == 'basketball':
            connector = self.basketball_connector
        else:
            raise ValueError(f"Unsupported league: {league}")

        # Define data types to collect
        data_types = ['matches', 'teams', 'players', 'standings', 'fixtures']

        # Collect data from each source with fallback
        for data_type in data_types:
            result = await self._ingest_data_with_fallback(
                connector=connector,
                league=league,
                data_type=data_type,
                season=season,
                start_date=start_date,
                end_date=end_date,
                force_refresh=force_refresh
            )
            results.append(result)

        # Create data snapshot if enabled
        if self.config.get('reproducibility', {}).get('data_snapshots', {}).get('enabled', True):
            await self._create_data_snapshot(league, season, results)

        logger.info(f"Data ingestion completed for {league}. Success rate: {sum(r.success for r in results)}/{len(results)}")

        return results

    async def _ingest_data_with_fallback(
        self,
        connector: Union[FootballDataConnector, BasketballDataConnector],
        league: str,
        data_type: str,
        season: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        force_refresh: bool = False
    ) -> DataIngestionResult:
        """
        Ingest data with fallback mechanism across multiple sources.
        """
        fallback_order = self.config['data_engineering']['fallbacks']['order']

        for source_priority, source_name in enumerate(fallback_order):
            try:
                logger.info(f"Attempting to fetch {data_type} data from {source_name}")

                # Check cache first
                cache_key = f"{league}_{data_type}_{season}_{start_date}_{end_date}_{source_name}"

                if not force_refresh:
                    cached_data = await self.cache_manager.get(cache_key)
                    if cached_data:
                        logger.info(f"Using cached data for {cache_key}")
                        return DataIngestionResult(
                            success=True,
                            source=f"{source_name}_cached",
                            records_count=len(cached_data),
                            data_hash=self._calculate_data_hash(cached_data),
                            timestamp=datetime.utcnow()
                        )

                # Fetch fresh data
                data = await self._fetch_data_from_source(
                    connector=connector,
                    source_name=source_name,
                    league=league,
                    data_type=data_type,
                    season=season,
                    start_date=start_date,
                    end_date=end_date
                )

                if data is not None and len(data) > 0:
                    # Validate data schema
                    validation_result = validate_raw_data(data, data_type)
                    if not validation_result.is_valid:
                        logger.warning(f"Data validation failed for {source_name}: {validation_result.errors}")
                        continue

                    # Save raw data
                    await self._save_raw_data(data, league, data_type, source_name, season)

                    # Cache data
                    await self.cache_manager.set(cache_key, data)

                    logger.info(f"Successfully fetched {len(data)} records from {source_name}")

                    return DataIngestionResult(
                        success=True,
                        source=source_name,
                        records_count=len(data),
                        data_hash=self._calculate_data_hash(data),
                        timestamp=datetime.utcnow()
                    )

            except Exception as e:
                logger.error(f"Failed to fetch data from {source_name}: {str(e)}")

                # If this is the last fallback option, return failure
                if source_priority == len(fallback_order) - 1:
                    return DataIngestionResult(
                        success=False,
                        source=source_name,
                        records_count=0,
                        data_hash="",
                        timestamp=datetime.utcnow(),
                        error_message=str(e)
                    )

                continue

        # Should not reach here, but just in case
        return DataIngestionResult(
            success=False,
            source="unknown",
            records_count=0,
            data_hash="",
            timestamp=datetime.utcnow(),
            error_message="All fallback sources failed"
        )

    @retry_with_backoff(max_attempts=5, backoff_strategy='exponential')
    async def _fetch_data_from_source(
        self,
        connector: Union[FootballDataConnector, BasketballDataConnector],
        source_name: str,
        league: str,
        data_type: str,
        season: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Optional[List[Dict]]:
        """
        Fetch data from a specific source using the appropriate connector.
        """
        if source_name == 'primary_api':
            return await connector.fetch_from_primary_api(league, data_type, season, start_date, end_date)
        elif source_name == 'secondary_api':
            return await connector.fetch_from_secondary_api(league, data_type, season, start_date, end_date)
        elif source_name == 'backup_csv':
            return await connector.fetch_from_backup_csv(league, data_type, season, start_date, end_date)
        else:
            raise ValueError(f"Unknown source: {source_name}")

    async def _save_raw_data(
        self,
        data: List[Dict],
        league: str,
        data_type: str,
        source: str,
        season: Optional[str] = None
    ):
        """
        Save raw data to disk with appropriate structure.
        """
        # Create directory structure
        league_dir = self.raw_data_dir / league.replace(' ', '_').lower()
        league_dir.mkdir(exist_ok=True)

        # Generate filename
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        season_str = f"_{season}" if season else ""
        filename = f"{data_type}_{source}_{timestamp}{season_str}.json"

        file_path = league_dir / filename

        # Save data
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)

        logger.info(f"Raw data saved to {file_path}")

    async def _create_data_snapshot(
        self,
        league: str,
        season: Optional[str],
        results: List[DataIngestionResult]
    ):
        """
        Create an immutable data snapshot for reproducibility.
        """
        snapshot_info = {
            'league': league,
            'season': season,
            'timestamp': datetime.utcnow().isoformat(),
            'results': [
                {
                    'success': r.success,
                    'source': r.source,
                    'records_count': r.records_count,
                    'data_hash': r.data_hash,
                    'error_message': r.error_message
                }
                for r in results
            ],
            'total_records': sum(r.records_count for r in results if r.success),
            'success_rate': sum(r.success for r in results) / len(results)
        }

        # Generate snapshot ID
        snapshot_id = hashlib.sha256(
            f"{league}_{season}_{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()[:12]

        snapshot_file = self.snapshots_dir / f"snapshot_{snapshot_id}.json"

        with open(snapshot_file, 'w', encoding='utf-8') as f:
            json.dump(snapshot_info, f, indent=2)

        logger.info(f"Data snapshot created: {snapshot_file}")

    def _get_sport_type(self, league: str) -> str:
        """
        Determine sport type from league name.
        """
        football_leagues = [
            'la liga', 'premier league', 'bundesliga', 'serie a', 'ligue 1',
            'champions league', 'europa league', 'world cup', 'euros'
        ]

        basketball_leagues = [
            'nba', 'euroleague', 'acb', 'ncaa basketball'
        ]

        league_lower = league.lower()

        if any(fl in league_lower for fl in football_leagues):
            return 'football'
        elif any(bl in league_lower for bl in basketball_leagues):
            return 'basketball'
        else:
            # Default to football for unknown leagues
            logger.warning(f"Unknown league type for {league}, defaulting to football")
            return 'football'

    def _calculate_data_hash(self, data: List[Dict]) -> str:
        """
        Calculate hash of data for integrity checking.
        """
        data_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(data_str.encode()).hexdigest()

    async def get_ingestion_status(self, league: str) -> Dict[str, Any]:
        """
        Get status of data ingestion for a league.
        """
        league_dir = self.raw_data_dir / league.replace(' ', '_').lower()

        if not league_dir.exists():
            return {'status': 'no_data', 'last_update': None, 'data_types': []}

        data_files = list(league_dir.glob('*.json'))

        if not data_files:
            return {'status': 'no_data', 'last_update': None, 'data_types': []}

        # Get most recent file
        latest_file = max(data_files, key=lambda f: f.stat().st_mtime)
        last_update = datetime.fromtimestamp(latest_file.stat().st_mtime)

        # Get available data types
        data_types = list(set(f.name.split('_')[0] for f in data_files))

        return {
            'status': 'data_available',
            'last_update': last_update.isoformat(),
            'data_types': data_types,
            'total_files': len(data_files)
        }
