from app.utils.metrics import get_metrics, increment_metric


def test_metrics_increment_and_aggregation():
    # Reset any existing keys for a clean state
    # Note: The get_metrics() returns a dict; we assert counts are updated appropriately
    increment_metric('api', 'calls', 1)
    increment_metric('api', 'errors', 1)
    metrics = get_metrics()
    assert metrics.get('api', {}).get('calls', 0) >= 1
    assert metrics.get('api', {}).get('errors', 0) >= 1
