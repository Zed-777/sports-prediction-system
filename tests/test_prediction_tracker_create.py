from app.models.prediction_tracker import create_prediction_record


def test_create_prediction_record_with_kwargs():
    rec = create_prediction_record(
        match_id='abc123',
        home_team='Home FC',
        away_team='Away FC',
        home_prob=0.55,
        draw_prob=0.25,
        away_prob=0.20,
        confidence=0.9,
        expected_home_goals=1,
        expected_away_goals=0,
        league='test-league',
        match_date='2025-12-20'
    )

    assert rec.match_id == 'abc123'
    assert rec.home_team_name == 'Home FC'
    assert rec.away_team_name == 'Away FC'
    assert abs(rec.predicted_home_prob - 0.55) < 1e-6
    assert rec.league == 'test-league'
