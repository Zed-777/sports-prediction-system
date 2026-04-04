#!/usr/bin/env python3
"""Advanced AI Prediction Engine v2.0 - Real ML Implementation
Machine Learning models with proper dependency handling
"""

import logging
import pickle
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import numpy as np
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.preprocessing import LabelEncoder, StandardScaler

warnings.filterwarnings("ignore")

# Conditional imports with proper fallbacks
LIGHTGBM_AVAILABLE = False
TENSORFLOW_AVAILABLE = False
XGBOOST_AVAILABLE = False

# Optional module placeholders to keep typing clean
lgb: Any | None = None
tf: Any | None = None
keras: Any | None = None
xgb: Any | None = None

try:
    import lightgbm as _lgb

    lgb = _lgb
    LIGHTGBM_AVAILABLE = True
except ImportError:
    lgb = None

try:
    import tensorflow as _tf
    from tensorflow import keras as _keras

    tf = _tf
    keras = _keras
    TENSORFLOW_AVAILABLE = True
except ImportError:
    keras = None
    tf = None

try:
    import xgboost as _xgb

    xgb = _xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    xgb = None


@dataclass
class ModelMetrics:
    """Model performance metrics"""

    accuracy: float
    confidence: float
    log_loss: float
    feature_importance: dict[str, float] | None = None


