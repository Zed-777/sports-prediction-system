"""Inference wrapper for the advanced model.

Implements a minimal AIMLPredictor-compatible interface for later integration.
"""

from pathlib import Path
import json


class AdvancedAIMLPredictor:
    def __init__(self, model_path: str | Path | None = None):
        self.model_path = model_path
        self.model = None
        if model_path:
            self._load_model(Path(model_path))

    def _load_model(self, p: Path):
        # Load model from joblib or LightGBM file
        if not p.exists():
            raise FileNotFoundError(f"Model artifact not found at {p}")
        from pathlib import Path as _P

        p = _P(p)
        if p.suffix in (".joblib", ".pkl"):
            import joblib

            self.model = joblib.load(p)
            self.model_type = "sklearn"
        elif p.suffix in (".txt", ".bin"):
            # assume LightGBM model
            try:
                import lightgbm as lgb

                self.model = lgb.Booster(model_file=str(p))
                self.model_type = "lightgbm"
            except Exception:
                raise RuntimeError("LightGBM not available to load model")
        else:
            # fallback - store path
            self.model = str(p)
            self.model_type = "unknown"

    def extract_advanced_features(self, match_info: dict) -> dict:
        # Minimal canonicalizer: produce numeric features similar to training CSV
        # Expects match_info to contain keys: expected_home_goals, expected_away_goals, home_win_prob, draw_prob, away_win_prob, confidence
        features = {
            "expected_home_goals": float(
                match_info.get("expected_home_goals", 0.0) or 0.0
            ),
            "expected_away_goals": float(
                match_info.get("expected_away_goals", 0.0) or 0.0
            ),
            "home_win_prob": float(
                match_info.get(
                    "home_win_prob", match_info.get("home_win_probability", 0.0)
                )
                or 0.0
            ),
            "draw_prob": float(
                match_info.get("draw_prob", match_info.get("draw_probability", 0.0))
                or 0.0
            ),
            "away_win_prob": float(
                match_info.get(
                    "away_win_prob", match_info.get("away_win_probability", 0.0)
                )
                or 0.0
            ),
            "confidence": float(
                match_info.get(
                    "confidence", match_info.get("report_accuracy_probability", 0.0)
                )
                or 0.0
            ),
        }
        return features

    def predict_with_ml_ensemble(self, features: dict) -> dict:
        # Predict probabilities using loaded model
        if self.model is None:
            raise RuntimeError("No model loaded")

        import numpy as np

        X = [
            [
                features.get("expected_home_goals", 0.0),
                features.get("expected_away_goals", 0.0),
                features.get("home_win_prob", 0.0),
                features.get("draw_prob", 0.0),
                features.get("away_win_prob", 0.0),
                features.get("confidence", 0.0),
            ]
        ]

        if getattr(self, "model_type", "") == "sklearn":
            probs = self.model.predict_proba(X)[0]
            return {
                "home_win_prob": float(probs[0]),
                "draw_prob": float(probs[1]),
                "away_win_prob": float(probs[2]),
                "meta": {"model": str(self.model_path)},
            }
        elif getattr(self, "model_type", "") == "lightgbm":
            probs = self.model.predict(X)
            if probs.shape[-1] == 3:
                return {
                    "home_win_prob": float(probs[0][0]),
                    "draw_prob": float(probs[0][1]),
                    "away_win_prob": float(probs[0][2]),
                    "meta": {"model": str(self.model_path)},
                }
            else:
                raise RuntimeError("Unexpected LightGBM prediction shape")
        else:
            raise RuntimeError("Unsupported model type for prediction")
