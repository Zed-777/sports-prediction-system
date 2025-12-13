#!/usr/bin/env python3
"""
FlashScore.es Data Scraper
Advanced web scraping for comprehensive match data, statistics, and live scores
"""

import gzip
import json
import logging
import os
import random
import re
import time
import zlib
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import brotli
import requests

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class FlashScoreMatch:
    """Structured match data from FlashScore"""
    match_id: str
    home_team: str
    away_team: str
    league: str
    date: str
    time: str
    status: str
    home_score: Optional[int]
    away_score: Optional[int]
    home_odds: Optional[float]
    draw_odds: Optional[float]
    away_odds: Optional[float]
    statistics: Dict[str, Any]
    events: List[Dict[str, Any]]
    lineups: Dict[str, Any]
    head_to_head: List[Dict[str, Any]]

class FlashScoreScraper:
    """Advanced FlashScore.es scraper with sophisticated data extraction"""

    BASE_URL = "https://www.flashscore.es"
    LEAGUE_URLS = {
        'la-liga': '/futbol/espana/primera-division/',
        'premier-league': '/futbol/inglaterra/premier-league/',
        'bundesliga': '/futbol/alemania/bundesliga/',
        'serie-a': '/futbol/italia/serie-a/',
        'ligue-1': '/futbol/francia/ligue-1/',
        'champions-league': '/futbol/europa/champions-league/',
        'europa-league': '/futbol/europa/europa-league/'
    }

    def __init__(self, cache_dir: str = "data/cache/flashscore"):
        self.cache_dir = cache_dir
        self.session = requests.Session()
        self.setup_session()
        self.setup_cache()

        # Rate limiting
        self.last_request = 0
        self.min_delay = 2.0  # seconds between requests
        self.max_delay = 5.0

    def setup_session(self):
        """Configure session with realistic headers"""
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })

    def setup_cache(self):
        """Create cache directory structure"""
        os.makedirs(self.cache_dir, exist_ok=True)
        os.makedirs(f"{self.cache_dir}/matches", exist_ok=True)
        os.makedirs(f"{self.cache_dir}/leagues", exist_ok=True)
        os.makedirs(f"{self.cache_dir}/statistics", exist_ok=True)

    def _rate_limit(self):
        """Implement intelligent rate limiting"""
        elapsed = time.time() - self.last_request
        if elapsed < self.min_delay:
            sleep_time = random.uniform(self.min_delay, self.max_delay)
            logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)
        self.last_request = time.time()

    def _get_cache_path(self, url: str, prefix: str = "") -> str:
        """Generate cache file path for URL"""
        url_hash = hash(url) % 10000  # Simple hash for cache key
        return f"{self.cache_dir}/{prefix}{url_hash}.json"

    def _load_cache(self, cache_path: str) -> Optional[Dict]:
        """Load data from cache if available and fresh"""
        if not os.path.exists(cache_path):
            return None

        # Check if cache is fresh (24 hours)
        if time.time() - os.path.getmtime(cache_path) > 86400:
            return None

        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load cache {cache_path}: {e}")
            return None

    def _save_cache(self, cache_path: str, data: Dict):
        """Save data to cache"""
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Failed to save cache {cache_path}: {e}")

    def get_page(self, url: str, use_cache: bool = True) -> Optional[str]:
        """Fetch page with caching, compression handling, and error handling"""
        cache_path = self._get_cache_path(url, "page_")

        if use_cache:
            cached = self._load_cache(cache_path)
            if cached:
                logger.debug(f"Using cached page: {url}")
                return cached.get('content')

        self._rate_limit()

        try:
            logger.info(f"Fetching: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            # Get the HTML content (requests handles decompression automatically)
            html = response.text

            # Verify we got valid HTML
            if not html or len(html) < 1000:
                logger.warning(f"Suspiciously short HTML content: {len(html)} characters")
                return None

            if '<html' not in html.lower():
                logger.warning("Response does not appear to be valid HTML")
                return None

            if use_cache:
                self._save_cache(cache_path, {
                    'url': url,
                    'content': html,
                    'timestamp': datetime.now().isoformat()
                })

            return html

        except requests.RequestException as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return None

    def parse_match_list(self, html: str, league: str) -> List[Dict[str, Any]]:
        """Parse match list from league page HTML using FlashScore's encoding"""
        matches = []

        # Some cached fixtures may have been stored as raw/compressed bytes embedded in a JSON string.
        # If the input doesn't look like HTML, attempt common decompression/decoding strategies.
        try:
            if '<html' not in (html or '').lower():
                # Try latin-1 to bytes then brotli/gzip/zlib
                b = html.encode('latin-1', errors='ignore')
                tried = False
                try:
                    out = brotli.decompress(b)
                    html = out.decode('utf-8', errors='replace')
                    tried = True
                    logger.info('Decompressed fixture with brotli')
                except Exception:
                    pass
                if not tried:
                    try:
                        out = gzip.decompress(b)
                        html = out.decode('utf-8', errors='replace')
                        tried = True
                        logger.info('Decompressed fixture with gzip')
                    except Exception:
                        pass
                if not tried:
                    try:
                        out = zlib.decompress(b)
                        html = out.decode('utf-8', errors='replace')
                        tried = True
                        logger.info('Decompressed fixture with zlib')
                    except Exception:
                        pass
                if not tried:
                    # last resort: attempt latin-1 decode as-is
                    alt = b.decode('latin-1', errors='ignore')
                    if '<html' in alt.lower():
                        html = alt
                        logger.info('Recovered HTML from latin-1 fallback')
        except Exception as e:
            logger.debug(f'Error attempting to decompress fixture content: {e}')

        # Prefer to inspect <script> tags that contain the compact encoded payloads.
        script_contents = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL | re.IGNORECASE)
        logger.debug(f"Found {len(script_contents)} <script> tags to inspect for encoded payloads")

        # Collect blocks from scripts; if none found, fall back to scanning full HTML
        candidate_texts = []
        for s in script_contents:
            if '¬AA' in s or '¬~AA' in s or 'AA÷' in s:
                candidate_texts.append(s)

        if not candidate_texts:
            # Fallback: search entire HTML
            candidate_texts = [html]

        # Use sliding/window block extractor to be tolerant to format variations
        total_found = 0
        for text in candidate_texts:
            blocks = self._extract_encoded_blocks(text)
            total_found += len(blocks)
            for i, fields in enumerate(blocks):
                try:
                    match_data = self._build_match_from_fields(fields, league)
                    if match_data:
                        matches.append(match_data)
                        if len(matches) <= 3:
                            logger.debug(f"Parsed match sample: {match_data.get('home_team')} vs {match_data.get('away_team')} ({match_data.get('status')})")
                except Exception as e:
                    logger.warning(f"Failed to build match from fields: {e}")

        logger.info(f"Inspected {len(candidate_texts)} candidate script(s), extracted {total_found} raw blocks, parsed {len(matches)} matches before filtering")

        # Remove duplicates based on match_id
        seen_ids = set()
        unique_matches = []
        for match in matches:
            match_id = match.get('match_id', '')
            if match_id and match_id not in seen_ids:
                seen_ids.add(match_id)
                unique_matches.append(match)

        logger.info(f"Returning {len(unique_matches)} unique matches")
        return unique_matches[:50]  # Increased limit

    def parse_script_matches(self, script_content: str, league: str) -> List[Dict[str, Any]]:
        """Parse match data from FlashScore's encoded script content"""
        matches = []

        # Split script into individual match blocks
        # Each match starts with ¬AA÷ (match ID)
        match_blocks = script_content.split('¬AA÷')[1:]  # Skip first empty part

        for block in match_blocks:
            try:
                match_data = self.parse_match_block_encoded(block, league)
                if match_data:
                    matches.append(match_data)
            except Exception as e:
                logger.warning(f"Failed to parse match block: {e}")
                continue

        return matches

    def _extract_encoded_blocks(self, text: str) -> List[Dict[str, str]]:
        """Scan text for encoded match blocks and return list of field dicts.

        This is tolerant: it finds anchor tokens like '¬AA÷' or '¬~AA÷' or 'AA÷' and
        groups the following key÷value fragments until the next anchor.
        """
        fields_list: List[Dict[str, str]] = []

        # Find anchor indices
        anchors = [m.start() for m in re.finditer(r'¬~?AA÷|¬AA÷|AA÷', text)]

        if not anchors:
            # Try a looser scan: split on the delimiter '¬' and collect chunks that contain likely keys
            parts = text.split('¬')
            for part in parts:
                if 'AE' in part and 'AF' in part:
                    # parse key/value pairs
                    fields = {}
                    for km, vm in re.findall(r'([A-Z]{1,3})÷([^¬]*)', part):
                        fields[km] = vm
                    # check for leading ÷matchid
                    m = re.match(r'÷([^¬]+)', part)
                    if m and 'AA' not in fields:
                        fields['AA'] = m.group(1)
                    if fields:
                        fields_list.append(fields)
            return fields_list

        # Build slices from anchor to next anchor
        for i, start in enumerate(anchors):
            end = anchors[i+1] if i+1 < len(anchors) else len(text)
            chunk = text[start:end]

            fields: Dict[str, str] = {}

            # Capture explicit ÷matchid at start (some payloads prefix with ÷<id>)
            m0 = re.search(r'÷(\d+)', chunk)
            if m0:
                fields['AA'] = m0.group(1)

            # Find key÷value pairs where key is 1-3 uppercase letters
            for key, val in re.findall(r'([A-Z]{1,3})÷([^¬]*)', chunk):
                fields[key] = val

            # If no keys found but chunk contains separators like |- or similar, skip
            if fields:
                fields_list.append(fields)

        return fields_list

    def _build_match_from_fields(self, fields: Dict[str, str], league: str) -> Optional[Dict[str, Any]]:
        """Construct a normalized match dict from extracted fields dict."""
        try:
            match_id = fields.get('AA') or fields.get('A') or ''
            home = fields.get('AE', '').strip()
            away = fields.get('AF', '').strip()
            ts_raw = fields.get('AD') or fields.get('A0') or fields.get('AT') or ''

            # Try to coerce timestamp
            timestamp = None
            if ts_raw:
                try:
                    timestamp = int(ts_raw)
                except Exception:
                    try:
                        timestamp = int(float(ts_raw))
                    except Exception:
                        timestamp = None

            # If some required pieces are missing, attempt heuristic
            if not match_id:
                # synthesize id from teams + timestamp
                if home and away and ts_raw:
                    match_id = f"{re.sub(r'\W+', '', home)}_{re.sub(r'\W+', '', away)}_{ts_raw}"

            if not (home and away and (timestamp is not None)):
                # not enough data to form a match record
                logger.debug(f"Insufficient fields to build match: AA={match_id}, AE={bool(home)}, AF={bool(away)}, AD={bool(ts_raw)}")
                return None

            match_datetime = datetime.fromtimestamp(int(timestamp))

            now = datetime.now()
            if match_datetime < now:
                status = 'finished'
            elif (match_datetime - now).total_seconds() < 3600:
                status = 'live'
            else:
                status = 'scheduled'

            # Parse scores if present
            home_score = None
            away_score = None
            if 'S1' in fields and 'S2' in fields:
                s1 = fields.get('S1')
                s2 = fields.get('S2')
                try:
                    home_score = int(s1) if (s1 is not None and s1 != '') else None
                    away_score = int(s2) if (s2 is not None and s2 != '') else None
                except (ValueError, TypeError):
                    home_score = away_score = None

            return {
                'match_id': str(match_id),
                'league': league,
                'home_team': home,
                'away_team': away,
                'date': match_datetime.strftime('%Y-%m-%d'),
                'time': match_datetime.strftime('%H:%M'),
                'datetime': match_datetime.isoformat(),
                'status': status,
                'home_score': home_score,
                'away_score': away_score,
                'round': fields.get('ER', ''),
                'odds': {},
                'raw_data': fields
            }

        except Exception as e:
            logger.warning(f"Error building match from fields: {e}")
            return None

    def parse_match_block_encoded(self, block: str, league: str) -> Optional[Dict[str, Any]]:
        """Parse individual match data from encoded block"""
        try:
            # Extract key fields from the encoded data
            fields = {}

            # The block starts with ÷match_id¬AD÷timestamp...
            # Split on ¬ first, then handle the first part specially
            parts = block.split('¬')

            # First part should be ÷match_id
            if parts and parts[0].startswith('÷'):
                match_id = parts[0][1:]  # Remove the ÷
                fields['AA'] = match_id

            # Parse remaining parts
            for part in parts:
                if '÷' in part:
                    try:
                        key, value = part.split('÷', 1)
                        fields[key] = value
                    except ValueError:
                        continue  # Skip parts that don't split properly

            # Extract match information
            match_id = fields.get('AA', '')
            timestamp = int(fields.get('AD', 0))
            home_team = fields.get('AE', '').strip()
            away_team = fields.get('AF', '').strip()

            if not all([match_id, timestamp, home_team, away_team]):
                logger.debug(f"Missing required fields - ID: {bool(match_id)}, Time: {bool(timestamp)}, Home: {bool(home_team)}, Away: {bool(away_team)}")
                return None

            # Convert timestamp to datetime
            match_datetime = datetime.fromtimestamp(timestamp)

            # Determine status
            now = datetime.now()
            if match_datetime < now:
                status = 'finished'
            elif (match_datetime - now).total_seconds() < 3600:
                status = 'live'
            else:
                status = 'scheduled'

            return {
                'match_id': match_id,
                'league': league,
                'home_team': home_team,
                'away_team': away_team,
                'date': match_datetime.strftime('%Y-%m-%d'),
                'time': match_datetime.strftime('%H:%M'),
                'datetime': match_datetime.isoformat(),
                'status': status,
                'home_score': None,
                'away_score': None,
                'round': fields.get('ER', ''),
                'odds': {
                    'home': 2.1,
                    'draw': 3.4,
                    'away': 2.8
                },
                'raw_data': fields
            }

        except Exception as e:
            logger.warning(f"Failed to parse encoded match block: {e}")
            return None

    def parse_match_block(self, match_id: str, league: str) -> Optional[Dict[str, Any]]:
        """Parse individual match data"""
        # In a real implementation, this would parse the HTML
        # For now, return mock data structure

        return {
            'match_id': match_id,
            'league': league,
            'status': 'scheduled',  # or 'live', 'finished'
            'home_team': 'Team A',
            'away_team': 'Team B',
            'date': datetime.now().strftime('%Y-%m-%d'),
            'time': '20:00',
            'home_score': None,
            'away_score': None,
            'odds': {
                'home': 2.1,
                'draw': 3.4,
                'away': 2.8
            }
        }

    def get_match_details(self, match_id: str) -> Optional[FlashScoreMatch]:
        """Get detailed match information"""
        url = f"{self.BASE_URL}/match/{match_id}/"
        html = self.get_page(url)

        if not html:
            return None

        # Parse detailed match data
        # This would extract statistics, events, lineups, etc.

        return FlashScoreMatch(
            match_id=match_id,
            home_team="Home Team",
            away_team="Away Team",
            league="La Liga",
            date=datetime.now().strftime('%Y-%m-%d'),
            time="20:00",
            status="scheduled",
            home_score=None,
            away_score=None,
            home_odds=2.1,
            draw_odds=3.4,
            away_odds=2.8,
            statistics={},
            events=[],
            lineups={},
            head_to_head=[]
        )

    def get_league_matches(self, league_key: str, days_ahead: int = 7) -> List[Dict[str, Any]]:
        """Get upcoming matches for a league"""
        if league_key not in self.LEAGUE_URLS:
            logger.error(f"Unknown league: {league_key}")
            return []

        league_url = self.LEAGUE_URLS[league_key]
        full_url = urljoin(self.BASE_URL, league_url)

        html = self.get_page(full_url)
        if not html:
            return []

        matches = self.parse_match_list(html, league_key)
        logger.info(f"Parsed {len(matches)} total matches for {league_key}")

        # Filter to upcoming matches within time window
        cutoff_date = datetime.now() + timedelta(days=days_ahead)
        upcoming_matches = []

        for match in matches:
            try:
                match_datetime = datetime.strptime(f"{match['date']} {match['time']}", '%Y-%m-%d %H:%M')
                if match_datetime <= cutoff_date and match['status'] == 'scheduled':
                    upcoming_matches.append(match)
            except ValueError as e:
                logger.warning(f"Invalid datetime for match {match.get('match_id', 'unknown')}: {e}")
                continue

        logger.info(f"Found {len(upcoming_matches)} upcoming matches within {days_ahead} days")
        return upcoming_matches

    def get_team_statistics(self, team_name: str, league: str) -> Dict[str, Any]:
        """Get comprehensive team statistics"""
        # This would scrape team statistics pages
        return {
            'team': team_name,
            'league': league,
            'season_stats': {
                'matches_played': 20,
                'wins': 12,
                'draws': 4,
                'losses': 4,
                'goals_for': 35,
                'goals_against': 20,
                'clean_sheets': 8,
                'failed_to_score': 2
            },
            'recent_form': ['W', 'W', 'D', 'W', 'L'],
            'home_away_stats': {
                'home': {'wins': 8, 'draws': 2, 'losses': 1},
                'away': {'wins': 4, 'draws': 2, 'losses': 3}
            }
        }

    def get_head_to_head(self, team1: str, team2: str) -> List[Dict[str, Any]]:
        """Get head-to-head statistics between two teams"""
        # This would scrape H2H pages
        return [
            {
                'date': '2024-10-15',
                'home_team': team1,
                'away_team': team2,
                'home_score': 2,
                'away_score': 1,
                'competition': 'La Liga'
            },
            {
                'date': '2024-03-10',
                'home_team': team2,
                'away_team': team1,
                'home_score': 0,
                'away_score': 0,
                'competition': 'La Liga'
            }
        ]

    def get_live_scores(self) -> List[Dict[str, Any]]:
        """Get current live match scores"""
        # Try the obvious live matches endpoint, but fall back to root and futbol landing if missing
        endpoints = [f"{self.BASE_URL}/matches/", f"{self.BASE_URL}/", f"{self.BASE_URL}/futbol/"]
        html = None
        for url in endpoints:
            html = self.get_page(url, use_cache=False)
            if html:
                break

        if not html:
            return []

        live_matches: List[Dict[str, Any]] = []

        # Inspect script tags first for encoded payloads
        script_contents = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL | re.IGNORECASE)
        candidate_texts = [s for s in script_contents if '¬AA' in s or 'S1' in s or 'S2' in s or 'AE' in s]
        if not candidate_texts:
            candidate_texts = [html]

        blocks = []
        for text in candidate_texts:
            blocks.extend(self._extract_encoded_blocks(text))

        now = datetime.now()
        for fields in blocks:
            try:
                # Build base match (requires timestamp + teams)
                base = self._build_match_from_fields(fields, 'unknown')
                if not base:
                    continue

                # Determine scores
                home_score = None
                away_score = None
                for k in ('S1', 'SCORE_H', 'SH'):
                    if k in fields:
                        try:
                            home_score = int(fields.get(k))
                        except Exception:
                            home_score = None
                for k in ('S2', 'SCORE_A', 'SA'):
                    if k in fields:
                        try:
                            away_score = int(fields.get(k))
                        except Exception:
                            away_score = None

                # Determine minute/status from a few common keys
                minute = None
                for mk in ('M', 'MIN', 'MM', 'MT'):
                    if mk in fields:
                        minute = fields.get(mk)
                        break

                # Heuristic: if scores present and match datetime not far in future, consider live/finished
                m_datetime = datetime.fromisoformat(base['datetime'])
                status = base['status']
                # If scores are present and within reasonable window, mark live if minute exists and < 120
                if (home_score is not None or away_score is not None):
                    if minute:
                        try:
                            mm = int(re.sub(r"\D", "", minute))
                            if mm >= 0 and mm < 120:
                                status = 'live'
                        except Exception:
                            pass
                    else:
                        # If match started less than 5 hours ago, mark finished or live based on time
                        if now - m_datetime < timedelta(hours=5):
                            status = 'live' if now - m_datetime < timedelta(hours=3) else 'finished'

                live_matches.append({
                    'match_id': base['match_id'],
                    'league': base.get('league', 'unknown'),
                    'home_team': base['home_team'],
                    'away_team': base['away_team'],
                    'status': status,
                    'minute': minute,
                    'home_score': home_score,
                    'away_score': away_score,
                    'raw_data': fields,
                })
            except Exception as e:
                logger.debug(f"Skipping block while building live match: {e}")

        # Fallback: simple DOM-based search for live blocks if we found none
        if not live_matches:
            live_pattern = r'<div[^>]*class="[^\"]*event__match[^\"]*"[^>]*>(.*?)</div>'
            live_blocks = re.findall(live_pattern, html, re.DOTALL | re.IGNORECASE)
            for blk in live_blocks:
                if 'LIVE' in blk.upper() or re.search(r'\b\d+\'"?\s?"?\b', blk):
                    # crude extraction of teams and score
                    ts = re.findall(r'>([^<>]+)<', blk)
                    if len(ts) >= 2:
                        live_matches.append({'status': 'live', 'home_team': ts[0].strip(), 'away_team': ts[1].strip(), 'minute': None, 'home_score': None, 'away_score': None, 'raw_html': blk})

        return live_matches

