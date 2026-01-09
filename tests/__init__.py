"""
Test package for the Sports Prediction System
"""

import os
import sys
from pathlib import Path

import pytest

# Add the app directory to the Python path
app_dir = Path(__file__).parent.parent / "app"
sys.path.insert(0, str(app_dir))

# Test configuration
pytest_plugins = ["pytest_asyncio"]
