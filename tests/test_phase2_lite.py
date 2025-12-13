import os
from phase2_lite import test_phase2_lite


def test_phase2_lite_smoke():
    """Smoke test for Phase 2 Lite predictor. Ensures it returns a valid dict with a confidence field."""
    result = test_phase2_lite()
    assert isinstance(result, dict)
    assert 'confidence' in result
    assert isinstance(result['confidence'], float) or isinstance(result['confidence'], int)
