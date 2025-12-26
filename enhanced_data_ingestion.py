#!/usr/bin/env python3
"""
Enhanced Data Ingestion System
Multi-source data collection with FlashScore.es integration and advanced caching
"""

import argparse
import json
import logging
import os
import time
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import requests
from app.utils.http import safe_request_get

# Import FlashScore integration
try:
    from flashscore_scraper import AdvancedDataIntegrator, FlashScoreScraper

    FLASHSCORE_AVAILABLE = True
except ImportError:
    FLASHSCORE_AVAILABLE = False
    FlashScoreScraper = None  # type: ignore
    AdvancedDataIntegrator = None  # type: ignore

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Enhanced league mappings with FlashScore URLs
LEAGUE_CONFIG = {
    "la-liga": {
        "football_data_code": "PD",
        "flashscore_url": "/futbol/espana/primera-division/",
        "folder": "la-liga",
        "name": "La Liga",
    },
    "premier-league": {
        "football_data_code": "PL",
        "flashscore_url": "/futbol/inglaterra/premier-league/",
        "folder": "premier-league",
        "name": "Premier League",
    },
    "bundesliga": {
        "football_data_code": "BL1",
        "flashscore_url": "/futbol/alemania/bundesliga/",
        "folder": "bundesliga",
        "name": "Bundesliga",
    },
    "serie-a": {
        "football_data_code": "SA",
        "flashscore_url": "/futbol/italia/serie-a/",
        "folder": "serie-a",
        "name": "Serie A",
    },
    "ligue-1": {
        "football_data_code": "FL1",
        "flashscore_url": "/futbol/francia/ligue-1/",
        "folder": "ligue-1",
        "name": "Ligue 1",
    },
    "champions-league": {
        "football_data_code": "CL",
        "flashscore_url": "/futbol/europa/champions-league/",
        "folder": "champions-league",
        "name": "Champions League",
    },
    "europa-league": {
        "football_data_code": "EL",
        "flashscore_url": "/futbol/europa/europa-league/",
        "folder": "europa-league",
        "name": "Europa League",
    },
}

LEAGUE_ALIASES = {
    "laliga": "la-liga",
    "premierleague": "premier-league",
    "seriea": "serie-a",
    "ligue1": "ligue-1",
    "championsleague": "champions-league",
    "europaleague": "europa-league",
}


@dataclass(frozen=True)
class LeagueConfig:
    code: str
    folder: str
    name: str
    flashscore_url: str | None = None

    @classmethod
    def from_key(cls, key: str) -> "LeagueConfig":
        try:
            config = LEAGUE_CONFIG[key.lower()]
            return cls(
                code=config["football_data_code"],
                folder=config["folder"],
                name=config["name"],
                flashscore_url=config.get("flashscore_url"),
            )
        except KeyError as exc:
            raise ValueError(
                f"Unknown league '{key}'. Supported: {', '.join(sorted(LEAGUE_CONFIG.keys()))}"
            ) from exc


