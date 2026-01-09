#!/usr/bin/env python3
"""
Train models using processed historical dataset
"""

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


def main():
    # Import app packages after sys.path insertion
    from app.data.historical_loader import dataset_to_arrays, load_processed_dataset
    from app.models.advanced_ai_engine import AdvancedAIEngine

    processed, labels = load_processed_dataset()
    X, y = dataset_to_arrays(processed)

    # Convert back to 'records' to use engine.train_models
    matches = []
    for p in processed:
        m = {
            "id": p["match_id"],
            "home_team": p["home_team"],
            "away_team": p["away_team"],
            "date": p["date"],
            "home_score": None,
            "away_score": None,
            "status": "finished",
            "league": p["features"].get("league", "la-liga"),
        }
        # attach feature fields required by engine._extract_features
        m["home_form"] = {
            "win_rate": p["features"].get("home_recent_form", 0.5),
            "goals_per_game": p["features"].get("home_avg_goals", 1.0),
            "goals_conceded_per_game": 1.0,
        }
        m["away_form"] = {
            "win_rate": p["features"].get("away_recent_form", 0.5),
            "goals_per_game": p["features"].get("away_avg_goals", 1.0),
            "goals_conceded_per_game": 1.0,
        }
        m["h2h"] = p["features"].get("h2h", {})
        matches.append(m)

    # Train models
    engine = AdvancedAIEngine(api_key="loader_key")
    engine.train_models(matches, labels)

    print("Training from historical data complete")


if __name__ == "__main__":
    main()
