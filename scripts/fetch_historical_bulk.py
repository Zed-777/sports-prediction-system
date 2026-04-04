#!/usr/bin/env python3
"""Bulk Historical Data Seeder (HIST-001)
=======================================
Fetches all finished matches for the last two seasons from
Football-Data.org, generates pre-match probability predictions
for each, and stores the prediction + actual result pair in
data/historical/*.json.

This is the primary mechanism to build a large real-world
dataset for profitability validation.

Usage
-----
    python scripts/fetch_historical_bulk.py
    python scripts/fetch_historical_bulk.py --leagues premier-league la-liga
    python scripts/fetch_historical_bulk.py --seasons 2024 2023
    python scripts/fetch_historical_bulk.py --dry-run          # test without writes
    python scripts/fetch_historical_bulk.py --resume           # skip already-seeded matches

Requirements
------------
    FOOTBALL_DATA_API_KEY must be set in .env or environment.
    Free Tier key is sufficient (10 calls/min rate limit respected).
    Sign up: https://www.football-data.org/client/register

Output
------
    data/historical/{league}_results.json  (appends new records)
    data/historical/seed_progress.json     (progress tracking for --resume)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

LEAGUE_CONFIG: dict[str, dict] = {
    "premier-league": {"comp": "PL",  "free_tier": True},
    "la-liga":        {"comp": "PD",  "free_tier": True},
    "bundesliga":     {"comp": "BL1", "free_tier": True},
    "serie-a":        {"comp": "SA",  "free_tier": True},
    "ligue-1":        {"comp": "FL1", "free_tier": True},
}

FD_BASE = "https://api.football-data.org/v4"
RATE_LIMIT_DELAY = 7          # seconds between API calls (≤10 calls/min on free tier)
PROGRESS_FILE = _ROOT / "data" / "historical" / "seed_progress.json"


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("hist_seed")


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def _read_env_key(key: str) -> str:
    """Read from environment or .env file."""
    val = os.environ.get(key)
    if val:
        return val
    env_file = _ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith(f"{key}=") and not line.startswith("#"):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def _get(url: str, headers: dict, delay: float = 0.0) -> dict:
    """Throttled GET with basic error handling."""
    if delay:
        time.sleep(delay)
    try:
        resp = requests.get(url, headers=headers, timeout=20)
        resp.raise_for_status()
        return resp.json()
    except requests.HTTPError as exc:
        log.warning(f"HTTP {exc.response.status_code} for {url}")
        if exc.response.status_code == 429:
            log.info("Rate limited — waiting 60 s")
            time.sleep(60)
        return {}
    except Exception as exc:
        log.warning(f"Request error: {exc}")
        return {}


# ---------------------------------------------------------------------------
# Prediction helpers
# ---------------------------------------------------------------------------

def _generate_prediction(match: dict, comp_code: str, predictor: Any) -> dict | None:
    """Call EnhancedPredictor.enhanced_prediction with the match dict.
    Returns the prediction dict, or None on failure.
    """
    try:
        # Suppress the voluminous print output from the predictor
        import contextlib
        import io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            result = predictor.enhanced_prediction(match, comp_code)
        return result
    except Exception as exc:
        log.debug(f"Prediction failed: {exc}")
        return None


def _actual_result(home_score: int | None, away_score: int | None) -> str:
    """Convert score to label."""
    if home_score is None or away_score is None:
        return "unknown"
    if home_score > away_score:
        return "home_win"
    if away_score > home_score:
        return "away_win"
    return "draw"


# ---------------------------------------------------------------------------
# Progress tracking
# ---------------------------------------------------------------------------

def _load_progress() -> set[str]:
    if PROGRESS_FILE.exists():
        try:
            d = json.loads(PROGRESS_FILE.read_text())
            return set(d.get("seeded_ids", []))
        except Exception:
            pass
    return set()


def _save_progress(seeded: set[str]) -> None:
    PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROGRESS_FILE.write_text(
        json.dumps({"seeded_ids": sorted(seeded), "updated_at": datetime.now().isoformat()},
                   indent=2),
    )


# ---------------------------------------------------------------------------
# Historical JSON I/O
# ---------------------------------------------------------------------------

def _load_historical(league: str) -> list[dict]:
    path = _ROOT / "data" / "historical" / f"{league}_results.json"
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return []


def _save_historical(league: str, records: list[dict]) -> None:
    path = _ROOT / "data" / "historical" / f"{league}_results.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(records, indent=2, ensure_ascii=False))


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def seed_league(
    league: str,
    seasons: list[str],
    headers: dict,
    predictor: Any | None,
    seeded: set[str],
    dry_run: bool,
    resume: bool,
    stats: dict,
) -> None:
    config = LEAGUE_CONFIG[league]
    comp = config["comp"]
    historical = _load_historical(league)
    existing_ids = {r.get("match_id") for r in historical}

    for season in seasons:
        url = f"{FD_BASE}/competitions/{comp}/matches?season={season}&status=FINISHED"
        log.info(f"  Fetching {league} season={season} ...")
        data = _get(url, headers, delay=RATE_LIMIT_DELAY)
        matches = data.get("matches", [])
        log.info(f"  -> {len(matches)} finished matches returned")

        for match in matches:
            fd_id = str(match.get("id", ""))
            home = match.get("homeTeam", {}).get("name", "")
            away = match.get("awayTeam", {}).get("name", "")
            date_str = (match.get("utcDate") or "")[:10]
            score_ft = match.get("score", {}).get("fullTime", {})
            home_score = score_ft.get("home") if score_ft else None
            away_score = score_ft.get("away") if score_ft else None

            if not home or not away or not date_str:
                continue
            if home_score is None or away_score is None:
                continue  # Score not available

            # Build a stable match_id
            def _slug(n: str) -> str:
                import re
                return re.sub(r"[^a-z0-9]+", "-", n.lower()).strip("-")

            match_id = f"{_slug(home)}_vs_{_slug(away)}_{date_str}"

            if resume and (fd_id in seeded or match_id in seeded):
                stats["skipped"] += 1
                continue
            if match_id in existing_ids:
                stats["skipped"] += 1
                continue

            # Generate prediction (if predictor loaded)
            pred = None
            if predictor is not None:
                pred = _generate_prediction(match, comp, predictor)

            # Build historical record
            if pred:
                home_p = float(pred.get("home_win_prob") or pred.get("home_win_probability") or 0.33)
                draw_p = float(pred.get("draw_prob") or pred.get("draw_probability") or 0.34)
                away_p = float(pred.get("away_win_prob") or pred.get("away_win_probability") or 0.33)
                confidence = float(pred.get("confidence") or pred.get("prediction_strength") or 0.5)
                data_quality = float(pred.get("data_quality_score") or 0.6)
            else:
                # Fallback: uninformative prior (will still record actual result)
                home_p, draw_p, away_p = 0.40, 0.28, 0.32  # typical home-advantage prior
                confidence = 0.50
                data_quality = 0.50

            record = {
                "match_id":       match_id,
                "fd_match_id":    fd_id,
                "league":         league,
                "season":         season,
                "home_team":      home,
                "away_team":      away,
                "match_date":     date_str,
                "home_win_prob":  round(home_p, 4),
                "draw_prob":      round(draw_p, 4),
                "away_win_prob":  round(away_p, 4),
                "confidence":     round(confidence, 4),
                "data_quality":   round(data_quality, 4),
                "prediction_source": "enhanced_predictor" if pred else "prior_only",
                "actual_result":  _actual_result(home_score, away_score),
                "home_score":     home_score,
                "away_score":     away_score,
                "seeded_at":      datetime.now(UTC).isoformat(),
            }

            if not dry_run:
                historical.append(record)
                existing_ids.add(match_id)
                seeded.add(fd_id)
                seeded.add(match_id)

            stats["added"] += 1
            if stats["added"] % 50 == 0:
                log.info(f"    ... {stats['added']} records added so far")
                if not dry_run:
                    _save_historical(league, historical)
                    _save_progress(seeded)

        # Rate-limit: small pause between season batches
        time.sleep(2)

    if not dry_run:
        _save_historical(league, historical)
    log.info(f"  {league}: {stats['added']} new records ({stats['skipped']} skipped)")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bulk-seed historical match data with predictions and actual results",
    )
    parser.add_argument(
        "--leagues", nargs="+",
        choices=list(LEAGUE_CONFIG.keys()),
        default=list(LEAGUE_CONFIG.keys()),
        help="Leagues to seed (default: all 5)",
    )
    parser.add_argument(
        "--seasons", nargs="+",
        default=["2024", "2023"],
        help="Seasons to fetch e.g. 2024 2023 (default: 2024 2023)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Fetch and predict but do not write to disk",
    )
    parser.add_argument(
        "--resume", action="store_true",
        help="Skip matches already recorded in seed_progress.json",
    )
    parser.add_argument(
        "--no-predictor", action="store_true",
        help="Skip prediction generation; record prior + actual result only (faster)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
    )
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Check API key
    api_key = _read_env_key("FOOTBALL_DATA_API_KEY")
    if not api_key or api_key.startswith("YOUR_") or api_key.startswith("your_"):
        print()
        print("ERROR: FOOTBALL_DATA_API_KEY is not set.")
        print()
        print("  Get a FREE key (no credit card) at:")
        print("    https://www.football-data.org/client/register")
        print()
        print("  Then add it to your .env file:")
        print("    FOOTBALL_DATA_API_KEY=<your key here>")
        print()
        print("  Or set it in PowerShell for this session:")
        print("    $env:FOOTBALL_DATA_API_KEY='<your key here>'")
        print()
        sys.exit(1)

    headers = {"X-Auth-Token": api_key}

    # Load predictor (optional)
    predictor = None
    if not args.no_predictor:
        try:
            import contextlib
            import io
            log.info("Loading EnhancedPredictor ...")
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                from enhanced_predictor import EnhancedPredictor
                predictor = EnhancedPredictor(api_key)
            log.info("Predictor loaded.")
        except Exception as exc:
            log.warning(f"Could not load predictor ({exc}); using prior fallback only")

    # Load resume progress
    seeded = _load_progress() if args.resume else set()

    total_stats = {"added": 0, "skipped": 0}

    log.info(f"Seeding {len(args.leagues)} leagues x {len(args.seasons)} seasons")
    log.info(f"  Leagues : {', '.join(args.leagues)}")
    log.info(f"  Seasons : {', '.join(args.seasons)}")
    log.info(f"  Dry-run : {args.dry_run}")
    log.info(f"  Predictor: {'prior-only' if predictor is None else 'EnhancedPredictor'}")
    log.info("")

    for league in args.leagues:
        per_league = {"added": 0, "skipped": 0}
        seed_league(
            league=league,
            seasons=args.seasons,
            headers=headers,
            predictor=predictor,
            seeded=seeded,
            dry_run=args.dry_run,
            resume=args.resume,
            stats=per_league,
        )
        total_stats["added"] += per_league["added"]
        total_stats["skipped"] += per_league["skipped"]

        if not args.dry_run:
            _save_progress(seeded)

    print()
    print("=" * 56)
    print("  Seeding complete.")
    print(f"  Records added   : {total_stats['added']}")
    print(f"  Records skipped : {total_stats['skipped']}")
    if not args.dry_run:
        print(f"  Progress file   : {PROGRESS_FILE.relative_to(_ROOT)}")
    print("=" * 56)
    print()
    print("Next steps:")
    print("  1. Re-run profitability validation with real data:")
    print("       python scripts/run_profitability_analysis.py \\")
    print("         --profile standard --n-synthetic 0")
    print()


if __name__ == "__main__":
    main()
