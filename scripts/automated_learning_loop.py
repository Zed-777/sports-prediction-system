#!/usr/bin/env python3
"""
Automated Learning Loop - Sports Prediction System

Runs daily (4 AM UTC) to collect match results and retrain models.
NO MANUAL INTERVENTION REQUIRED - runs fully automatically via Windows Task Scheduler

USAGE:
    python scripts/automated_learning_loop.py [--league LEAGUE] [--verbose]

PART OF: Automated Learning Architecture (MPDP.md)
"""

import argparse
import json
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def setup_logging(log_dir):
    """Setup logging to file and console"""
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / f"learning_loop_{datetime.now():%Y-%m-%d_%H%M%S}.log"
    
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    
    # File handler
    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(fh)
    
    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(ch)
    
    return logger, log_file


def run_learning_loop(league="all", verbose=False):
    """Execute the automated learning loop"""
    
    project_root = Path(__file__).parent.parent
    log_dir = project_root / "data" / "logs" / "automated"
    
    logger, log_file = setup_logging(log_dir)
    
    try:
        logger.info("=" * 60)
        logger.info("AUTOMATED LEARNING LOOP STARTED")
        logger.info("=" * 60)
        logger.info(f"League: {league}")
        logger.info(f"Log file: {log_file}")
        logger.info(f"Timestamp: {datetime.now():%Y-%m-%d %H:%M:%S}")
        
        # Change to project root
        import os
        os.chdir(project_root)
        
        # Step 1: Collect completed match results
        logger.info("Step 1: Collecting completed match results...")
        try:
            collect_args = [
                sys.executable,
                "scripts/collect_historical_results.py",
                "--fetch-all" if league == "all" else f"--league {league}",
                "--auto-optimize 50"
            ]
            result = subprocess.run(
                " ".join(collect_args),
                shell=True,
                capture_output=True,
                text=True,
                timeout=600
            )
            if result.returncode == 0:
                logger.info("✓ Results collected successfully")
            else:
                logger.warning(f"⚠ Collection completed with warnings (code: {result.returncode})")
            logger.debug(f"Output: {result.stdout[:500]}")
        except Exception as e:
            logger.warning(f"⚠ Collection step error: {e}")
        
        # Step 2: Update prediction tracker
        logger.info("Step 2: Updating prediction tracker with match results...")
        try:
            result = subprocess.run(
                f'{sys.executable} scripts/update_prediction_results.py --days-back 14 --verbose',
                shell=True,
                capture_output=True,
                text=True,
                timeout=600
            )
            if result.returncode == 0:
                logger.info("✓ Prediction tracker updated successfully")
            else:
                logger.warning(f"⚠ Tracker update completed with warnings (code: {result.returncode})")
            logger.debug(f"Output: {result.stdout[:500]}")
        except Exception as e:
            logger.warning(f"⚠ Tracker update error: {e}")
        
        # Step 3: Optimize models
        logger.info("Step 3: Retraining models with new data...")
        try:
            leagues_to_process = [
                "premier-league", "la-liga", "serie-a", "bundesliga", "ligue-1"
            ] if league == "all" else [league]
            
            for lg in leagues_to_process:
                logger.info(f"  Processing: {lg}")
                result = subprocess.run(
                    f'{sys.executable} scripts/optimize_accuracy.py --mode full --league {lg}',
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=600
                )
                if result.returncode == 0:
                    logger.info(f"    ✓ {lg} optimized")
                else:
                    logger.warning(f"    ⚠ {lg} optimization (code: {result.returncode})")
        except Exception as e:
            logger.warning(f"⚠ Model optimization error: {e}")
        
        # Step 4: Cleanup
        logger.info("Step 4: Cleaning up old cache files...")
        try:
            cache_dir = project_root / "data" / "cache"
            old_count = 0
            for f in cache_dir.glob("*"):
                import time
                if time.time() - f.stat().st_mtime > 30 * 86400:  # >30 days
                    f.unlink()
                    old_count += 1
            if old_count > 0:
                logger.info(f"✓ Removed {old_count} old cache files")
        except Exception as e:
            logger.warning(f"⚠ Cleanup error: {e}")
        
        # Summary
        logger.info("=" * 60)
        logger.info("AUTOMATED LEARNING LOOP COMPLETED")
        logger.info("=" * 60)
        logger.info(f"Status: SUCCESS")
        logger.info(f"Timestamp: {datetime.now():%Y-%m-%d %H:%M:%S}")
        logger.info("Next run: 4 AM UTC tomorrow")
        
        return 0
        
    except Exception as e:
        logger.error(f"CRITICAL ERROR: {e}", exc_info=True)
        logger.error("AUTOMATED LEARNING LOOP FAILED")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Automated learning loop for sports prediction system"
    )
    parser.add_argument(
        "--league",
        default="all",
        choices=["all", "premier-league", "la-liga", "serie-a", "bundesliga", "ligue-1"],
        help="League to process (default: all)"
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    exit_code = run_learning_loop(league=args.league, verbose=args.verbose)
    sys.exit(exit_code)
