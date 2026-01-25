#!/usr/bin/env python3
"""
Run historical backfill across leagues using `scripts/collect_historical_results.py`.
Usage:
  python scripts/run_historical_backfill.py --leagues premier-league --days 365 --execute

By default it runs in dry-run mode which only reports what would be fetched.
"""
import argparse
import os
import sys
import logging
from pathlib import Path

# Ensure project root on path when executed from scripts/
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.collect_historical_results import HistoricalResultsCollector

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--leagues", type=str, nargs="*", help="List of leagues to backfill (slugs)")
    parser.add_argument("--days", type=int, default=365 * 3, help="Days lookback to fetch (default 3 years)")
    parser.add_argument("--execute", action="store_true", help="Actually perform fetches. Without this flag, runs as dry-run.")
    parser.add_argument("--commit", action="store_true", help="Create a local branch and commit updated historical files (no push). Use with --execute.")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode (save raw responses to reports/debug/flashscore)")
    args = parser.parse_args()

    collector = HistoricalResultsCollector()
    collector.ensure_historical_files()

    target_leagues = args.leagues if args.leagues else collector.detect_report_leagues()
    if not target_leagues:
        logger.error("No target leagues detected. Nothing to do.")
        return 1

    # Check for primary API key
    fd_key = os.environ.get("FOOTBALL_DATA_API_KEY")
    api_football_key = os.environ.get("API_FOOTBALL_KEY") or os.environ.get("API_FOOTBALL_KEY_RAPID")

    logger.info(f"Detected FOOTBALL_DATA_API_KEY={'set' if fd_key else 'missing'}, API_FOOTBALL_KEY={'set' if api_football_key else 'missing'}")

    any_updates = 0
    for league in target_leagues:
        logger.info(f"Preparing backfill for league: {league} (lookback {args.days} days)")

        # Collect any existing predictions from reports and save
        preds = collector.collect_from_reports(league)
        logger.info(f"Found {len(preds)} predictions from existing reports for {league}")
        if preds and args.execute:
            saved = collector.save_historical_data(league, preds)
            logger.info(f"Saved {saved} collected predictions to historical file for {league}")
            any_updates += saved

        # Fetch from APIs (preferred)
        if fd_key or api_football_key:
            if args.execute:
                logger.info(f"Executing fetch_and_update_from_api for {league} (days={args.days}) (debug={args.debug})")
                updated = collector.fetch_and_update_from_api(league, days_lookback=args.days, debug=args.debug)
                logger.info(f"Updated {updated} records for {league} from APIs")
                any_updates += updated
                if args.debug:
                    logger.info(f"Debug files (if any) will be under reports/debug/flashscore/")
                    # Run the inspector to summarize debug files
                    try:
                        import subprocess
                        inspector_out = PROJECT_ROOT / 'reports' / 'metrics' / 'flashscore_debug_summary.json'
                        subprocess.check_call([sys.executable, str(PROJECT_ROOT / 'scripts' / 'debug_flashscore_inspect.py'), '--dir', str(PROJECT_ROOT / 'reports' / 'debug' / 'flashscore'), '--out', str(inspector_out)])
                        logger.info(f"FlashScore debug summary: {inspector_out}")
                    except Exception as e:
                        logger.debug(f"Failed to run debug inspector: {e}")
            else:
                logger.info(f"Dry-run: would fetch up to {args.days} days for {league} from configured APIs")
        else:
            logger.warning("No API keys found for Football-Data or API-Football; skipping remote backfill. Consider setting FOOTBALL_DATA_API_KEY or API_FOOTBALL_KEY in environment or .env file.")

        # Backfill provider ids where possible
        if args.execute:
            backfilled = collector.backfill_provider_ids(league, debug=args.debug)
            logger.info(f"Backfilled {backfilled} provider ids for {league}")
            any_updates += backfilled

        # Generate summary report
        try:
            summary_path = collector.generate_summary_report(league)
            logger.info(f"Generated historical summary: {summary_path}")
        except FileNotFoundError:
            logger.warning(f"No historical file for {league} to summarize")

    if args.execute and args.commit and any_updates > 0:
        # Create a local branch and commit historical files
        import subprocess
        branch = "feature/historical-backfill"
        try:
            subprocess.check_call(["git", "checkout", "-b", branch])
            subprocess.check_call(["git", "add", "data/historical"])
            subprocess.check_call(["git", "commit", "-m", f"Backfill historical results ({any_updates} updates)"])
            logger.info(f"Committed historical updates on branch {branch}. Not pushing automatically.")
        except Exception as e:
            logger.error(f"Failed to commit backfill changes: {e}")

    logger.info("Backfill run complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
