"""Market odds data connector for integrating real bookmaker probabilities."""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from typing import Any, cast

from app.utils.http import safe_request_get


@dataclass
class MarketOdds:
    """Container for normalized market odds information."""

    home_price: float | None
    draw_price: float | None
    away_price: float | None
    probabilities: dict[str, float]
    source: str
    fetched_at: float
    bookmaker_count: int


class OddsDataConnector:
    """Fetches and normalizes odds from The Odds API (or compatible endpoints)."""

    def __init__(self, settings: dict[str, Any] | None = None) -> None:
        settings = settings or {}
        self.base_url = settings.get("base_url", "https://api.the-odds-api.com/v4")
        self.default_sport = settings.get("default_sport", "soccer")
        self.default_market = settings.get("default_market", "h2h")
        self.region = settings.get("region", "uk")
        self.env_key = settings.get("env_key", "ODDS_API_KEY")
        self.cache_ttl = settings.get("cache_ttl", 900)
        self.sport_map: dict[str, str] = settings.get("sport_map", {})

        self.logger = logging.getLogger("odds_connector")
        self._cache: dict[str, dict[str, Any]] = {}

    def get_match_odds(
        self,
        league_slug: str,
        home_team: str,
        away_team: str,
        match_date: str | None = None,
    ) -> MarketOdds | None:
        """Return market odds for a given fixture if available. Handles caching and fallbacks."""
        api_key = os.getenv(self.env_key)
        if not api_key:
            self.logger.debug(
                "[Odds] Skipping fetch: environment key %s missing", self.env_key,
            )
            return None

        cache_key = self._build_cache_key(league_slug, home_team, away_team, match_date)
        cached = self._cache.get(cache_key)
        if cached and time.time() - cached["fetched_at"] <= self.cache_ttl:
            return cast("MarketOdds", cached["payload"])

        sport_key = self._resolve_sport_key(league_slug)
        url = f"{self.base_url}/sports/{sport_key}/odds"
        params = {
            "apiKey": api_key,
            "regions": self.region,
            "markets": self.default_market,
            "oddsFormat": "decimal",
        }

        try:
            response = safe_request_get(
                url, params=params, timeout=10, logger=self.logger,
            )
            response.raise_for_status()
            data = response.json()
        except Exception as exc:  # requests raises multiple exception types
            self.logger.warning(
                "[Odds] Fetch failed for %s vs %s: %s", home_team, away_team, exc,
            )
            return None

        normalized_home = self._normalize_name(home_team)
        normalized_away = self._normalize_name(away_team)

        event = self._match_event(data, normalized_home, normalized_away)
        if not event:
            self.logger.info(
                "[Odds] No matching event found for %s vs %s in league %s",
                home_team,
                away_team,
                league_slug,
            )
            return None

        market = self._extract_market(event)
        if not market:
            self.logger.info(
                "[Odds] H2H market missing for %s vs %s", home_team, away_team,
            )
            return None

        probabilities = self._compute_probabilities(market)
        odds_payload = MarketOdds(
            home_price=market.get("home"),
            draw_price=market.get("draw"),
            away_price=market.get("away"),
            probabilities=probabilities,
            source="the-odds-api",
            fetched_at=time.time(),
            bookmaker_count=market.get("bookmaker_count", 0),
        )

        self._cache[cache_key] = {
            "payload": odds_payload,
            "fetched_at": odds_payload.fetched_at,
        }
        return odds_payload

    # Internal helpers -------------------------------------------------

    def _build_cache_key(
        self, league: str, home: str, away: str, match_date: str | None,
    ) -> str:
        date_part = match_date or "na"
        return f"{league.lower()}::{self._normalize_name(home)}::{self._normalize_name(away)}::{date_part}"

    def _resolve_sport_key(self, league_slug: str) -> str:
        slug = (league_slug or self.default_sport).lower()
        return cast("str", self.sport_map.get(slug, self.default_sport))

    def _normalize_name(self, name: Any) -> str:
        s: str = str(name or "")
        chars: list[str] = []
        for ch in s:
            if ch.isalnum():
                chars.append(ch.lower())
        result: str = "".join(chars)
        return result

    def _match_event(
        self, events: Any, home_norm: str, away_norm: str,
    ) -> dict[str, Any] | None:
        if not isinstance(events, list):
            return None
        for event in events:
            if not isinstance(event, dict):
                continue
            event_home = self._normalize_name(event.get("home_team", ""))
            event_away = self._normalize_name(event.get("away_team", ""))
            if event_home == home_norm and event_away == away_norm:
                return cast("dict[str, Any]", event)
        return None

    def _extract_market(self, event: dict[str, Any]) -> dict[str, Any] | None:
        bookmakers = event.get("bookmakers", [])
        if not bookmakers:
            return None

        bookmaker_count = 0
        best_prices: dict[str, float] = {}
        for bookmaker in bookmakers:
            try:
                markets = bookmaker.get("markets", [])
            except AttributeError:
                continue
            bookmaker_count += 1
            for market in markets:
                if market.get("key") != self.default_market:
                    continue
                outcomes = market.get("outcomes", [])
                for outcome in outcomes:
                    name_norm = self._normalize_name(outcome.get("name", ""))
                    price = outcome.get("price") or outcome.get("odds")
                    try:
                        price = float(price)
                    except (TypeError, ValueError):
                        continue

                    if name_norm in ("draw", "tie"):
                        key = "draw"
                    elif name_norm == self._normalize_name(event.get("home_team", "")):
                        key = "home"
                    elif name_norm == self._normalize_name(event.get("away_team", "")):
                        key = "away"
                    else:
                        continue

                    prev = best_prices.get(key)
                    if prev is None or price < prev:
                        best_prices[key] = price

        if not best_prices:
            return None

        best_prices["bookmaker_count"] = bookmaker_count
        return best_prices

    def _compute_probabilities(self, prices: dict[str, float]) -> dict[str, float]:
        implied: dict[str, float] = {}
        for key in ("home", "draw", "away"):
            price = prices.get(key)
            if price and price > 1.0:
                implied[key] = 1.0 / price
            else:
                implied[key] = 0.0

        total = sum(implied.values())
        if total <= 0:
            return dict.fromkeys(("home", "draw", "away"), 0.0)

        return {key: value / total for key, value in implied.items()}


__all__ = ["MarketOdds", "OddsDataConnector"]
