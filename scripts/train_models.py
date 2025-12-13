#!/usr/bin/env python3
"""
Train models using the ML enhancer from processed historical dataset
"""
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))



def main():
    # Import ML enhancer after sys.path insert so app imports resolve cleanly
    from app.models.ml_enhancer import MachineLearningEnhancer

    enhancer = MachineLearningEnhancer()
    result = enhancer.train_from_processed_dataset()
    print("Train from processed dataset result:", result)

if __name__ == '__main__':
    main()
