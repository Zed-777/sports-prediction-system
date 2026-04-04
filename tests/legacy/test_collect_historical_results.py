import json

from scripts.collect_historical_results import HistoricalResultsCollector


def write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def test_provider_id_match_and_persistence(tmp_path):
    collector = HistoricalResultsCollector()
    collector.historical_dir = tmp_path
    league = "la-liga"
    out_file = tmp_path / f"{league}_results.json"

    rec = [
        {
            "match_id": "rayo-1",
            "league": league,
            "home_team": "Rayo Vallecano de Madrid",
            "away_team": "Real Betis Balompié",
            "match_date": "2025-12-15T20:00",
            "prediction": {},
            "actual_result": None,
        },
    ]
    write_json(out_file, rec)

    # Use the API provider id to update
    matched = collector._match_and_update(
        league,
        "2025-12-15",
        "Rayo Vallecano de Madrid",
        "Real Betis Balompié",
        1,
        2,
        debug=True,
        provider_id="544366",
        provider_name="football-data",
    )
    assert matched == 1

    updated = read_json(out_file)
    assert updated[0].get("actual_result") is not None
    assert updated[0]["actual_result"]["home_score"] == 1
    assert updated[0]["actual_result"]["away_score"] == 2
    assert (
        updated[0].get("provider_ids")
        and str(updated[0]["provider_ids"].get("football_data_id")) == "544366"
    )


def test_normalization_and_fuzzy_matching(tmp_path):
    collector = HistoricalResultsCollector()
    collector.historical_dir = tmp_path
    league = "la-liga"
    out_file = tmp_path / f"{league}_results.json"

    rec = [
        {
            "match_id": "alaves-vs-real",
            "league": league,
            "home_team": "Deportivo Alavés",
            "away_team": "Real Madrid Club de Fútbol",
            "match_date": "2025-12-14T20:00",
            "prediction": {},
            "actual_result": None,
        },
    ]
    write_json(out_file, rec)

    # API returns slightly different name spellings (no diacritics, CF vs Club)
    matched = collector._match_and_update(
        league, "2025-12-14", "Deportivo Alaves", "Real Madrid CF", 0, 3, debug=True,
    )
    assert matched == 1

    updated = read_json(out_file)
    assert updated[0].get("actual_result") is not None
    assert updated[0]["actual_result"]["home_score"] == 0
    assert updated[0]["actual_result"]["away_score"] == 3


def test_backfill_provider_ids_from_reports(tmp_path):
    collector = HistoricalResultsCollector()
    collector.historical_dir = tmp_path
    collector.reports_dir = tmp_path / "reports" / "leagues"
    league = "la-liga"
    out_file = tmp_path / f"{league}_results.json"

    rec = [
        {
            "match_id": "test-match",
            "league": league,
            "home_team": "Home FC",
            "away_team": "Away FC",
            "match_date": "2025-12-20T18:00",
            "prediction": {},
            "actual_result": None,
        },
    ]
    write_json(out_file, rec)

    # Create report prediction.json with provider_ids
    pred_dir = collector.reports_dir / league / "matches" / "test-match"
    pred_dir.mkdir(parents=True, exist_ok=True)
    pred = {
        "home_team": "Home FC",
        "away_team": "Away FC",
        "provider_ids": {"football_data_id": "999999"},
    }
    write_json(pred_dir / "prediction.json", pred)

    updated_count = collector.backfill_provider_ids(league, debug=True)
    assert updated_count == 1

    updated = read_json(out_file)
    assert (
        updated[0].get("provider_ids")
        and updated[0]["provider_ids"].get("football_data_id") == "999999"
    )


def test_save_historical_preserves_actual_result(tmp_path):
    collector = HistoricalResultsCollector()
    collector.historical_dir = tmp_path
    collector.reports_dir = tmp_path / "reports" / "leagues"
    league = "la-liga"
    out_file = tmp_path / f"{league}_results.json"

    rec = [
        {
            "match_id": "preserve-match",
            "league": league,
            "home_team": "Home FC",
            "away_team": "Away FC",
            "match_date": "2025-12-20T18:00",
            "prediction": {},
            "actual_result": {
                "home_score": 2,
                "away_score": 1,
                "outcome": "home_win",
                "updated_at": "2025-12-17T00:00:00",
            },
        },
    ]
    write_json(out_file, rec)

    # Create report prediction with same match id
    pred_dir = collector.reports_dir / league / "matches" / "preserve-match"
    pred_dir.mkdir(parents=True, exist_ok=True)
    pred = {"home_team": "Home FC", "away_team": "Away FC", "provider_ids": {}}
    write_json(pred_dir / "prediction.json", pred)

    # Collect and save; this should keep existing actual_result
    results = collector.collect_from_reports(league)
    collector.save_historical_data(league, results)

    updated = read_json(out_file)
    assert updated[0].get("actual_result") is not None
    assert updated[0]["actual_result"]["home_score"] == 2
    assert updated[0]["actual_result"]["away_score"] == 1
