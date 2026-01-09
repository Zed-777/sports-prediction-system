#!/usr/bin/env python3
"""
Initialize empty historical files for supported/detected leagues.

Usage:
    python scripts/init_historical_files.py
"""

import logging
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.collect_historical_results import HistoricalResultsCollector

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    collector = HistoricalResultsCollector()
    created = collector.ensure_historical_files()
    if created:
        logger.info("Created historical files:")
        for p in created:
            logger.info(f"  {p}")
    else:
        logger.info("Historical files already present; no files created.")


if __name__ == "__main__":
    main()
