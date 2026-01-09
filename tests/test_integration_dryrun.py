import os



class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_generate_dryrun(monkeypatch, tmp_path):
    # Set mock API key before importing module
    monkeypatch.setenv("FOOTBALL_DATA_API_KEY", "test_key_for_unit_tests")

    import generate_fast_reports

    # Prepare fake matches payload
    matches = [
        {
            "id": 99999,
            "utcDate": "2025-11-02T20:00:00Z",
            "homeTeam": {"id": 1, "name": "Dryrun Home"},
            "awayTeam": {"id": 2, "name": "Dryrun Away"},
        }
    ]

    fake_payload = {"matches": matches}

    # Monkeypatch requests.get used by the generator

    def fake_get(*args, **kwargs):
        return FakeResponse(fake_payload)

    monkeypatch.setattr("requests.get", fake_get)

    # Create generator instance without running full init side-effects
    gen = generate_fast_reports.SingleMatchGenerator.__new__(
        generate_fast_reports.SingleMatchGenerator
    )
    # Minimal attributes expected by generate_matches_report
    gen.api_key = "test"
    gen.headers = {"X-Auth-Token": "test"}
    gen._settings = getattr(
        generate_fast_reports.SingleMatchGenerator(), "_settings", {}
    )
    gen.phase2_lite_predictor = None

    # Stub enhanced_predictor and data_quality_enhancer
    class StubPredictor:
        def enhanced_prediction(self, match, code):
            return {
                "home_team": "Dryrun Home",
                "away_team": "Dryrun Away",
                "report_accuracy_probability": 0.75,
                "home_win_probability": 50,
                "draw_probability": 25,
                "away_win_probability": 25,
                "expected_home_goals": 1.2,
                "expected_away_goals": 1.0,
                "expected_final_score": "1-1",
                "prediction_engine": "stub",
            }

    class StubEnhancer:
        def comprehensive_data_enhancement(self, match):
            return {}

    gen.enhanced_predictor = StubPredictor()
    gen.data_quality_enhancer = StubEnhancer()

    # Call generator method
    # Using a small temp reports dir to avoid polluting repo
    try:
        os.environ["REPORTS_DIR"] = str(tmp_path)
        # Ensure the method exists and runs without raising
        gen.generate_matches_report(1, "la-liga")
    finally:
        if "REPORTS_DIR" in os.environ:
            del os.environ["REPORTS_DIR"]
