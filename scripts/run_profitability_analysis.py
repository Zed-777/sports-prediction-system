"""
Profitability Analysis CLI (PROF-005)
======================================
Runs the full live-trading validation pipeline and prints a comprehensive
performance report.

Usage
-----
    python scripts/run_profitability_analysis.py [options]

Options
-------
    --profile     conservative | standard | aggressive  (default: standard)
    --bookmaker   soft | sharp | exchange | default      (default: sharp)
    --n-synthetic Number of synthetic matches to generate (default: 2000)
    --model-acc   Assumed model accuracy 0-1              (default: 0.60)
    --no-save     Skip saving results to disk
    --verbose     Debug logging
    --results-dir Directory for output files              (default: reports/profitability)

Exit codes
----------
    0  LIVE-READY: strategy passes all criteria
    1  NOT YET READY: one or more criteria not met
    2  Error
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def _setup_logging(verbose: bool) -> logging.Logger:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    return logging.getLogger("profitability_analysis")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run profitability analysis and live-trading validation"
    )
    parser.add_argument(
        "--profile",
        choices=["conservative", "standard", "aggressive"],
        default="standard",
        help="Qualifying parameter profile (default: standard)",
    )
    parser.add_argument(
        "--bookmaker",
        choices=["soft", "sharp", "exchange", "default"],
        default="sharp",
        help="Bookmaker type for market odds simulation (default: sharp)",
    )
    parser.add_argument(
        "--n-synthetic",
        type=int,
        default=2000,
        help="Synthetic matches to generate when real data is sparse (default: 2000)",
    )
    parser.add_argument(
        "--model-acc",
        type=float,
        default=0.60,
        help="Assumed model accuracy 0-1 for synthetic generation (default: 0.60)",
    )
    parser.add_argument(
        "--results-dir",
        type=str,
        default="reports/profitability",
        help="Output directory (default: reports/profitability)",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Skip saving results to disk",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging",
    )
    args = parser.parse_args()

    logger = _setup_logging(args.verbose)

    try:
        from app.models.qualifying_gate import QualifyingParams
        from app.models.live_trading_validator import LiveTradingValidator

        # Select qualifying profile
        if args.profile == "conservative":
            params = QualifyingParams.conservative()
            profile_label = "Conservative"
        elif args.profile == "aggressive":
            params = QualifyingParams.aggressive()
            profile_label = "Aggressive"
        else:
            params = QualifyingParams.standard()
            profile_label = "Standard"

        logger.info(f"Running profitability analysis — profile: {profile_label}, "
                    f"bookmaker: {args.bookmaker}")
        logger.info(f"  Min edge: {params.min_edge_pct}pp  |  "
                    f"Min confidence: {params.min_confidence}  |  "
                    f"Odds: {params.min_odds}–{params.max_odds}")

        validator = LiveTradingValidator(
            results_dir=args.results_dir,
            bookmaker_type=args.bookmaker,
        )

        verdict = validator.run(
            params=params,
            n_synthetic=args.n_synthetic,
            model_accuracy=args.model_acc,
            n_walk_forward_splits=5,
            n_sensitivity_runs=True,
            save_results=not args.no_save,
            verbose=True,
        )

        # Final console output
        v = verdict["verdict"]
        fs = verdict["full_sample_report"]

        print("\n" + "=" * 68)
        if v["live_ready"]:
            print("  ✓ LIVE-READY: Strategy passes all qualifying criteria!")
        else:
            print("  ✗ NOT YET READY: One or more criteria not met.")
        print(f"  Live-readiness score: {v['live_readiness_score']:.1f}/100")
        print("=" * 68)
        print(f"  Sample : {fs['sample']['qualifying_bets']} qualifying bets "
              f"({fs['sample']['total_bets']} total evaluated)")
        print(f"  ROI    : {fs['financial']['roi_pct']:+.2f}%  "
              f"[95% CI: {fs['statistics']['ci_95_low_pct']:+.2f}%, "
              f"{fs['statistics']['ci_95_high_pct']:+.2f}%]")
        print(f"  Hit    : {fs['sample']['hit_rate_pct']:.1f}%  "
              f"  p={fs['statistics']['p_value']:.4f} "
              f"({'sig' if fs['statistics']['statistically_significant'] else 'not sig'})")
        print(f"  MaxDD  : {fs['risk']['max_drawdown_pct']:.1f}%  "
              f"  Ruin risk: {fs['risk']['risk_of_ruin_pct']:.2f}%")
        print(f"  Sharpe : {fs['risk']['sharpe_equivalent']:.3f}")
        print()

        wf = verdict["walk_forward"]
        print(f"  Walk-forward ({wf['n_folds']} folds): "
              f"mean ROI={wf['mean_roi_pct']:+.2f}%  "
              f"positive in {wf['positive_roi_folds_pct']}% of folds  "
              f"({'PASS ✓' if wf['passed'] else 'FAIL ✗'})")
        print()

        print(f"  Recommendation: {v['recommendation']}")
        print()

        if v["failure_reasons"]:
            print("  Failure reasons:")
            for r in v["failure_reasons"]:
                print(f"    ✗ {r}")

        print()
        if not args.no_save:
            print(f"  Full report saved to: {args.results_dir}/")
        print("=" * 68 + "\n")

        # Exit 0 if live-ready, 1 otherwise
        sys.exit(0 if v["live_ready"] else 1)

    except Exception as exc:
        logger.error(f"Fatal error: {exc}", exc_info=True)
        sys.exit(2)


if __name__ == "__main__":
    main()
