import os

import pytest


def test_phase2_lite_smoke(monkeypatch):
    """Smoke test for Phase 2 Lite predictor. Ensures it returns a valid dict with a confidence field."""
    # Set mock API key before importing module
    monkeypatch.setenv('FOOTBALL_DATA_API_KEY', 'test_key_for_unit_tests')
    
    from phase2_lite import test_phase2_lite
    
    result = test_phase2_lite()
    assert result is not None, "test_phase2_lite returned None - API key may be invalid"
    assert isinstance(result, dict)
    assert 'confidence' in result
    assert isinstance(result['confidence'], (float, int))
