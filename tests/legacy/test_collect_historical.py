import json

import pandas as pd

from scripts.collect_historical_data import collect_from_csv, save_processed


def make_temp_csv(tmp_path, rows):
    p = tmp_path / "test_matches.csv"
    df = pd.DataFrame(rows)
    df.to_csv(p, index=False)
    return p


def test_collect_from_csv_basic(tmp_path):
    rows = [
        {
            "id": 1,
            "home_team": "A",
            "away_team": "B",
            "date": "2020-01-01",
            "home_score": 2,
            "away_score": 1,
            "status": "finished",
        },
        {
            "id": 2,
            "home_team": "A",
            "away_team": "C",
            "date": "2020-01-10",
            "home_score": 1,
            "away_score": 1,
            "status": "finished",
        },
    ]
    csv_path = make_temp_csv(tmp_path, rows)
    processed, labels = collect_from_csv(csv_path)
    assert len(processed) == 2
    assert labels == [2, 1] or labels == [2, 1]


def test_save_processed_file(tmp_path):
    processed = [
        {
            "match_id": 1,
            "date": "2020-01-01",
            "home_team": "A",
            "away_team": "B",
            "features": {},
            "label": 2,
        },
    ]
    labels = [2]
    out_path = tmp_path / "historical_dataset.json"
    save_processed(processed, labels, out_path)
    assert out_path.exists()
    data = json.loads(out_path.read_text(encoding="utf-8"))
    assert "processed" in data and "labels" in data
