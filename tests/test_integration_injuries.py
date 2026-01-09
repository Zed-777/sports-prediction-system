import os
from types import SimpleNamespace

import pytest

from app.data.connectors.injuries import InjuriesConnector
from data_quality_enhancer import DataQualityEnhancer


def test_get_player_injury_impact_end_to_end(monkeypatch):
    # Prepare a parsed injuries payload as produced by the connector parser
    parsed = [
        {
            "player": {"name": "Y. Player"},
            "reason": "hamstring injury",
            "status": "out",
            "estimated_return": "2026-02-01",
            "provenance": {"source": "tests/fixture", "snippet": "Y. Player – hamstring injury (out until 2026-02-01)"},
        },
        {
            "player": {"name": "Z. Player"},
            "reason": "knee injury",
            "status": "out",
            "estimated_return": "2026-03-01",
            "provenance": {"source": "tests/fixture", "snippet": "Z. Player – knee injury (expected return 2026-03-01)"},
        },
    ]

    # Monkeypatch InjuriesConnector.fetch_injuries to return our parsed payload
    def fake_fetch(self, team_id, team_name=None, season=None):
        return parsed

    monkeypatch.setattr("app.data.connectors.injuries.InjuriesConnector.fetch_injuries", fake_fetch)

    enhancer = DataQualityEnhancer("demo_key")
    res = enhancer.get_player_injury_impact(559, "Sevilla FC")

    assert isinstance(res, dict)
    # Two injured -> 2 * 8% = 16% strength reduction
    assert res.get("injured_count") == 2
    assert float(res.get("strength_reduction_pct")) == 16.0
    assert float(res.get("expected_lineup_strength")) == 84.0
    assert res.get("data_available") is True
