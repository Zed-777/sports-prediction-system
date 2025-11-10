import math
import os

import pytest

from app.data.odds_connector import OddsDataConnector


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    monkeypatch.delenv("ODDS_API_KEY", raising=False)


def test_get_match_odds_parses_market(monkeypatch):
    settings = {
        "base_url": "https://example-odds",
        "default_sport": "soccer",
        "default_market": "h2h",
        "region": "uk",
        "env_key": "ODDS_API_KEY",
        "cache_ttl": 900,
    }

    connector = OddsDataConnector(settings)

    sample_payload = [
        {
            "home_team": "Team A",
            "away_team": "Team B",
            "bookmakers": [
                {
                    "key": "fairbook",
                    "markets": [
                        {
                            "key": "h2h",
                            "outcomes": [
                                {"name": "Team A", "price": 1.8},
                                {"name": "Draw", "price": 3.6},
                                {"name": "Team B", "price": 4.2},
                            ],
                        }
                    ],
                }
            ],
        }
    ]

    def fake_get(url, params, timeout):  # noqa: D401 - simple stub
        return _FakeResponse(sample_payload)

    monkeypatch.setenv("ODDS_API_KEY", "test-key")
    monkeypatch.setattr("app.data.odds_connector.requests.get", fake_get)

    odds = connector.get_match_odds("premier-league", "Team A", "Team B", "2025-11-03")

    assert odds is not None
    assert odds.bookmaker_count == 1
    assert math.isclose(odds.probabilities["home"], (1 / 1.8) / (1 / 1.8 + 1 / 3.6 + 1 / 4.2), rel_tol=1e-3)
    assert math.isclose(odds.probabilities["draw"], (1 / 3.6) / (1 / 1.8 + 1 / 3.6 + 1 / 4.2), rel_tol=1e-3)
    assert odds.probabilities["home"] + odds.probabilities["draw"] + odds.probabilities["away"] == pytest.approx(1.0, rel=1e-3)

    # Ensure caching avoids a second HTTP call
    call_count = {"count": 0}

    def counting_get(url, params, timeout):
        call_count["count"] += 1
        return _FakeResponse(sample_payload)

    monkeypatch.setattr("app.data.odds_connector.requests.get", counting_get)
    cached = connector.get_match_odds("premier-league", "Team A", "Team B", "2025-11-03")

    assert cached is odds  # cached object reused
    assert call_count["count"] == 0


def test_get_match_odds_gracefully_handles_missing_env(monkeypatch):
    connector = OddsDataConnector({"env_key": "ODDS_API_KEY"})
    monkeypatch.delenv("ODDS_API_KEY", raising=False)
    result = connector.get_match_odds("la-liga", "Real", "Barca", "2025-11-03")
    assert result is None
