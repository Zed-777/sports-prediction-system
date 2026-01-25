import os



def test_flashscore_ingest_and_image_generation(monkeypatch, tmp_path):
    """Integration-style test: ingest FlashScore data and produce JSON + PNG output."""
    # Set mock API key before importing modules
    monkeypatch.setenv("FOOTBALL_DATA_API_KEY", "test_key_for_unit_tests")

    from enhanced_data_ingestion import EnhancedDataIngestion, LeagueConfig
    from generate_fast_reports import SingleMatchGenerator

    api_key = os.getenv("FOOTBALL_DATA_API_KEY", "TEST_KEY")

    ingestion = EnhancedDataIngestion(api_key, enable_flashscore=True)
    league = LeagueConfig.from_key("la-liga")

    # Fetch FlashScore data (uses cached fixture if available)
    fs_data = ingestion.fetch_flashscore_data(league)
    assert fs_data is not None
    assert isinstance(fs_data.get("matches", []), list)

    # Minimal football-data-like match for merging
    football_data = {
        "matches": [
            {
                "id": 999999,
                "homeTeam": {"id": 1, "name": "Getafe CF"},
                "awayTeam": {"id": 2, "name": "Girona FC"},
            }
        ],
        "data_source": "football-data.org",
    }

    merged = ingestion.merge_data_sources(football_data, fs_data)
    assert merged.get("flashscore_metadata", {}).get("integrated", False) is True

    fd_match = merged["matches"][0]

    # Minimal prediction payload for the renderer
    match_data = {
        "match_id": fd_match.get("id"),
        "home_team": fd_match.get("homeTeam", {}).get("name", "Home"),
        "away_team": fd_match.get("awayTeam", {}).get("name", "Away"),
        "date": "2025-10-31",
        "time": "21:00",
        "league": league.name,
        "confidence": 0.78,
        "report_accuracy_probability": 0.76,
        "home_win_probability": 42.0,
        "draw_probability": 28.0,
        "away_win_probability": 30.0,
        "expected_home_goals": 1.1,
        "expected_away_goals": 1.3,
        "processing_time": 0.5,
        "expected_final_score": "1-1",
        "player_availability": {
            "home_team": {"expected_lineup_strength": 90},
            "away_team": {"expected_lineup_strength": 88},
        },
        "data_quality_score": 78.0,
        "prediction_engine": "Test Engine",
        "generated_at": "2025-10-28T00:00:00",
    }

    generator = SingleMatchGenerator()
    out_dir = tmp_path / "match"
    out_dir.mkdir(parents=True)

    generator.save_json(match_data, str(out_dir))
    generator.save_image(match_data, str(out_dir))

    assert (out_dir / "prediction.json").exists()
    assert (out_dir / "prediction_card.png").exists()


def test_flashscore_merge_and_prediction(monkeypatch):
    """Test merge behavior and that the predictor consumes FlashScore features."""
    # Set mock API key before importing modules
    monkeypatch.setenv("FOOTBALL_DATA_API_KEY", "test_key_for_unit_tests")

    from enhanced_data_ingestion import EnhancedDataIngestion
    from enhanced_predictor import EnhancedPredictor

    # Build minimal football-data match structure
    football_match = {
        "id": 1,
        "utcDate": "2025-10-31T19:00:00Z",
        "homeTeam": {"id": 100, "name": "Team A"},
        "awayTeam": {"id": 200, "name": "Team B"},
    }
    football_data = {"matches": [football_match], "data_source": "football-data.org"}

    # Minimal FlashScore match
    fs_match = {
        "home_team": "Team A",
        "away_team": "Team B",
        "home_recent_form": "WWDWW",
        "away_recent_form": "DLWDD",
        "score": {"home": 0, "away": 0},
        "odds_data": {"home": 2.50, "away": 3.10},
    }
    flashscore_data = {"matches": [fs_match], "live_scores": [], "league": "la-liga"}

    ingestion = EnhancedDataIngestion(api_key="DUMMY_API_KEY", enable_flashscore=False)
    merged = ingestion.merge_data_sources(football_data, flashscore_data)

    assert "flashscore_metadata" in merged
    fd_match = merged["matches"][0]
    assert "flashscore_data" in fd_match
    assert fd_match["flashscore_data"]["home_team"] == "Team A"

    predictor = EnhancedPredictor(api_key="DUMMY_API_KEY")

    # Monkeypatch network-heavy methods
    monkeypatch.setattr(
        predictor,
        "fetch_team_home_away_stats",
        lambda team_id, code: {
            "home": {
                "matches": 10,
                "win_rate": 50,
                "avg_goals_for": 1.2,
                "avg_goals_against": 1.1,
            },
            "away": {
                "matches": 8,
                "win_rate": 40,
                "avg_goals_for": 1.0,
                "avg_goals_against": 1.3,
            },
        },
    )
    monkeypatch.setattr(
        predictor,
        "fetch_head_to_head_history",
        lambda h, a, c: {
            "total_meetings": 2,
            "avg_goals_for_when_home": 1.1,
            "avg_goals_for_when_away": 1.2,
            "home_advantage_vs_opponent": 52.0,
            "recent_form": [],
        },
    )

    result = predictor.enhanced_prediction(fd_match, "PD")

    assert isinstance(result, dict)
    assert "confidence" in result and isinstance(result["confidence"], float)
    assert ("home_win_prob" in result) or ("home_win_probability" in result)

    assert fd_match.get("_flashscore_features") is not None
    fs_features = fd_match["_flashscore_features"]
    assert "home_form_score" in fs_features
    assert "odds_home" in fs_features
