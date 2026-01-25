import json
from pathlib import Path


from generate_fast_reports import SingleMatchGenerator


def test_publication_gate_redirects_low_confidence(tmp_path, monkeypatch):
    monkeypatch.setenv("FOOTBALL_DATA_API_KEY", "DUMMY_KEY")

    gen = SingleMatchGenerator(skip_injuries=True)

    match_folder = tmp_path / "reports" / "leagues" / "premier-league" / "matches" / "m_low_conf"
    match_folder.mkdir(parents=True, exist_ok=True)

    match_data = {
        "id": "m_low_conf",
        "league": "premier-league",
        "home_team": "A Team",
        "away_team": "B Team",
        # Low confidence and low data quality to trigger gate
        "report_accuracy_probability": 0.20,
        "data_quality_score": 20.0,
    }

    gen.save_json(match_data, str(match_folder))

    # Expect redirected synthetic folder
    synthetic_path = Path("reports") / "simulated" / "premier-league" / "matches" / (Path(str(match_folder)).name + "_synthetic")
    assert synthetic_path.exists(), f"Expected synthetic dir at {synthetic_path}"
    pred_json = synthetic_path / "prediction.json"
    assert pred_json.exists(), "prediction.json not written for synthetic report"
    data = json.loads(pred_json.read_text(encoding="utf-8"))
    assert data.get("is_synthetic") or (data.get("synthetic_reason") == "publication_gate_threshold")

    # Ensure public folder did NOT receive prediction.json
    public_json = match_folder / "prediction.json"
    assert not public_json.exists(), "Public report should not include low-confidence prediction.json"
