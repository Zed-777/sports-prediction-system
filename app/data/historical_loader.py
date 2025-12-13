#!/usr/bin/env python3
"""
Historical Data Loader
- Loads processed historical dataset produced by scripts/collect_historical_data.py
- Provides API to get features and labels for training
"""

import json
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).parent.parent.parent
PROCESSED_DIR = ROOT / 'data' / 'processed' / 'historical'


def load_processed_dataset(filename: str = 'historical_dataset.json') -> tuple[list[dict[str, Any]], list[int]]:
    path = PROCESSED_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Processed historical dataset not found at {path}")
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    processed = data.get('processed', [])
    labels = data.get('labels', [])
    return processed, labels


def dataset_to_arrays(processed: list[dict[str, Any]]) -> tuple[np.ndarray, list[int]]:
    """Convert processed dataset to feature matrix and labels
    Uses the same 20 feature format as AdvancedAIEngine._extract_features
    """
    X = []
    y = []
    for sample in processed:
        f = sample['features']
        feature_vector = [
            float(f.get('home_strength', 0.5)),
            float(f.get('away_strength', 0.5)),
            float(f.get('strength_diff', 0.0)),
            float(f.get('home_win_rate', 0.0)),
            float(f.get('away_win_rate', 0.0)),
            float(f.get('home_avg_goals', 0.0)),
            float(f.get('away_avg_goals', 0.0)),
            float(f.get('home_recent_form', 0.5)),
            float(f.get('away_recent_form', 0.5)),
            float(f['h2h'].get('home_wins', 0)),
            float(f['h2h'].get('draws', 0)),
            float(f['h2h'].get('away_wins', 0)),
            1.0,  # home advantage
            float(f.get('is_derby', 0)),
            float(f.get('league_position_diff', 0)),
            float(f.get('weather', {}).get('temperature', 18.0) / 40.0),
            float(f.get('weather', {}).get('precipitation', 0.0) / 10.0),
            0.5,  # placeholder for referee bias
            0.5,  # placeholder for referee strictness
            1.0 if 'la-liga' in f.get('league', '').lower() else 0.5
        ]
        X.append(feature_vector)
        y.append(int(sample['label']))
    return np.array(X), y


if __name__ == '__main__':
    print("Quick loader test: loading historical dataset...")
    processed, labels = load_processed_dataset()
    X, y = dataset_to_arrays(processed[:10])
    print(f"Loaded {len(processed)} samples, sample features shape: {X.shape}")

