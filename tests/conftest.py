"""
Test fixtures and configuration for the Sports Prediction System tests
"""

# Use a non-interactive matplotlib backend for tests to avoid GUI/tk issues on CI
try:
    import matplotlib
    matplotlib.use('Agg')
except Exception:
    # If matplotlib is not available at config time, tests that need it will import and skip accordingly
    pass

import asyncio
import shutil
import tempfile
from pathlib import Path
from typing import Any

import pytest

from app.config import create_default_config


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_config() -> dict[str, Any]:
    """
    Provide a test configuration dictionary.
    """
    config = create_default_config()
    config.update({
        'environment': 'test',
        'database': {
            'type': 'sqlite',
            'path': ':memory:'
        },
        'logging': {
            'level': 'WARNING'
        },
        'data_engineering': {
            'caching': {
                'enabled': False
            },
            'retry_policy': {
                'max_attempts': 2
            }
        }
    })
    return config


@pytest.fixture
def temp_data_dir():
    """
    Create a temporary directory for test data.
    """
    temp_dir = tempfile.mkdtemp(prefix="sports_prediction_test_")
    temp_path = Path(temp_dir)

    # Create subdirectories
    (temp_path / "raw").mkdir()
    (temp_path / "processed").mkdir()
    (temp_path / "snapshots").mkdir()

    yield temp_path

    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_match_data():
    """
    Provide sample match data for testing.
    """
    return [
        {
            "id": 1,
            "home_team": "Real Madrid",
            "away_team": "Barcelona",
            "date": "2025-10-20",
            "home_score": None,
            "away_score": None,
            "status": "scheduled"
        },
        {
            "id": 2,
            "home_team": "Atletico Madrid",
            "away_team": "Sevilla",
            "date": "2025-10-20",
            "home_score": None,
            "away_score": None,
            "status": "scheduled"
        }
    ]


@pytest.fixture
def sample_team_data():
    """
    Provide sample team data for testing.
    """
    return [
        {
            "id": 1,
            "name": "Real Madrid",
            "league": "La Liga",
            "founded": 1902,
            "venue": "Santiago Bernabéu"
        },
        {
            "id": 2,
            "name": "Barcelona",
            "league": "La Liga",
            "founded": 1899,
            "venue": "Camp Nou"
        }
    ]


@pytest.fixture
def sample_predictions():
    """
    Provide sample prediction data for testing.
    """
    return [
        {
            "match_id": 1,
            "home_team": "Real Madrid",
            "away_team": "Barcelona",
            "home_win_prob": 0.45,
            "draw_prob": 0.25,
            "away_win_prob": 0.30,
            "confidence": 0.85,
            "expected_home_score": 1.8,
            "expected_away_score": 1.2,
            "model_version": "1.0.0",
            "prediction_date": "2025-10-19"
        }
    ]


@pytest.mark.asyncio
async def pytest_configure(config):
    """Configure pytest for async tests."""
    pass


def pytest_collection_modifyitems(config, items):
    """
    Add markers to tests based on their location and name.
    """
    for item in items:
        # Add 'unit' marker to tests in tests/unit/
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)

        # Add 'integration' marker to tests in tests/integration/
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)

        # Add 'slow' marker to tests that might be slow
        if "slow" in item.name.lower() or "integration" in str(item.fspath):
            item.add_marker(pytest.mark.slow)
