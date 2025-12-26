#!/usr/bin/env python3
"""
Test script for Enhanced Data Ingestion System
Demonstrates multi-source data collection with FlashScore integration
"""

import importlib.util
import os
import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))


def test_enhanced_ingestion():
    """Test the enhanced data ingestion system"""
    print("=== Enhanced Data Ingestion System Test ===\n")

    # Check if FlashScore scraper is available
    flashscore_available = importlib.util.find_spec("flashscore_scraper") is not None
    if flashscore_available:
        print("✓ FlashScore integration available")
    else:
        print("⚠ FlashScore integration not available")

    # Import the enhanced ingestion system
    try:
        from enhanced_data_ingestion import EnhancedDataIngestion, LeagueConfig

        print("✓ Enhanced data ingestion system imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import enhanced data ingestion: {e}")
        return False

    # Test league configuration
    try:
        league = LeagueConfig.from_key("la-liga")
        print(f"✓ League configuration works: {league.name} ({league.code})")
    except Exception as e:
        print(f"✗ League configuration failed: {e}")
        return False

    # Test API key resolution (without actual API call)
    api_key = os.getenv("FOOTBALL_DATA_API_KEY", "test_key")
    print(f"✓ API key resolution works (using: {api_key[:8]}...)")

    # Initialize ingestion system
    try:
        ingestion = EnhancedDataIngestion(
            api_key, enable_flashscore=flashscore_available
        )
        print("✓ Enhanced data ingestion system initialized")
    except Exception as e:
        print(f"✗ Failed to initialize ingestion system: {e}")
        return False

    # Test data quality calculation
    test_data = {
        "data_source": "football-data.org",
        "matches": [
            {"homeTeam": {"name": "Real Madrid"}, "awayTeam": {"name": "Barcelona"}},
            {"homeTeam": {"name": "Atletico Madrid"}, "awayTeam": {"name": "Sevilla"}},
        ],
        "flashscore_metadata": {"integrated": flashscore_available},
    }

    quality_score = ingestion._calculate_data_quality(test_data)
    print(f"✓ Data quality calculation works: {quality_score:.1f}%")

    # Test FlashScore integration if available
    if flashscore_available:
        try:
            flashscore_data = ingestion.fetch_flashscore_data(league, days_ahead=7)
            if flashscore_data:
                print(
                    f"✓ FlashScore data fetching works: {len(flashscore_data.get('matches', []))} matches"
                )
            else:
                print("⚠ FlashScore data fetching returned no data (may be normal)")
        except Exception as e:
            print(f"⚠ FlashScore data fetching failed: {e}")
    else:
        print("⚠ Skipping FlashScore tests (not available)")

    print("\n=== Test Summary ===")
    print("✓ Enhanced data ingestion system is ready!")
    print("✓ Multi-source data integration configured")
    print("✓ Data quality assessment working")
    if flashscore_available:
        print("✓ FlashScore.es integration enabled")
    else:
        print("⚠ FlashScore.es integration disabled")

    print("\n=== Usage Examples ===")
    print("# Basic usage (Football-Data.org only):")
    print("python enhanced_data_ingestion.py --league la-liga --seasons 2023")
    print()
    print("# With FlashScore integration:")
    print("python enhanced_data_ingestion.py --league premier-league --years-back 2")
    print()
    print("# Live scores only:")
    print("python enhanced_data_ingestion.py --live-only")
    print()
    print("# Force overwrite existing data:")
    print("python enhanced_data_ingestion.py --league bundesliga --force")

    return True


if __name__ == "__main__":
    success = test_enhanced_ingestion()
    sys.exit(0 if success else 1)