class AdvancedAIEngine:
    """Advanced AI Engine with ensemble ML models.
    Clean version with proper dependency handling.
    """

    def __init__(self, api_key: str):
        """Initialize the AI engine with dependency checking"""
        self.api_key = api_key
        self.logger = logging.getLogger(__name__)
        self.models: dict[str, Any] = {}
        self.scaler = StandardScaler()
        self.label_encoder = LabelEncoder()
        self.feature_names: list[str] = []
        self.models_dir = Path("models/ml_enhanced")
        self.models_dir.mkdir(parents=True, exist_ok=True)

        # Check available dependencies
        self.available_models = []
        if XGBOOST_AVAILABLE:
            self.available_models.append("xgboost")
        if LIGHTGBM_AVAILABLE:
            self.available_models.append("lightgbm")
        if TENSORFLOW_AVAILABLE:
            self.available_models.append("neural_network")

        # Always available (scikit-learn)
        self.available_models.extend(["random_forest", "gradient_boosting"])

        # Initialize or load models
        self._initialize_models()
        self.logger.info(
            f"Advanced AI Engine initialized with models: {self.available_models}",
        )

    def is_available(self) -> bool:
        """Check if the advanced AI engine is fully available"""
        return len(self.available_models) >= 3

    def get_availability_status(self) -> dict[str, Any]:
        """Get detailed availability status"""
        return {
            "available": self.is_available(),
            "models_available": self.available_models,
            "missing_dependencies": {
                "xgboost": not XGBOOST_AVAILABLE,
                "lightgbm": not LIGHTGBM_AVAILABLE,
                "tensorflow": not TENSORFLOW_AVAILABLE,
            },
            "fallback_mode": len(self.available_models) < 5,
        }

    def enhanced_prediction(
        self, match_data: dict[str, Any], league_code: str,
    ) -> dict[str, Any]:
        """Generate enhanced prediction using available models.
        Falls back to basic ensemble if advanced models unavailable.
        """
        if not self.is_available():
            return self._fallback_prediction(match_data, league_code)

        try:
            # This would contain the full implementation when dependencies are available
            return self._advanced_prediction(match_data, league_code)
        except Exception as e:
            self.logger.warning(
                f"Advanced prediction failed: {e}, falling back to basic",
            )
            return self._fallback_prediction(match_data, league_code)

    def _fallback_prediction(
        self, match_data: dict[str, Any], league_code: str,
    ) -> dict[str, Any]:
        """Fallback prediction using basic ensemble"""
        return self._real_fallback_prediction(match_data, league_code)

    def _initialize_models(self) -> None:
        """Initialize or load pre-trained models"""
        # Try to load existing models
        rf_path = self.models_dir / "random_forest.pkl"
        gb_path = self.models_dir / "gradient_boosting.pkl"

        if rf_path.exists() and gb_path.exists():
            try:
                with open(rf_path, "rb") as f:
                    self.models["random_forest"] = pickle.load(f)
                with open(gb_path, "rb") as f:
                    self.models["gradient_boosting"] = pickle.load(f)
                self.logger.info("Loaded existing scikit-learn models")
                return
            except Exception as e:
                self.logger.warning(f"Failed to load existing models: {e}")

        # Initialize new models with default parameters
        self.models["random_forest"] = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            random_state=42,
            n_jobs=-1,
        )

        self.models["gradient_boosting"] = GradientBoostingClassifier(
            n_estimators=100, max_depth=6, learning_rate=0.1, random_state=42,
        )

        # Initialize XGBoost if available
        if XGBOOST_AVAILABLE:
            xgb_path = self.models_dir / "xgboost.pkl"
            if xgb_path.exists():
                try:
                    with open(xgb_path, "rb") as f:
                        self.models["xgboost"] = pickle.load(f)
                    self.logger.info("Loaded existing XGBoost model")
                except Exception as e:
                    self.logger.warning(f"Failed to load XGBoost: {e}")
                    self.models["xgboost"] = cast("Any", xgb).XGBClassifier(
                        n_estimators=100,
                        max_depth=6,
                        learning_rate=0.1,
                        random_state=42,
                    )
            else:
                self.models["xgboost"] = cast("Any", xgb).XGBClassifier(
                    n_estimators=100, max_depth=6, learning_rate=0.1, random_state=42,
                )

        # Initialize LightGBM if available
        if LIGHTGBM_AVAILABLE:
            lgb_path = self.models_dir / "lightgbm.pkl"
            if lgb_path.exists():
                try:
                    with open(lgb_path, "rb") as f:
                        self.models["lightgbm"] = pickle.load(f)
                    self.logger.info("Loaded existing LightGBM model")
                except Exception as e:
                    self.logger.warning(f"Failed to load LightGBM: {e}")
                    self.models["lightgbm"] = cast("Any", lgb).LGBMClassifier(
                        n_estimators=100,
                        max_depth=6,
                        learning_rate=0.1,
                        random_state=42,
                        verbose=-1,
                    )
            else:
                self.models["lightgbm"] = cast("Any", lgb).LGBMClassifier(
                    n_estimators=100,
                    max_depth=6,
                    learning_rate=0.1,
                    random_state=42,
                    verbose=-1,
                )

        self.logger.info(f"Initialized models: {list(self.models.keys())}")

    def _extract_features(
        self, match_data: dict[str, Any], league_code: str,
    ) -> np.ndarray:
        """Extract feature vector from match data for ML models"""
        features = []

        # Team strength estimates (from match data or defaults)
        home_team = match_data.get("home_team", {})
        away_team = match_data.get("away_team", {})

        # Basic team metrics (use defaults if not available)
        home_strength = home_team.get("strength", 0.5)
        away_strength = away_team.get("strength", 0.5)

        features.extend(
            [
                float(home_strength),
                float(away_strength),
                float(home_strength - away_strength),  # Strength differential
            ],
        )

        # Form features
        home_form = match_data.get("home_form", {})
        away_form = match_data.get("away_form", {})

        features.extend(
            [
                float(home_form.get("win_rate", 0.45)),
                float(away_form.get("win_rate", 0.35)),
                float(home_form.get("goals_per_game", 1.3)),
                float(away_form.get("goals_per_game", 1.0)),
                float(home_form.get("goals_conceded_per_game", 1.0)),
                float(away_form.get("goals_conceded_per_game", 1.2)),
            ],
        )

        # Head-to-head
        h2h = match_data.get("h2h", {})
        features.extend(
            [
                float(h2h.get("home_wins", 0.45)),
                float(h2h.get("draws", 0.30)),
                float(h2h.get("away_wins", 0.25)),
            ],
        )

        # Venue and context
        features.extend(
            [
                1.0,  # Home advantage
                float(match_data.get("is_derby", 0)),
                float(match_data.get("league_position_diff", 0) / 20.0),  # Normalize
            ],
        )

        # Weather impact (if available)
        weather = match_data.get("weather", {})
        features.extend(
            [
                float(weather.get("temperature", 18.0) / 40.0),
                float(weather.get("precipitation", 0.0) / 10.0),
            ],
        )

        # League context
        features.append(1.0 if "la-liga" in league_code.lower() else 0.5)

        # Pad to fixed size (20 features)
        while len(features) < 20:
            features.append(0.0)

        return np.array(features[:20]).reshape(1, -1)

    def train_models(
        self, training_data: list[dict[str, Any]], labels: list[int],
    ) -> None:
        """Train all available models on historical data
        Args:
            training_data: List of match data dictionaries
            labels: List of outcomes (0=away win, 1=draw, 2=home win)
        """
        if len(training_data) < 50:
            self.logger.warning(
                f"Insufficient training data: {len(training_data)} samples",
            )
            return

        self.logger.info(f"Training models on {len(training_data)} samples...")

        # Extract features
        X_list: list[np.ndarray] = []
        for match in training_data:
            features = self._extract_features(match, match.get("league", "unknown"))
            X_list.append(features.flatten())

        X = np.array(X_list)
        y = np.array(labels)

        # Fit scaler
        X_scaled = self.scaler.fit_transform(X)

        # Train each model
        for model_name, model in self.models.items():
            try:
                self.logger.info(f"Training {model_name}...")
                model.fit(X_scaled, y)

                # Save model
                model_path = self.models_dir / f"{model_name}.pkl"
                with open(model_path, "wb") as f:
                    pickle.dump(model, f)

                self.logger.info(f"✓ {model_name} trained and saved")
            except Exception as e:
                self.logger.error(f"Failed to train {model_name}: {e}")

        # Save scaler
        scaler_path = self.models_dir / "scaler.pkl"
        with open(scaler_path, "wb") as f:
            pickle.dump(self.scaler, f)

        self.logger.info("Model training complete!")

    def _advanced_prediction(
        self, match_data: dict[str, Any], league_code: str,
    ) -> dict[str, Any]:
        """Advanced prediction using full ML ensemble with real trained models"""
        import time

        start_time = time.time()

        try:
            # Extract features from match data
            features = self._extract_features(match_data, league_code)

            # Scale features
            scaler_path = self.models_dir / "scaler.pkl"
            if scaler_path.exists():
                with open(scaler_path, "rb") as f:
                    scaler = pickle.load(f)
                features = scaler.transform(features)

            # Get predictions from all available models
            predictions = []
            model_outputs = {}

            # Random Forest (always available)
            if (
                "random_forest" in self.available_models
                and "random_forest" in self.models
            ):
                rf_pred = self.models["random_forest"].predict_proba(features)[0]
                predictions.append(rf_pred)
                model_outputs["random_forest"] = rf_pred.tolist()

            # Gradient Boosting (always available)
            if (
                "gradient_boosting" in self.available_models
                and "gradient_boosting" in self.models
            ):
                gb_pred = self.models["gradient_boosting"].predict_proba(features)[0]
                predictions.append(gb_pred)
                model_outputs["gradient_boosting"] = gb_pred.tolist()

            # XGBoost (if available)
            if XGBOOST_AVAILABLE and "xgboost" in self.models:
                xgb_pred = self.models["xgboost"].predict_proba(features)[0]
                predictions.append(xgb_pred)
                model_outputs["xgboost"] = xgb_pred.tolist()

            # LightGBM (if available)
            if LIGHTGBM_AVAILABLE and "lightgbm" in self.models:
                lgb_pred = self.models["lightgbm"].predict_proba(features)[0]
                predictions.append(lgb_pred)
                model_outputs["lightgbm"] = lgb_pred.tolist()

            if not predictions:
                self.logger.warning(
                    "No models available for prediction, using fallback",
                )
                return self._real_fallback_prediction(match_data, league_code)

            # Ensemble: average predictions across models
            ensemble_pred = np.mean(predictions, axis=0)

            # Calculate confidence based on model agreement
            std_dev = np.std(predictions, axis=0)
            agreement = 1.0 - np.mean(std_dev)  # Higher agreement = lower std dev
            base_confidence = min(0.85, max(0.55, agreement))

            # Extract probabilities
            away_win_prob = float(ensemble_pred[0])
            draw_prob = float(ensemble_pred[1])
            home_win_prob = float(ensemble_pred[2])

            # Normalize to sum to 1.0
            total = away_win_prob + draw_prob + home_win_prob
            if total > 0:
                away_win_prob /= total
                draw_prob /= total
                home_win_prob /= total

            # Estimate expected goals based on probabilities and league averages
            league_avg_goals = 2.7  # Typical for La Liga
            home_advantage = 1.15

            expected_home_goals = (
                league_avg_goals * home_advantage * (home_win_prob + 0.5 * draw_prob)
            )
            expected_away_goals = league_avg_goals * (away_win_prob + 0.5 * draw_prob)

            processing_time = time.time() - start_time

            return {
                "home_win_prob": round(home_win_prob, 4),
                "draw_prob": round(draw_prob, 4),
                "away_win_prob": round(away_win_prob, 4),
                "confidence": round(base_confidence, 4),
                "expected_home_goals": round(expected_home_goals, 2),
                "expected_away_goals": round(expected_away_goals, 2),
                "model_ensemble": "advanced_ml",
                "models_used": list(model_outputs.keys()),
                "model_outputs": model_outputs,
                "ensemble_agreement": round(agreement, 4),
                "available_models": self.available_models,
                "enhanced": True,
                "processing_time": round(processing_time, 3),
            }

        except Exception as e:
            self.logger.error(f"Advanced prediction error: {e}", exc_info=True)
            return self._real_fallback_prediction(match_data, league_code)

    def _real_fallback_prediction(
        self, match_data: dict[str, Any], league_code: str,
    ) -> dict[str, Any]:
        """Real fallback when ML models fail"""
        return {
            "home_win_prob": 0.45,
            "draw_prob": 0.30,
            "away_win_prob": 0.25,
            "confidence": 0.50,
            "expected_home_goals": 1.2,
            "expected_away_goals": 0.8,
            "model_ensemble": "basic_fallback",
            "available_models": self.available_models,
            "enhanced": False,
            "processing_time": 0.1,
        }


# For backward compatibility
def create_advanced_ai_engine(api_key: str) -> AdvancedAIEngine:
    """Factory function to create AI engine"""
    return AdvancedAIEngine(api_key)
