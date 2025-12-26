"""Script to build processed features for advanced model training"""

from pathlib import Path
import sys, os

# Ensure repo root is on sys.path for local runs
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.data.advanced_model_features import build_sample_dataset

if __name__ == "__main__":
    out = Path("data/processed/advanced_model/sample_train.csv")
    build_sample_dataset(out, augment_per_match=40)
