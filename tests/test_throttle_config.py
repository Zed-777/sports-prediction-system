from app.utils.http import get_min_interval_for_host


def test_get_min_interval_for_known_hosts():
    assert (
        get_min_interval_for_host(
            "https://api.football-data.org/v4/competitions/PL/matches",
        )
        == 6.0
    )
    assert (
        get_min_interval_for_host("https://api-football-v1.p.rapidapi.com/v3/injuries")
        == 1.2
    )
    assert get_min_interval_for_host("https://api.sportsdata.io/v3/soccer") == 1.0
    assert get_min_interval_for_host("https://api.the-odds-api.com/v4") == 1.0


def test_get_min_interval_for_unknown_host():
    assert get_min_interval_for_host("https://example.com/some/endpoint") == 0.5
