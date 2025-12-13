#!/usr/bin/env python3
import os
import pytest

# Debug: print env at test time
print(f"\n[DEBUG] At pytest module load time:")
print(f"  API_FOOTBALL_KEY: {os.environ.get('API_FOOTBALL_KEY')!r}")
print(f"  FOOTBALL_DATA_API_KEY: {os.environ.get('FOOTBALL_DATA_API_KEY')!r}")

def test_debug_env():
    """Simple test to show env vars"""
    api_key = os.environ.get('API_FOOTBALL_KEY')
    if not api_key or api_key.startswith('YOUR_'):
        pytest.skip('API_FOOTBALL_KEY not set or placeholder; skipping API-Football test')
    print(f"  API_FOOTBALL_KEY value: {api_key!r}")
