#!/usr/bin/env python3
"""Initial Model Training Script
Trains ML models with synthetic data to bootstrap the system
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np

from app.models.advanced_ai_engine import AdvancedAIEngine


def generate_synthetic_training_data(n_samples: int = 500):
    """Generate synthetic match data for initial training"""
    print(f"Generating {n_samples} synthetic training samples...")

    training_data = []
    labels = []

    for i in range(n_samples):
        # Simulate match with realistic patterns
        home_strength = np.random.beta(3, 2)  # Home teams tend to be stronger
        away_strength = np.random.beta(2, 3)  # Away teams tend to be weaker

        # Strength differential influences outcome
        strength_diff = home_strength - away_strength

        # Calculate outcome probabilities
        if strength_diff > 0.2:
            # Strong home advantage
            probs = [0.15, 0.20, 0.65]  # away, draw, home
        elif strength_diff > 0:
            # Moderate home advantage
            probs = [0.20, 0.30, 0.50]
        elif strength_diff > -0.2:
            # Slight away advantage
            probs = [0.35, 0.30, 0.35]
        else:
            # Strong away advantage
            probs = [0.55, 0.25, 0.20]

        outcome = np.random.choice([0, 1, 2], p=probs)

        # Create match data
        match = {
            "home_team": {"name": f"Home Team {i}", "strength": home_strength},
            "away_team": {"name": f"Away Team {i}", "strength": away_strength},
            "home_form": {
                "win_rate": np.clip(home_strength + np.random.normal(0, 0.1), 0, 1),
                "goals_per_game": 1.0 + home_strength * 1.5,
                "goals_conceded_per_game": 1.5 - home_strength * 0.8,
            },
            "away_form": {
                "win_rate": np.clip(away_strength + np.random.normal(0, 0.1), 0, 1),
                "goals_per_game": 0.8 + away_strength * 1.2,
                "goals_conceded_per_game": 1.8 - away_strength * 0.7,
            },
            "h2h": {
                "home_wins": 0.45 + (strength_diff * 0.3),
                "draws": 0.30,
                "away_wins": 0.25 - (strength_diff * 0.3),
            },
            "is_derby": np.random.choice([0, 1], p=[0.9, 0.1]),
            "league_position_diff": np.random.randint(-15, 15),
            "weather": {
                "temperature": 18.0 + np.random.normal(0, 5),
                "precipitation": max(0, np.random.normal(2, 3)),
            },
            "league": "la-liga",
        }

        training_data.append(match)
        labels.append(outcome)

    print(f"✓ Generated {len(training_data)} training samples")
    print(
        f"  Outcome distribution: Home={labels.count(2)}, Draw={labels.count(1)}, Away={labels.count(0)}",
    )

    return training_data, labels


def main():
    """Train initial models"""
    print("=" * 60)
    print("Initial Model Training")
    print("=" * 60)

    # Create AI engine
    api_key = "dummy_key_for_training"
    engine = AdvancedAIEngine(api_key)

    print(f"\nAvailable models: {engine.available_models}")

    # Generate training data
    training_data, labels = generate_synthetic_training_data(500)

    # Train models
    print("\nTraining models...")
    engine.train_models(training_data, labels)

    print("\n" + "=" * 60)
    print("Training Complete!")
    print("=" * 60)
    print("\nModels saved to: models/ml_enhanced/")
    print("\nNext steps:")
    print("  1. Test predictions with: python phase2_lite.py")
    print("  2. Generate report with: python generate_fast_reports.py")
    print("  3. Collect real historical data for retraining")

    # Quick test
    print("\n" + "=" * 60)
    print("Quick Test Prediction")
    print("=" * 60)

    test_match = {
        "home_team": {"name": "FC Barcelona", "strength": 0.9},
        "away_team": {"name": "Test Team", "strength": 0.5},
        "home_form": {
            "win_rate": 0.75,
            "goals_per_game": 2.3,
            "goals_conceded_per_game": 0.8,
        },
        "away_form": {
            "win_rate": 0.40,
            "goals_per_game": 1.1,
            "goals_conceded_per_game": 1.5,
        },
        "h2h": {"home_wins": 0.60, "draws": 0.25, "away_wins": 0.15},
        "is_derby": 0,
        "league_position_diff": 10,
        "weather": {"temperature": 20.0, "precipitation": 0.0},
        "league": "la-liga",
    }

    result = engine.enhanced_prediction(test_match, "la-liga")
    print("\nTest match prediction:")
    print(f"  Home Win: {result['home_win_prob']:.1%}")
    print(f"  Draw: {result['draw_prob']:.1%}")
    print(f"  Away Win: {result['away_win_prob']:.1%}")
    print(f"  Confidence: {result['confidence']:.1%}")
    print(f"  Models Used: {result.get('models_used', [])}")
    print(f"  Enhanced: {result['enhanced']}")


if __name__ == "__main__":
    main()
