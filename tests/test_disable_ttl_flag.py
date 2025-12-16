import os
import pytest


def test_disable_ttl_override_propagates(monkeypatch):
    # Set a mock API key so SingleMatchGenerator can initialize
    monkeypatch.setenv('FOOTBALL_DATA_API_KEY', 'test_key_for_unit_tests')
    
    # Import after setting env var to avoid import-time errors
    from generate_fast_reports import SingleMatchGenerator
    
    ttl_override = 123
    gen = SingleMatchGenerator(skip_injuries=False, injuries_disable_ttl_override=ttl_override)
    assert gen.data_quality_enhancer.injuries_disable_ttl_override == ttl_override
