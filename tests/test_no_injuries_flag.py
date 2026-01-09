import os
import pytest


def test_generator_skip_injuries_flag(monkeypatch):
    # Set a mock API key so SingleMatchGenerator can initialize
    monkeypatch.setenv("FOOTBALL_DATA_API_KEY", "test_key_for_unit_tests")

    # Import after setting env var to avoid import-time errors
    from generate_fast_reports import SingleMatchGenerator

    gen = SingleMatchGenerator(skip_injuries=True)
    assert gen.data_quality_enhancer.skip_injuries is True
