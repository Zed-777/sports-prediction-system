import time
from app.utils.throttle import ThrottleManager, TokenBucket


def test_endpoint_min_interval_matching():
    tm = ThrottleManager()
    host = 'api.football-data.org'
    tm.set_endpoint_min_interval(host, '/v4/matches', 2.0)
    tm.set_endpoint_min_interval(host, '/v4/competitions', 3.5)

    # Exact match
    url = 'https://api.football-data.org/v4/matches'
    assert tm.get_min_interval(url) == 2.0

    # Prefix match
    url2 = 'https://api.football-data.org/v4/matches?limit=5'
    assert tm.get_min_interval(url2) == 2.0

    # Longer prefix should match
    url3 = 'https://api.football-data.org/v4/competitions/PD/matches'
    assert tm.get_min_interval(url3) == 3.5


def test_endpoint_bucket_longest_prefix_match():
    tm = ThrottleManager()
    host = 'v3.football.api-sports.io'
    bucket1 = TokenBucket(capacity=2, rate=0.5)
    bucket2 = TokenBucket(capacity=4, rate=1.0)
    tm.set_endpoint_bucket(host, '/fixtures', bucket1)
    tm.set_endpoint_bucket(host, '/fixtures/team', bucket2)

    # Urls should select the correct bucket
    assert tm.get_bucket('https://v3.football.api-sports.io/fixtures') is bucket1
    assert tm.get_bucket('https://v3.football.api-sports.io/fixtures/team/23') is bucket2
