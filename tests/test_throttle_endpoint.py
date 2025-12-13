import time

from app.utils.throttle import ThrottleManager, TokenBucket


def test_endpoint_min_interval_matching():
    mgr = ThrottleManager()
    host = 'api.example.com'
    mgr.set_endpoint_min_interval(host, '/v1/items/', 2.0)
    mgr.set_endpoint_min_interval(host, '/v1/items/special/', 1.0)

    url1 = 'https://api.example.com/v1/items/123'
    url2 = 'https://api.example.com/v1/items/special/456'
    url3 = 'https://api.example.com/v1/other/456'

    assert mgr.get_min_interval(url1, default=0.5) == 2.0
    assert mgr.get_min_interval(url2, default=0.5) == 1.0
    assert mgr.get_min_interval(url3, default=0.5) == 0.5


def test_endpoint_bucket_matching():
    mgr = ThrottleManager()
    host = 'api.example.com'
    tb_items = TokenBucket(capacity=2, rate=1.0)
    tb_special = TokenBucket(capacity=1, rate=0.2)

    mgr.set_endpoint_bucket(host, '/v1/items/', tb_items)
    mgr.set_endpoint_bucket(host, '/v1/items/special/', tb_special)

    url1 = 'https://api.example.com/v1/items/123'
    url2 = 'https://api.example.com/v1/items/special/456'
    url3 = 'https://api.example.com/v1/other/456'

    assert mgr.get_bucket(url1) is tb_items
    assert mgr.get_bucket(url2) is tb_special
    assert mgr.get_bucket(url3) is None
