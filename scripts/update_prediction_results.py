"""
Update Prediction Results (CC-002 / TODO #48)
============================================
Fetches actual match results for pending predictions tracked in the
PredictionTracker SQLite database and updates accuracy metrics.

Designed to be called daily (e.g., from fetch-results.yml) after matches
have concluded.

Usage:
    python scripts/update_prediction_results.py [--days-back N] [--dry-run] [--verbose]

Exit codes:
    0 - success (including zero pending predictions)
    1 - unexpected error
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Ensure repo root is on the path
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def _setup_logging(verbose: bool) -> logging.Logger:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    return logging.getLogger("update_prediction_results")


def _fetch_result_from_api(
    match_id: int,
    home_team: str,
    away_team: str,
    league: str,
    match_date: str,
    api_key: str,
    logger: logging.Logger,
) -> tuple[int, int] | None:
    """
    Try to fetch the actual final score from Football-Data.org for a given match.

    Returns (home_goals, away_goals) tuple or None if result not found.
    """
    try:
        import requests  # type: ignore

        headers = {"X-Auth-Token": api_key}

        # Attempt to retrieve the specific match by its Football-Data match ID
        url = f"https://api.football-data.org/v4/matches/{match_id}"
        resp = requests.get(url, headers=headers, timeout=15)

        if resp.status_code == 200:
            data = resp.json()
            score = data.get("score", {}).get("fullTime", {})
            home = score.get("home") if score.get("home") is not None else score.get("homeTeam")
            away = score.get("away") if score.get("away") is not None else score.get("awayTeam")
            if home is not None and away is not None:
                logger.debug(
                    f"  [API] {home_team} {home}-{away} {away_team} (match_id={match_id})"
                )
                return int(home), int(away)
        elif resp.status_code == 429:
            logger.warning("  [API] Rate-limited by Football-Data.org; backing off")
        else:
            logger.debug(f"  [API] Match {match_id} not found (HTTP {resp.status_code})")

    except Exception as exc:
        logger.debug(f"  [API] Error fetching match {match_id}: {exc}")

    return None


def run(days_back: int = 7, dry_run: bool = False, verbose: bool = False) -> int:
    """Main entry point. Returns count of results updated."""
    logger = _setup_logging(verbose)

    try:
        from app.models.prediction_tracker import PredictionTracker
    except ImportError as exc:
        logger.error(f"Cannot import PredictionTracker: {exc}")
        return 0

    api_key = os.getenv("FOOTBALL_DATA_API_KEY", "")
    if not api_key:
        logger.warning(
            "FOOTBALL_DATA_API_KEY not set — result fetching will be skipped; "
            "only manual updates via record_result() will work."
        )

    tracker = PredictionTracker()  # default db path: data/predictions.db
    pending = tracker.get_pending_results(limit=100)

    # Filter to predictions for matches within days_back
    cutoff = (datetime.now() - timedelta(days=days_back)).isoformat()
    pending = [p for p in pending if p.get("match_date", "9999") >= cutoff]

    logger.info(
        f"Found {len(pending)} predictions pending results "
        f"(matches up to {days_back} days ago)"
    )

    updated = 0
    failed = 0

    for p in pending:
        match_id = p["match_id"]
        home_team = p["home_team"]
        away_team = p["away_team"]
        league = p["league"]
        match_date = p["match_date"]

        logger.info(
            f"  [{updated + failed + 1}/{len(pending)}] "
            f"{home_team} vs {away_team} [{league}] on {match_date}"
        )

        if not api_key:
            logger.debug("    Skipping (no API key)")
            failed += 1
            continue

        result = _fetch_result_from_api(
            match_id=match_id,
            home_team=home_team,
            away_team=away_team,
            league=league,
            match_date=match_date,
            api_key=api_key,
            logger=logger,
        )

        if result is None:
            logger.debug(f"    Result not available yet for match {match_id}")
            failed += 1
            continue

        home_goals, away_goals = result
        outcome = "home" if home_goals > away_goals else ("away" if away_goals > home_goals else "draw")
        logger.info(f"    Result: {home_goals}-{away_goals} ({outcome})")

        if not dry_run:
            updated_record = tracker.record_result(match_id, home_goals, away_goals)
            if updated_record:
                correct = "✓" if updated_record.prediction_correct else "✗"
                logger.info(
                    f"    {correct} Prediction was '{updated_record.predicted_outcome}', "
                    f"actual '{outcome}' | brier={updated_record.brier_score:.4f}"
                )
                updated += 1
            else:
                logger.warning(f"    Could not update record for match {match_id}")
                failed += 1
        else:
            logger.info("    [DRY RUN] Would update result")
            updated += 1

    # Print accuracy summary
    if updated > 0 and not dry_run:
        try:
            stats = tracker.get_accuracy_stats(days_back=90)
            total = stats.get("total_predictions", 0)
            if total > 0:
                logger.info(
                    f"\n📊 Accuracy summary (last 90 days): "
                    f"{stats['accuracy_pct']} over {total} predictions "
                    f"| Brier={stats.get('brier_score', 'N/A')}"
                )
                league_comp = tracker.get_league_comparison()
                for league, data in league_comp.items():
                    if data["total_predictions"] > 0:
                        acc = data["accuracy"] or 0
                        logger.info(
                            f"  {league}: {acc:.1%} ({data['total_predictions']} predictions)"
                        )
        except Exception as exc:
            logger.debug(f"Could not generate summary: {exc}")

    logger.info(f"\nDone — {updated} updated, {failed} skipped/unavailable")
    return updated


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch and record actual match results for tracked predictions"
    )
    parser.add_argument(
        "--days-back",
        type=int,
        default=7,
        help="Only process predictions for matches up to N days ago (default: 7)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate updates without writing to DB",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable debug logging",
    )
    args = parser.parse_args()

    try:
        run(days_back=args.days_back, dry_run=args.dry_run, verbose=args.verbose)
    except Exception as exc:
        logging.getLogger("update_prediction_results").error(f"Fatal error: {exc}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