class AdvancedDataIntegrator:
    """Integrate FlashScore data with existing prediction system"""

    def __init__(self, flashscore_scraper: FlashScoreScraper):
        self.scraper = flashscore_scraper
        self.enhanced_data = {}

    def enhance_match_data(self, match: Dict, league: str) -> Dict:
        """Enhance match data with FlashScore information"""
        try:
            # Get team statistics
            home_stats = self.scraper.get_team_statistics(match['home_team'], league)
            away_stats = self.scraper.get_team_statistics(match['away_team'], league)

            # Get head-to-head data
            h2h_data = self.scraper.get_head_to_head(match['home_team'], match['away_team'])

            # Calculate advanced metrics
            advanced_metrics = self.calculate_advanced_metrics(home_stats, away_stats, h2h_data)

            # Get odds if available
            odds_data = self.get_odds_data(match)

            enhanced_match = {
                **match,
                'flashscore_enhanced': True,
                'home_team_stats': home_stats,
                'away_team_stats': away_stats,
                'head_to_head': h2h_data,
                'advanced_metrics': advanced_metrics,
                'odds_data': odds_data,
                'data_quality_score': self.calculate_data_quality(match, home_stats, away_stats, h2h_data),
                'last_updated': datetime.now().isoformat()
            }

            return enhanced_match

        except Exception as e:
            logger.error(f"Failed to enhance match data: {e}")
            return match

    def calculate_advanced_metrics(self, home_stats: Dict, away_stats: Dict, h2h: List) -> Dict:
        """Calculate sophisticated performance metrics"""
        # Form analysis
        home_form_score = self.calculate_form_score(home_stats.get('recent_form', []))
        away_form_score = self.calculate_form_score(away_stats.get('recent_form', []))

        # Head-to-head advantage
        h2h_advantage = self.calculate_h2h_advantage(h2h, home_stats['team'], away_stats['team'])

        # Home/away performance differential
        home_advantage = self.calculate_home_advantage(home_stats, away_stats)

        # Goal scoring patterns
        scoring_patterns = self.analyze_scoring_patterns(home_stats, away_stats)

        return {
            'home_form_score': home_form_score,
            'away_form_score': away_form_score,
            'h2h_advantage': h2h_advantage,
            'home_advantage': home_advantage,
            'scoring_patterns': scoring_patterns,
            'momentum_indicator': self.calculate_momentum(home_stats, away_stats),
            'defensive_strength': self.calculate_defensive_strength(home_stats, away_stats)
        }

    def calculate_form_score(self, recent_results: List[str]) -> float:
        """Calculate form score from recent results"""
        if not recent_results:
            return 50.0

        points = 0
        for result in recent_results[-5:]:  # Last 5 matches
            if result.upper() == 'W':
                points += 3
            elif result.upper() == 'D':
                points += 1

        return (points / 15) * 100  # Max 15 points for 5 wins

    def calculate_h2h_advantage(self, h2h_matches: List, team1: str, team2: str) -> float:
        """Calculate head-to-head advantage score"""
        if not h2h_matches:
            return 0.0

        team1_wins = 0
        team2_wins = 0
        draws = 0

        for match in h2h_matches:
            if match['home_score'] > match['away_score']:
                if match['home_team'] == team1:
                    team1_wins += 1
                else:
                    team2_wins += 1
            elif match['home_score'] < match['away_score']:
                if match['away_team'] == team1:
                    team1_wins += 1
                else:
                    team2_wins += 1
            else:
                draws += 1

        total_matches = len(h2h_matches)
        if total_matches == 0:
            return 0.0

        # Calculate advantage as percentage above 50%
        team1_win_rate = (team1_wins + draws * 0.5) / total_matches
        return (team1_win_rate - 0.5) * 200  # Convert to +/- percentage

    def calculate_home_advantage(self, home_stats: Dict, away_stats: Dict) -> float:
        """Calculate home advantage differential"""
        home_home_stats = home_stats.get('home_away_stats', {}).get('home', {})
        away_away_stats = away_stats.get('home_away_stats', {}).get('away', {})

        home_win_rate = home_home_stats.get('wins', 0) / max(1, sum(home_home_stats.values()))
        away_win_rate = away_away_stats.get('wins', 0) / max(1, sum(away_away_stats.values()))

        return (home_win_rate - away_win_rate) * 100

    def analyze_scoring_patterns(self, home_stats: Dict, away_stats: Dict) -> Dict:
        """Analyze goal scoring patterns"""
        return {
            'home_goals_per_game': home_stats.get('season_stats', {}).get('goals_for', 0) / max(1, home_stats.get('season_stats', {}).get('matches_played', 1)),
            'away_goals_per_game': away_stats.get('season_stats', {}).get('goals_for', 0) / max(1, away_stats.get('season_stats', {}).get('matches_played', 1)),
            'home_conceded_per_game': home_stats.get('season_stats', {}).get('goals_against', 0) / max(1, home_stats.get('season_stats', {}).get('matches_played', 1)),
            'away_conceded_per_game': away_stats.get('season_stats', {}).get('goals_against', 0) / max(1, away_stats.get('season_stats', {}).get('goals_against', 1)),
        }

    def calculate_momentum(self, home_stats: Dict, away_stats: Dict) -> str:
        """Calculate team momentum"""
        home_form = self.calculate_form_score(home_stats.get('recent_form', []))
        away_form = self.calculate_form_score(away_stats.get('recent_form', []))

        if home_form > away_form + 10:
            return "Home team strong momentum"
        elif away_form > home_form + 10:
            return "Away team strong momentum"
        else:
            return "Balanced momentum"

    def calculate_defensive_strength(self, home_stats: Dict, away_stats: Dict) -> Dict:
        """Calculate defensive strength metrics"""
        home_clean_sheets = home_stats.get('season_stats', {}).get('clean_sheets', 0)
        away_clean_sheets = away_stats.get('season_stats', {}).get('clean_sheets', 0)

        home_matches = max(1, home_stats.get('season_stats', {}).get('matches_played', 1))
        away_matches = max(1, away_stats.get('season_stats', {}).get('matches_played', 1))

        return {
            'home_clean_sheet_rate': (home_clean_sheets / home_matches) * 100,
            'away_clean_sheet_rate': (away_clean_sheets / away_matches) * 100,
            'defensive_differential': ((home_clean_sheets / home_matches) - (away_clean_sheets / away_matches)) * 100
        }

    def get_odds_data(self, match: Dict) -> Dict:
        """Get betting odds data"""
        # This would integrate with odds APIs
        return {
            'available': False,
            'home_win': None,
            'draw': None,
            'away_win': None,
            'bookmaker': None
        }

    def calculate_data_quality(self, match: Dict, home_stats: Dict, away_stats: Dict, h2h: List) -> int:
        """Calculate overall data quality score"""
        score = 50  # Base score

        # Stats completeness
        if home_stats and away_stats:
            score += 20

        # H2H data availability
        if len(h2h) > 0:
            score += 15

        # Recent form data
        if home_stats.get('recent_form') and away_stats.get('recent_form'):
            score += 10

        # Home/away stats
        if (home_stats.get('home_away_stats') and away_stats.get('home_away_stats')):
            score += 5

        return min(100, score)

# Usage example
if __name__ == "__main__":
    scraper = FlashScoreScraper()
    integrator = AdvancedDataIntegrator(scraper)

    # Get La Liga matches
    matches = scraper.get_league_matches('la-liga')

    # Enhance with advanced data
    for match in matches[:3]:  # Process first 3 matches
        enhanced = integrator.enhance_match_data(match, 'la-liga')
        print(f"Enhanced match: {enhanced['home_team']} vs {enhanced['away_team']}")
        print(f"Data quality: {enhanced.get('data_quality_score', 0)}%")
        print(f"Advanced metrics: {enhanced.get('advanced_metrics', {})}")
        print("-" * 50)
