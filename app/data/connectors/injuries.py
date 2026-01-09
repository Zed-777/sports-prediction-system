"""Injuries connector

Provides a unified `InjuriesConnector.fetch_injuries(team_id, team_name=None)` method.
Primary source: API-Football (RapidAPI)
Fallbacks: FlashScore (via `flashscore_scraper.AdvancedDataIntegrator` / `FlashScoreScraper`)

Caching and 429 handling are implemented to avoid repeated rate limits.
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime
from typing import List, Optional

from app.types import JSONDict
from app.utils.http import safe_request_get
from app.utils import state_sync

# Optional FlashScore integration
try:
    from flashscore_scraper import FlashScoreScraper
    FLASHSCORE_AVAILABLE = True
except Exception:
    FlashScoreScraper = None  # type: ignore
    FLASHSCORE_AVAILABLE = False


class InjuriesConnector:
    def __init__(self, cache_dir: str = "data/cache"):
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)
        self._host = "api-football-v1.p.rapidapi.com"

    def _cache_path(self, team_id: int, season: Optional[int] = None) -> str:
        year = season or datetime.now().year
        return os.path.join(self.cache_dir, f"injuries_{team_id}_{year}.json")

    def fetch_injuries(self, team_id: int, team_name: Optional[str] = None, season: Optional[int] = None) -> Optional[List[JSONDict]]:
        """Fetch injury list for `team_id`.

        Returns a list of injury dicts compatible with `_analyze_injury_data`'s expected format,
        or None if no data is available.
        """
        # 1. Try cache
        cache_file = self._cache_path(team_id, season=season)
        try:
            if os.path.exists(cache_file):
                with open(cache_file, "r", encoding="utf-8") as f:
                    payload = json.load(f)
                ts = float(payload.get("timestamp", 0))
                # Use 24h TTL by default
                if time.time() - ts < 86400:
                    return payload.get("data")
        except Exception:
            pass

        # 2. Try API-Football (RapidAPI)
        api_key = os.getenv("API_FOOTBALL_KEY")
        if api_key:
            try:
                url = f"https://{self._host}/v3/injuries"
                headers = {
                    "X-RapidAPI-Key": api_key,
                    "X-RapidAPI-Host": self._host,
                }
                params = {"team": str(team_id), "season": str(season or datetime.now().year)}
                r = safe_request_get(url, headers=headers, params=params, timeout=10, retries=3, backoff=0.5)
                if r.status_code == 200:
                    data = r.json()
                    parsed = data.get("response") or data
                    # Cache
                    try:
                        with open(cache_file, "w", encoding="utf-8") as f:
                            json.dump({"timestamp": time.time(), "data": parsed}, f)
                    except Exception:
                        pass
                    return parsed
                elif r.status_code == 429:
                    # Persist disable flag to avoid repeated 429s
                    ttl = 900  # default 15 minutes
                    disabled_until = time.time() + ttl
                    try:
                        state_sync.set_disabled_flag(self._host, "/v3/injuries", disabled_until, reason="429")
                    except Exception:
                        pass
                    try:
                        with open(os.path.join(self.cache_dir, "injuries_disabled_until.json"), "w", encoding="utf-8") as f:
                            json.dump({"disabled_until": disabled_until, "reason": "429"}, f)
                    except Exception:
                        pass
                else:
                    # Other non-200: fall through to fallbacks
                    pass
            except Exception:
                # On errors, fall through to fallback methods
                pass

        # 3. Fallback to FlashScore parsing if available and team_name provided
        if FLASHSCORE_AVAILABLE and team_name:
            try:
                scraper = FlashScoreScraper()
                # We attempt to find recent matches involving the team and scan match details for injury mentions
                # Use `get_league_matches` or `parse_match_list` is heavier; as a simple fallback, search recent matches
                # We will inspect next 7 days for mentions
                league_matches = []
                # Try to use the get_match_details when we have a match_id; otherwise try parsing team page
                # Best-effort: use team name to find candidate matches from a few league pages
                # For simplicity, call get_match_details for a few likely matches is not implemented; instead, attempt to fetch team page
                # Team page url heuristic
                team_slug = team_name.lower().replace(" ", "-")
                # Try a couple of common country directories (es, en) and fallback to root
                urls = [f"https://www.flashscore.es/team/{team_slug}/", f"https://www.flashscore.com/team/{team_slug}/"]
                injuries_found: List[JSONDict] = []
                for url in urls:
                    html = scraper.get_page(url, use_cache=True)
                    if not html:
                        continue

                    # If the HTML contains likely injury phrases, try to extract structured info
                    parsed_from_html = self._parse_injuries_from_team_html(html, url)
                    if parsed_from_html:
                        injuries_found.extend(parsed_from_html)

                # Try Transfermarkt page if nothing found and team_name is available
                if not injuries_found and team_name:
                    try:
                        tm_slug = team_name.lower().replace(" ", "-")
                        tm_url = f"https://www.transfermarkt.com/{tm_slug}/verletzungen/verein/"
                        tm_html = scraper.get_page(tm_url, use_cache=True)
                        if tm_html:
                            tm_parsed = self._parse_transfermarkt_html(tm_html, tm_url)
                            if tm_parsed:
                                injuries_found.extend(tm_parsed)
                    except Exception:
                        pass

                if injuries_found:
                    # Return normalized structure
                    try:
                        with open(cache_file, "w", encoding="utf-8") as f:
                            json.dump({"timestamp": time.time(), "data": injuries_found}, f)
                    except Exception:
                        pass
                    return injuries_found
            except Exception:
                pass

        # 4. No data available
        return None

    def _parse_injuries_from_team_html(self, html: str, source_url: str) -> List[JSONDict]:
        """Extract injury instances from team HTML using heuristics.

        Returns a list of dicts: {'player': {'name': ..}, 'reason': .., 'status': .., 'estimated_return': .., 'provenance': {'source': url, 'snippet': ..}}
        """
        import re

        results: List[JSONDict] = []
        text = re.sub(r"\s+", " ", html)
        lowered = text.lower()
        # Sentences likely to contain injury info
        candidate_sentences = []
        for sep in (".", ";", "\n"):
            parts = [p.strip() for p in text.split(sep) if p.strip()]
            for p in parts:
                low = p.lower()
                if any(k in low for k in ("injur", "out", "suspend", "doubtful", "expected return")):
                    candidate_sentences.append(p)

        # Deduplicate
        candidate_sentences = list(dict.fromkeys(candidate_sentences))

        name_re = re.compile(r"([A-Z][A-Za-z\.\'\-]+(?:\s+[A-Z][A-Za-z\.\'\-]+)+)")
        reason_re = re.compile(r"with\s+([a-zA-Z\s\-]+injury)", re.IGNORECASE)
        exp_return_re = re.compile(r"expected return\s*(?:on\s*)?([0-9]{4}-[0-9]{2}-[0-9]{2})", re.IGNORECASE)

        for sent in candidate_sentences:
            s_low = sent.lower()
            # find name
            name = None
            m_name = name_re.search(sent)
            if m_name:
                name = m_name.group(1).strip()
            # find reason
            reason = None
            m_reason = reason_re.search(sent)
            if m_reason:
                reason = m_reason.group(1).strip()
            # find estimated return
            est = None
            m_est = exp_return_re.search(sent)
            if m_est:
                est = m_est.group(1)
            else:
                # Try searching the whole HTML text for a nearby date if not found in the sentence
                m_est2 = exp_return_re.search(text)
                if m_est2:
                    est = m_est2.group(1)

            if name or reason or est:
                results.append({
                    "player": {"name": name or "Unknown"},
                    "reason": reason or "site_mention",
                    "status": "injury",
                    "estimated_return": est,
                    "provenance": {"source": source_url, "snippet": sent.strip()},
                })

        return results

    def _parse_transfermarkt_html(self, html: str, source_url: str) -> List[JSONDict]:
        """Parse Transfermarkt injury list HTML (very small heuristic parser suitable for fixtures)."""
        import re

        results: List[JSONDict] = []
        # Look for list items containing player name and date
        for m in re.finditer(r"<li>(.*?)</li>", html, re.IGNORECASE | re.DOTALL):
            item = re.sub(r"\s+", " ", m.group(1)).strip()
            # e.g., 'Y. Player – hamstring injury (out until 2026-02-01)'
            name_match = re.match(r"([A-Z][A-Za-z\.\'\-]+(?:\s+[A-Z][A-Za-z\.\'\-]+)*)", item)
            reason_match = re.search(r"([a-zA-Z\s\-]+injury)", item, re.IGNORECASE)
            date_match = re.search(r"(20[0-9]{2}-[0-9]{2}-[0-9]{2})", item)
            name = name_match.group(1).strip() if name_match else "Unknown"
            reason = reason_match.group(1).strip() if reason_match else "site_mention"
            est = date_match.group(1) if date_match else None
            results.append({
                "player": {"name": name},
                "reason": reason,
                "status": "injury",
                "estimated_return": est,
                "provenance": {"source": source_url, "snippet": item},
            })

        return results