"""
Backtesting CLI Runner (VB-001 / TODO #32)
==========================================
Runs the BacktestingFramework against historical data using the
EnhancedPredictor, saves results to reports/backtests/ and prints a summary.

Usage:
    python scripts/run_backtest.py [--leagues PL,PD,...] [--days N] [--model-name NAME] [--verbose]

Exit codes:
    0 - success
    1 - error
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

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
    return logging.getLogger("run_backtest")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run historical backtesting for prediction accuracy validation"
    )
    parser.add_argument(
        "--leagues",
        type=str,
        default=None,
        help="Comma-separated league IDs to backtest (default: all available)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=365,
        help="Number of past days of historical data to use (default: 365)",
    )
    parser.add_argument(
        "--train-window",
        type=int,
        default=180,
        help="Training window in days for rolling backtest (default: 180)",
    )
    parser.add_argument(
        "--test-window",
        type=int,
        default=30,
        help="Test window in days for rolling backtest (default: 30)",
    )
    parser.add_argument(
        "--model-name",
        type=str,
        default=f"enhanced_v4_{datetime.now().strftime('%Y%m%d')}",
        help="Name for this model run (used in output files)",
    )
    parser.add_argument(
        "--results-dir",
        type=str,
        default="reports/backtests",
        help="Directory to write backtest results (default: reports/backtests)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable debug logging",
    )
    parser.add_argument(
        "--skip-predictor",
        action="store_true",
        help="Use a dummy predictor instead of the real EnhancedPredictor (for CI / smoke tests)",
    )
    args = parser.parse_args()

    logger = _setup_logging(args.verbose)

    # Import framework
    try:
        from app.models.backtesting import BacktestingFramework, create_simple_predictor
    except ImportError as exc:
        logger.error(f"Cannot import BacktestingFramework: {exc}")
        sys.exit(1)

    framework = BacktestingFramework(
        data_dir="data",
        results_dir=args.results_dir,
    )

    # Load historical data
    leagues = [l.strip() for l in args.leagues.split(",")] if args.leagues else None
    from datetime import timedelta
    start_date = datetime.now() - timedelta(days=args.days)

    matches = framework.load_historical_data(leagues=leagues, start_date=start_date)

    if not matches:
        logger.warning(
            "No historical data found. Run `scripts/collect_historical_results.py` first "
            "or ensure data/historical/ contains match JSON files."
        )
        # Write empty marker so CI can see the job ran
        out = Path(args.results_dir)
        out.mkdir(parents=True, exist_ok=True)
        marker = {
            "model_name": args.model_name,
            "run_date": datetime.now().isoformat(),
            "status": "no_data",
            "message": "No historical match data available for backtesting.",
        }
        marker_path = out / f"backtest_no_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(marker_path, "w", encoding="utf-8") as f:
            json.dump(marker, f, indent=2)
        logger.info(f"Wrote no-data marker to {marker_path}")
        sys.exit(0)

    logger.info(
        f"Loaded {len(matches)} historical matches. "
        f"Date range: {matches[0]['date'].date()} to {matches[-1]['date'].date()}"
    )

    # Build predictor
    if args.skip_predictor:
        logger.info("Using dummy predictor (--skip-predictor flag set)")
        def predictor(match: dict) -> dict:
            return {
                "home_win_prob": 42.0,
                "draw_prob": 26.0,
                "away_win_prob": 32.0,
                "confidence": 50.0,
            }
    else:
        api_key = os.getenv("FOOTBALL_DATA_API_KEY", "dummy")
        try:
            from enhanced_predictor import EnhancedPredictor
            ep = EnhancedPredictor(api_key)
            predictor = create_simple_predictor(ep)
            logger.info("Using EnhancedPredictor for backtesting")
        except Exception as exc:
            logger.warning(f"EnhancedPredictor unavailable ({exc}); falling back to dummy predictor")
            def predictor(match: dict) -> dict:  # type: ignore[misc]
                return {
                    "home_win_prob": 42.0,
                    "draw_prob": 26.0,
                    "away_win_prob": 32.0,
                    "confidence": 50.0,
                }

    # Run backtest
    logger.info(
        f"Running backtest | model={args.model_name} | "
        f"train_window={args.train_window}d | test_window={args.test_window}d"
    )
    summary = framework.run_backtest(
        predictor=predictor,
        model_name=args.model_name,
        test_matches=matches,
        train_window_days=args.train_window,
        test_window_days=args.test_window,
        min_train_matches=10,
    )

    # Print summary
    if summary.total_matches == 0:
        logger.warning("Backtest produced 0 results — check historical data coverage.")
    else:
        print(f"\n{'='*60}")
        print(f"  BACKTEST SUMMARY: {summary.model_name}")
        print(f"{'='*60}")
        print(f"  Period : {summary.test_period_start.date()} → {summary.test_period_end.date()}")
        print(f"  Matches: {summary.total_matches}")
        print(f"  Accuracy          : {summary.accuracy*100:.1f}%")
        print(f"    Home predictions : {summary.home_accuracy*100:.1f}%")
        print(f"    Draw predictions : {summary.draw_accuracy*100:.1f}%")
        print(f"    Away predictions : {summary.away_accuracy*100:.1f}%")
        print(f"  Brier Score       : {summary.mean_brier_score:.4f}  (lower = better)")
        print(f"  Log Loss          : {summary.mean_log_loss:.4f}")
        print(f"  High-conf accuracy: {summary.high_confidence_accuracy*100:.1f}%")
        print(f"  Med-conf  accuracy: {summary.medium_confidence_accuracy*100:.1f}%")
        if summary.league_accuracy:
            print(f"\n  Accuracy by league:")
            for league, acc in sorted(summary.league_accuracy.items(), key=lambda x: -x[1]):
                print(f"    {league}: {acc*100:.1f}%")
        print(f"{'='*60}\n")

    logger.info(f"Results saved to {args.results_dir}/")


if __name__ == "__main__":
    main()
