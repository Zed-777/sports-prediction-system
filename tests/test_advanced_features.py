import json
import app.data.advanced_model_features as amf


def test_build_sample_dataset_creates_expected_columns_and_deterministic(tmp_path):
    # Use a temporary historical directory to isolate test data
    tmp_hist = tmp_path / "historical"
    tmp_hist.mkdir()
    test_file = tmp_hist / "test_dummy_results.json"

    entry = {
        "league": "test-league",
        "home_team": "AFC Test",
        "away_team": "BFC Foo",
        "prediction": {
            "home_win_prob": 60,  # percent -> should be normalized to 0.6
            "draw_prob": 20,
            "away_win_prob": 20,
            "confidence": 90,
            "expected_home_goals": 2.0,
            "expected_away_goals": 1.0,
        },
        "actual_result": {"home_score": 2, "away_score": 1},
    }

    test_file.write_text(json.dumps([entry]), encoding="utf-8")

    # Monkeypatch module HIST_DIR to point to our tmp_hist
    amf.HIST_DIR = tmp_hist

    out_csv1 = tmp_path / "out1.csv"
    out_csv2 = tmp_path / "out2.csv"

    amf.build_sample_dataset(out_csv1, augment_per_match=3, seed=42)
    amf.build_sample_dataset(out_csv2, augment_per_match=3, seed=42)

    assert out_csv1.exists()
    assert out_csv2.exists()

    txt1 = out_csv1.read_text(encoding="utf-8")
    txt2 = out_csv2.read_text(encoding="utf-8")
    # deterministic seed should produce identical files
    assert txt1 == txt2

    # Check columns present
    header = txt1.splitlines()[0]
    for col in ["league_idx", "goal_diff", "home_prob_ratio", "favored"]:
        assert col in header

    # Ensure number of data rows equals augment_per_match (3)
    lines = [l for l in txt1.splitlines() if l.strip()]
    assert len(lines) == 1 + 3  # header + rows

    # Check favored value corresponds to actual result (home_win -> favored=0)
    data_line = lines[1]
    parts = data_line.split(",")
    # locate favored index
    cols = header.split(",")
    fav_idx = cols.index("favored")
    assert parts[fav_idx] == "0"