class EnhancedDataIngestion:
    """Sophisticated multi-source data ingestion system"""

    def __init__(self, api_key: str, enable_flashscore: bool = True):
        self.api_key = api_key
        self.headers = {"X-Auth-Token": api_key}
        self.enable_flashscore = enable_flashscore and FLASHSCORE_AVAILABLE

        if self.enable_flashscore:
            if FlashScoreScraper is not None and AdvancedDataIntegrator is not None:
                self.flashscore_scraper = FlashScoreScraper()
                self.flashscore_integrator = AdvancedDataIntegrator(
                    self.flashscore_scraper
                )
                logger.info("[FLASHSCORE] FlashScore.es integration enabled")
            else:
                self.flashscore_scraper = None
                self.flashscore_integrator = None
                logger.warning("[WARNING] FlashScore classes not available")
        else:
            self.flashscore_scraper = None
            self.flashscore_integrator = None
            if enable_flashscore and not FLASHSCORE_AVAILABLE:
                logger.warning(
                    "[WARNING] FlashScore integration requested but not available"
                )

        # Rate limiting
        self.last_request = 0
        self.min_delay = 1.5  # seconds between API calls
        self.max_delay = 4.0

    def _rate_limit(self):
        """Intelligent rate limiting"""
        elapsed = time.time() - self.last_request
        if elapsed < self.min_delay:
            sleep_time = min(
                self.max_delay, self.min_delay + (self.max_delay - self.min_delay) * 0.1
            )
            logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)
        self.last_request = time.time()

    def fetch_football_data_matches(
        self, league: LeagueConfig, season: int
    ) -> dict[str, Any] | None:
        """Fetch match data from Football-Data.org"""
        url = f"https://api.football-data.org/v4/competitions/{league.code}/matches"
        params = {"season": season}

        self._rate_limit()

        try:
            logger.info(
                f"[DATA] Fetching {league.name} season {season} from Football-Data.org"
            )
            response = safe_request_get(
                url,
                headers=self.headers,
                params=params,
                timeout=30,
                retries=3,
                backoff=0.7,
                logger=logger,
            )
            response.raise_for_status()

            data = response.json()
            data["fetched_at"] = datetime.now().isoformat()
            data["data_source"] = "football-data.org"
            data["competition_code"] = league.code
            data["season"] = season

            return data

        except requests.RequestException as e:
            logger.error(
                f"[ERROR] Failed to fetch Football-Data for {league.code} season {season}: {e}"
            )
            return None

    def fetch_flashscore_data(
        self, league: LeagueConfig, days_ahead: int = 30
    ) -> dict[str, Any] | None:
        """Fetch additional data from FlashScore"""
        if not self.flashscore_scraper or not league.flashscore_url:
            return None

        try:
            logger.info(f"[FLASHSCORE] Fetching {league.name} data from FlashScore.es")

            # Allow deterministic test fixtures: if an environment variable points to a fixture JSON
            # or a known fixture file exists under data/cache/flashscore/fixtures/, prefer it.
            fixture_env = os.getenv("FS_FIXTURE_PATH")
            fixture_default = (
                Path("data/cache/flashscore/fixtures") / f"{league.folder}.json"
            )
            if fixture_env and Path(fixture_env).exists():
                logger.debug(f"[FLASHSCORE] Loading fixture from {fixture_env}")
                with open(fixture_env, encoding="utf-8") as f:
                    payload = json.load(f)
                matches = payload.get("matches", [])
                live_scores = payload.get("live_scores", [])
            elif fixture_default.exists():
                logger.debug(f"[FLASHSCORE] Loading default fixture {fixture_default}")
                with fixture_default.open("r", encoding="utf-8") as f:
                    payload = json.load(f)
                matches = payload.get("matches", [])
                live_scores = payload.get("live_scores", [])
            else:
                # Get upcoming matches
                matches = self.flashscore_scraper.get_league_matches(
                    league.folder, days_ahead
                )

                # Get live scores if any
                live_scores = self.flashscore_scraper.get_live_scores()

            flashscore_data = {
                "matches": matches,
                "live_scores": live_scores,
                "fetched_at": datetime.now().isoformat(),
                "data_source": "flashscore.es",
                "league": league.folder,
            }

            return flashscore_data

        except Exception as e:
            logger.error(
                f"[ERROR] Failed to fetch FlashScore data for {league.name}: {e}"
            )
            return None

    def merge_data_sources(
        self,
        football_data: dict[str, Any],
        flashscore_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Merge data from multiple sources into enhanced dataset"""
        merged = dict(football_data)  # Start with Football-Data.org data

        if flashscore_data:
            # Enhance matches with FlashScore data
            football_matches = {
                match["id"]: match for match in football_data.get("matches", [])
            }

            def normalize(name: str) -> str:
                if not name:
                    return ""
                # Remove diacritics, lower, remove punctuation, collapse whitespace
                s = unicodedata.normalize("NFKD", name)
                s = "".join(ch for ch in s if not unicodedata.combining(ch))
                s = s.lower()
                # Replace common abbreviations
                s = s.replace("fc ", "").replace(" cf", "").replace(" sc ", " ")
                # Keep alphanumerics and spaces
                s = "".join(ch if (ch.isalnum() or ch.isspace()) else " " for ch in s)
                s = " ".join(s.split())
                return s

            def similar(a: str, b: str) -> float:
                return SequenceMatcher(None, a, b).ratio()

            for fs_match in flashscore_data.get("matches", []):
                fs_home = normalize(
                    fs_match.get("home_team", "") or fs_match.get("home", "")
                )
                fs_away = normalize(
                    fs_match.get("away_team", "") or fs_match.get("away", "")
                )

                matched = False
                # Try exact or substring matches first
                for fd_match in football_matches.values():
                    home_team = normalize(fd_match.get("homeTeam", {}).get("name", ""))
                    away_team = normalize(fd_match.get("awayTeam", {}).get("name", ""))

                    if not home_team or not away_team or not fs_home or not fs_away:
                        continue

                    # exact/token containment
                    if (
                        home_team == fs_home
                        or fs_home in home_team
                        or home_team in fs_home
                    ) and (
                        away_team == fs_away
                        or fs_away in away_team
                        or away_team in fs_away
                    ):
                        fd_match["flashscore_data"] = fs_match
                        matched = True
                        break

                    # fallback: similarity threshold
                    home_sim = similar(home_team, fs_home)
                    away_sim = similar(away_team, fs_away)
                    if home_sim >= 0.75 and away_sim >= 0.75:
                        fd_match["flashscore_data"] = fs_match
                        matched = True
                        break

                if not matched:
                    # Could not match — store as unmatched for later manual review
                    # append to merged metadata list
                    merged.setdefault("flashscore_unmatched", []).append(fs_match)

            # Add FlashScore metadata
            merged["flashscore_metadata"] = {
                "integrated": True,
                "matches_enhanced": len(
                    [
                        m
                        for m in football_data.get("matches", [])
                        if "flashscore_data" in m
                    ]
                ),
                "live_scores_available": len(flashscore_data.get("live_scores", []))
                > 0,
            }

        merged["data_integration"] = {
            "sources": ["football-data.org"]
            + (["flashscore.es"] if flashscore_data else []),
            "merge_timestamp": datetime.now().isoformat(),
            "quality_score": self._calculate_data_quality(merged),
        }

        return merged

    def _calculate_data_quality(self, data: dict[str, Any]) -> float:
        """Calculate overall data quality score"""
        score = 50.0  # Base score

        # Football-Data.org quality
        if data.get("data_source") == "football-data.org":
            score += 30

        # FlashScore integration
        if data.get("flashscore_metadata", {}).get("integrated"):
            score += 15

        # Match completeness
        matches = data.get("matches", [])
        if matches:
            complete_matches = sum(
                1 for m in matches if m.get("homeTeam") and m.get("awayTeam")
            )
            completeness = complete_matches / len(matches)
            score += completeness * 10

        return min(100.0, score)

    def save_enhanced_snapshot(
        self,
        league: LeagueConfig,
        season: int,
        data: dict[str, Any],
        force: bool = False,
    ) -> Path:
        """Save enhanced multi-source data snapshot"""
        base_dir = Path("data/snapshots") / league.folder
        base_dir.mkdir(parents=True, exist_ok=True)

        # Enhanced filename with data sources
        sources = data.get("data_integration", {}).get("sources", [])
        source_suffix = "_enhanced" if len(sources) > 1 else ""
        target = base_dir / f"season_{season}{source_suffix}.json"

        if target.exists() and not force:
            logger.info(f"[SKIP] Enhanced snapshot already exists: {target}")
            return target

        # Save with metadata
        data["snapshot_metadata"] = {
            "created_at": datetime.now().isoformat(),
            "league": league.name,
            "season": season,
            "data_sources": data.get("data_integration", {}).get("sources", []),
            "quality_score": data.get("data_integration", {}).get("quality_score", 0),
            "flashscore_integrated": data.get("flashscore_metadata", {}).get(
                "integrated", False
            ),
        }

        tmp_path = target.with_suffix(".tmp")
        with tmp_path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
        tmp_path.replace(target)

        logger.info(
            f"[SAVE] Enhanced snapshot: {target} (Quality: {data['snapshot_metadata']['quality_score']:.1f}%)"
        )
        return target

    def ingest_league_season(
        self, league: LeagueConfig, season: int, force: bool = False
    ) -> bool:
        """Ingest complete season data from all available sources"""
        logger.info(
            f"[START] Starting enhanced ingestion for {league.name} season {season}"
        )

        # Fetch Football-Data.org data
        football_data = self.fetch_football_data_matches(league, season)
        if not football_data:
            logger.error(
                f"[ERROR] Failed to fetch base data for {league.name} season {season}"
            )
            return False

        # Fetch FlashScore data if enabled
        flashscore_data = None
        if self.enable_flashscore:
            flashscore_data = self.fetch_flashscore_data(league)

        # Merge data sources
        enhanced_data = self.merge_data_sources(football_data, flashscore_data)

        # Save enhanced snapshot
        self.save_enhanced_snapshot(league, season, enhanced_data, force)

        logger.info(
            f"[SUCCESS] Enhanced ingestion complete for {league.name} season {season}"
        )
        return True


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Enhanced multi-source data ingestion system."
    )
    parser.add_argument(
        "--league",
        required=True,
        help="League identifier (e.g. la-liga, premier-league).",
    )
    parser.add_argument(
        "--seasons",
        help="Comma-separated list of seasons (e.g. 2021,2022). Overrides --years-back if provided.",
    )
    parser.add_argument(
        "--years-back",
        type=int,
        default=2,
        help="Number of completed seasons to pull counting backwards from the current season.",
    )
    parser.add_argument(
        "--api-key",
        help="Optional explicit football-data API key; otherwise FOOTBALL_DATA_API_KEY env var is used.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Seconds to sleep between API calls when fetching multiple seasons.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing snapshot files instead of skipping them.",
    )
    parser.add_argument(
        "--no-flashscore",
        action="store_true",
        help="Disable FlashScore.es integration even if available.",
    )
    parser.add_argument(
        "--live-only",
        action="store_true",
        help="Only fetch live scores from FlashScore (for real-time updates).",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def resolve_api_key(explicit: str | None) -> str:
    api_key = explicit or os.getenv("FOOTBALL_DATA_API_KEY")
    if not api_key:
        raise SystemExit("FOOTBALL_DATA_API_KEY not set and --api-key not provided.")
    return api_key


def resolve_seasons(raw: str | None, years_back: int) -> list[int]:
    current_year = datetime.utcnow().year
    if raw:
        seasons: list[int] = []
        for chunk in raw.split(","):
            chunk = chunk.strip()
            if not chunk:
                continue
            try:
                seasons.append(int(chunk))
            except ValueError as exc:
                raise SystemExit(
                    f"Invalid season value '{chunk}'. Must be an integer like 2023."
                ) from exc
        return sorted(set(seasons))
    # Football seasons refer to starting year; assume we want completed seasons.
    return [current_year - offset for offset in range(1, years_back + 1)]


def main(argv: Iterable[str] | None = None) -> None:
    args = parse_args(argv)

    # Handle live-only mode
    if args.live_only:
        if not FLASHSCORE_AVAILABLE or FlashScoreScraper is None:
            raise SystemExit(
                "[ERROR] FlashScore integration required for live-only mode but not available."
            )

        logger.info("[LIVE] Fetching live scores only...")
        scraper = FlashScoreScraper()
        live_scores = scraper.get_live_scores()

        print(f"[DATA] Found {len(live_scores)} live matches:")
        for score in live_scores[:10]:  # Show first 10
            print(
                f"  • {score.get('home_team', 'Unknown')} vs {score.get('away_team', 'Unknown')}"
            )

        return

    try:
        league = LeagueConfig.from_key(args.league)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    api_key = resolve_api_key(args.api_key)
    seasons = resolve_seasons(args.seasons, args.years_back)

    # Initialize enhanced ingestion system
    enable_flashscore = FLASHSCORE_AVAILABLE and not args.no_flashscore
    ingestion = EnhancedDataIngestion(api_key, enable_flashscore)

    logger.info(
        f"[START] Starting enhanced ingestion for {len(seasons)} season(s) of {args.league}"
    )
    if enable_flashscore:
        logger.info("[FLASHSCORE] FlashScore.es integration enabled")
    else:
        logger.info("[DATA] Football-Data.org only mode")

    success_count = 0
    for index, season in enumerate(seasons, start=1):
        logger.info(f"[PROCESSING] ({index}/{len(seasons)}) Season {season}")
        try:
            if ingestion.ingest_league_season(league, season, force=args.force):
                success_count += 1
            else:
                logger.error(f"[ERROR] Failed to ingest season {season}")
        except Exception as exc:
            logger.error(f"[ERROR] Unexpected error processing season {season}: {exc}")
            continue

        if index < len(seasons):
            logger.info(f"[WAIT] Waiting {args.delay}s before next season...")
            time.sleep(max(args.delay, 0.0))

    logger.info(
        f"[COMPLETE] Successfully ingested {success_count}/{len(seasons)} seasons for {args.league}"
    )


if __name__ == "__main__":
    main()
