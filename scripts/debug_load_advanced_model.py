from pathlib import Path
import sys, os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.models.advanced_predictor import AdvancedAIMLPredictor

models = list(Path("models/advanced").glob("*"))
print("Found models:", models)
if not models:
    print("No models found")
    raise SystemExit(1)
# pick a joblib or first
m = sorted(models, key=lambda p: p.name)[-1]
print("Using model:", m)
model = AdvancedAIMLPredictor(m)
# make a sample features dict
sample = {
    "expected_home_goals": 1.5,
    "expected_away_goals": 1.0,
    "home_win_prob": 0.5,
    "draw_prob": 0.3,
    "away_win_prob": 0.2,
    "confidence": 0.8,
}
print("Features:", sample)
print("Prediction:", model.predict_with_ml_ensemble(sample))
