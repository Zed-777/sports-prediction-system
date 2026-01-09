from types import SimpleNamespace
from app.utils.metrics import get_metrics
from enhanced_predictor import EnhancedPredictor


def test_enhanced_predictor_metrics_propagation(monkeypatch):
    p = EnhancedPredictor("demo_key")

    # Monkeypatch safe_request_get to return a simple team matches payload
    def fake_safe_get(
        url, headers=None, params=None, timeout=None, logger=None, **kwargs
    ):
        payload = {
            "matches": [
                {
                    "homeTeam": {"id": 1},
                    "awayTeam": {"id": 2},
                    "score": {"fullTime": {"home": 1, "away": 1}},
                }
            ]
        }
        return SimpleNamespace(
            status_code=200,
            text="{}",
            json=lambda: payload,
            raise_for_status=lambda: None,
        )

    monkeypatch.setattr("enhanced_predictor.safe_request_get", fake_safe_get)
    # Reset initial metrics
    initial_metrics = get_metrics().get("api", {})
    initial_calls = initial_metrics.get("calls", 0)
    initial_errors = initial_metrics.get("errors", 0)

    # Invoke two team stat fetches (should increment api_call_count by 2)
    p.fetch_team_home_away_stats(1, "PL")
    p.fetch_team_home_away_stats(2, "PL")

    final_metrics = get_metrics().get("api", {})
    assert final_metrics.get("calls", 0) >= initial_calls + 2
    assert final_metrics.get("errors", 0) >= initial_errors
