#!/usr/bin/env python3
"""
Auto-Generated Baseline Predictions for Continuous Learning
Generates 1 baseline prediction per league daily for accuracy tracking
Stores in data/predictions.db - learning data only (no user-facing conflicts)
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def generate_baseline_predictions():
    """Generate 1 baseline prediction per league for continuous learning tracking"""
    
    leagues = ["premier-league", "la-liga", "serie-a", "bundesliga", "ligue-1"]
    success_count = 0
    
    logger.info("=" * 60)
    logger.info("AUTO-TRACKING: Generating baseline predictions")
    logger.info("=" * 60)
    logger.info(f"Timestamp: {datetime.now():%Y-%m-%d %H:%M:%S}")
    logger.info(f"Leagues: {', '.join(leagues)}")
    logger.info("")
    logger.info("Note: Predictions stored to data/predictions.db")
    logger.info("      Auto-generated reports will be overwritten by user reports")
    logger.info("")
    
    # Import the report generator
    try:
        from generate_fast_reports import ReportGenerator
    except ImportError as e:
        logger.error(f"Failed to import ReportGenerator: {e}")
        return False
    
    # Generate 1 prediction per league
    for league in leagues:
        try:
            logger.info(f"  Generating baseline: {league}")
            
            # Create generator for this league
            generator = ReportGenerator()
            
            # Generate 1 match report (standard - data goes to DB regardless of file output)
            generator.generate_matches_report(num_matches=1, league=league)
            
            logger.info(f"    ✓ {league} baseline tracked (DB: data/predictions.db)")
            success_count += 1
            
        except Exception as e:
            logger.warning(f"    ⚠ {league} baseline failed: {e}")
            # Don't fail the entire run, continue to next league
            continue
    
    logger.info("")
    logger.info("=" * 60)
    logger.info(f"AUTO-TRACKING: {success_count}/{len(leagues)} baselines generated")
    logger.info("=" * 60)
    logger.info("Status: Predictions written to data/predictions.db")
    logger.info("        Next daily update will validate accuracy")
    logger.info("")
    
    return success_count > 0


if __name__ == "__main__":
    try:
        success = generate_baseline_predictions()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Critical error: {e}", exc_info=True)
        sys.exit(1)
