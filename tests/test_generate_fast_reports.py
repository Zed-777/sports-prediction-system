import os
import pytest
from generate_fast_reports import SingleMatchGenerator


@pytest.mark.skipif(os.getenv('RUN_NETWORK_TESTS') != '1', reason="Network tests disabled")
def test_generate_single_premier_league_report():
    """Integration smoke test for generating a single premier league report."""
    gen = SingleMatchGenerator()
    # Run report generation for 1 match; this uses network calls by default so it's behind a flag
    gen.generate_matches_report(1, 'premier-league')
    # If generation succeeded without exceptions, test passes
    assert True
