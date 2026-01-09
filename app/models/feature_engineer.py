#!/usr/bin/env python3
"""
Advanced Feature Engineering System v1.0
State-of-the-art feature extraction for sports prediction with:
- Team/player embeddings for latent representation learning
- Fourier features for periodic patterns (seasonal, day-of-week)
- Polynomial feature interactions
- Target encoding with Bayesian smoothing
- Time-decay weighted aggregations
- Momentum and trend indicators
- Graph-based team similarity features
"""

import json
import logging
import math
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy import stats as scipy_stats


@dataclass
class FeatureSet:
    """Complete feature set for a match prediction"""

    static_features: np.ndarray
    temporal_features: np.ndarray
    interaction_features: np.ndarray
    embedding_features: np.ndarray
    feature_names: List[str]
    feature_importances: Dict[str, float] = field(default_factory=dict)

    def to_flat_array(self) -> np.ndarray:
        """Concatenate all features into a single array"""
        return np.concatenate(
            [
                self.static_features.flatten(),
                self.temporal_features.flatten(),
                self.interaction_features.flatten(),
                self.embedding_features.flatten(),
            ]
        )


class TeamEmbedding:
    """
    Learned team embeddings for capturing latent team characteristics.
    Uses matrix factorization of historical match results.
    """

    def __init__(self, embedding_dim: int = 16, learning_rate: float = 0.01):
        self.embedding_dim = embedding_dim
        self.learning_rate = learning_rate
        self.team_embeddings: Dict[str, np.ndarray] = {}
        self.team_biases: Dict[str, float] = {}
        self.global_mean = 0.0

    def get_embedding(self, team_name: str) -> np.ndarray:
        """Get or create embedding for a team"""
        if team_name not in self.team_embeddings:
            # Initialize with small random values
            self.team_embeddings[team_name] = np.random.randn(self.embedding_dim) * 0.1
            self.team_biases[team_name] = 0.0
        return self.team_embeddings[team_name]

    def update_from_match(
        self, home_team: str, away_team: str, home_goals: int, away_goals: int
    ):
        """Update embeddings based on match result using matrix factorization"""
        home_emb = self.get_embedding(home_team)
        away_emb = self.get_embedding(away_team)

        # Predict goal difference
        predicted = (
            np.dot(home_emb, away_emb)
            + self.team_biases.get(home_team, 0)
            - self.team_biases.get(away_team, 0)
            + self.global_mean
        )

        actual = home_goals - away_goals
        error = actual - predicted

        # Gradient descent update
        lr = self.learning_rate

        # Update embeddings
        home_grad = lr * error * away_emb
        away_grad = lr * error * home_emb

        self.team_embeddings[home_team] = home_emb + home_grad
        self.team_embeddings[away_team] = away_emb - away_grad  # Negative because away

        # Update biases
        self.team_biases[home_team] = self.team_biases.get(home_team, 0) + lr * error
        self.team_biases[away_team] = self.team_biases.get(away_team, 0) - lr * error

    def team_similarity(self, team1: str, team2: str) -> float:
        """Calculate cosine similarity between two teams"""
        emb1 = self.get_embedding(team1)
        emb2 = self.get_embedding(team2)

        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(np.dot(emb1, emb2) / (norm1 * norm2))

    def predict_goal_diff(self, home_team: str, away_team: str) -> float:
        """Predict goal difference using embeddings"""
        home_emb = self.get_embedding(home_team)
        away_emb = self.get_embedding(away_team)

        return (
            np.dot(home_emb, away_emb)
            + self.team_biases.get(home_team, 0)
            - self.team_biases.get(away_team, 0)
            + self.global_mean
        )


class FourierFeatures:
    """
    Fourier features for capturing periodic patterns.
    Transforms temporal features into sine/cosine components.
    """

    def __init__(self, num_frequencies: int = 5):
        self.num_frequencies = num_frequencies

    def encode_periodic(self, value: float, period: float) -> np.ndarray:
        """
        Encode a periodic value using Fourier features.

        Args:
            value: Current value (e.g., day of year)
            period: Period length (e.g., 365 for yearly)

        Returns:
            Array of [sin1, cos1, sin2, cos2, ...] features
        """
        features = []
        for freq in range(1, self.num_frequencies + 1):
            angle = 2 * math.pi * freq * value / period
            features.extend([math.sin(angle), math.cos(angle)])
        return np.array(features)

    def encode_datetime(self, dt: datetime) -> Dict[str, np.ndarray]:
        """
        Encode datetime with multiple periodic patterns.

        Returns:
            Dict with keys: 'day_of_week', 'day_of_year', 'month', 'hour'
        """
        return {
            "day_of_week": self.encode_periodic(dt.weekday(), 7),
            "day_of_year": self.encode_periodic(dt.timetuple().tm_yday, 365),
            "month": self.encode_periodic(dt.month, 12),
            "hour": (
                self.encode_periodic(dt.hour, 24)
                if dt.hour
                else np.zeros(self.num_frequencies * 2)
            ),
        }


class TargetEncoder:
    """
    Bayesian target encoding for categorical features.
    Applies shrinkage towards global mean based on sample size.
    """

    def __init__(self, min_samples_leaf: int = 10, smoothing: float = 10.0):
        self.min_samples_leaf = min_samples_leaf
        self.smoothing = smoothing
        self.encodings: Dict[str, Dict[str, float]] = {}
        self.global_means: Dict[str, float] = {}
        self.category_counts: Dict[str, Dict[str, int]] = {}

    def fit(
        self,
        category_values: List[str],
        targets: List[float],
        category_name: str = "default",
    ):
        """
        Fit target encoder on training data.

        Args:
            category_values: List of category values
            targets: Corresponding target values
            category_name: Name of the categorical feature
        """
        self.global_means[category_name] = np.mean(targets)
        self.encodings[category_name] = {}
        self.category_counts[category_name] = {}

        # Group by category
        category_sums: Dict[str, float] = {}
        category_counts: Dict[str, int] = {}

        for cat, target in zip(category_values, targets):
            if cat not in category_sums:
                category_sums[cat] = 0.0
                category_counts[cat] = 0
            category_sums[cat] += target
            category_counts[cat] += 1

        # Calculate smoothed encodings
        global_mean = self.global_means[category_name]

        for cat in category_sums:
            n = category_counts[cat]
            cat_mean = category_sums[cat] / n

            # Bayesian smoothing towards global mean
            # More samples = trust category mean more
            smoothing_factor = 1 / (
                1 + np.exp(-(n - self.min_samples_leaf) / self.smoothing)
            )

            self.encodings[category_name][cat] = (
                smoothing_factor * cat_mean + (1 - smoothing_factor) * global_mean
            )
            self.category_counts[category_name][cat] = n

    def transform(self, category_value: str, category_name: str = "default") -> float:
        """Transform a category value to its target encoding"""
        if category_name not in self.encodings:
            return 0.5  # Default

        if category_value in self.encodings[category_name]:
            return self.encodings[category_name][category_value]

        return self.global_means.get(category_name, 0.5)


class MomentumIndicator:
    """
    Technical analysis-style momentum indicators for form tracking.
    Includes RSI, MACD-like features, and trend strength.
    """

    def __init__(self):
        pass

    def calculate_rsi(self, values: List[float], period: int = 5) -> float:
        """
        Calculate Relative Strength Index for form values.
        RSI > 70 = strong form, RSI < 30 = poor form
        """
        if len(values) < 2:
            return 50.0

        gains = []
        losses = []

        for i in range(1, min(len(values), period + 1)):
            change = values[i] - values[i - 1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))

        avg_gain = np.mean(gains) if gains else 0
        avg_loss = np.mean(losses) if losses else 0

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return float(rsi)

    def calculate_macd(
        self, values: List[float], fast_period: int = 3, slow_period: int = 6
    ) -> Tuple[float, float]:
        """
        Calculate MACD-like indicator for form momentum.
        Returns (macd_value, signal_line)
        """
        if len(values) < slow_period:
            return 0.0, 0.0

        # EMA calculation
        def ema(data: List[float], period: int) -> float:
            if len(data) < period:
                return np.mean(data)
            alpha = 2 / (period + 1)
            result = data[0]
            for val in data[1:period]:
                result = alpha * val + (1 - alpha) * result
            return result

        fast_ema = ema(values, fast_period)
        slow_ema = ema(values, slow_period)
        macd = fast_ema - slow_ema

        # Signal line (EMA of MACD with period 2)
        signal = macd * 0.5  # Simplified

        return float(macd), float(signal)

    def calculate_trend_strength(self, values: List[float]) -> Tuple[float, str]:
        """
        Calculate trend strength and direction using linear regression.
        Returns (r_squared, direction)
        """
        if len(values) < 3:
            return 0.0, "neutral"

        x = np.arange(len(values))
        y = np.array(values)

        # Linear regression
        slope, intercept, r_value, p_value, std_err = scipy_stats.linregress(x, y)

        r_squared = r_value**2
        direction = "up" if slope > 0.01 else ("down" if slope < -0.01 else "neutral")

        return float(r_squared), direction


class PolynomialInteractions:
    """
    Generate polynomial feature interactions up to degree N.
    With feature selection based on importance.
    """

    def __init__(self, degree: int = 2, max_features: int = 50):
        self.degree = degree
        self.max_features = max_features
        self.interaction_names: List[str] = []

    def generate(self, features: Dict[str, float]) -> Tuple[np.ndarray, List[str]]:
        """
        Generate polynomial interactions.

        Args:
            features: Dict of feature_name -> value

        Returns:
            (interaction_array, interaction_names)
        """
        names = list(features.keys())
        values = np.array(list(features.values()))
        n = len(values)

        interactions = []
        interaction_names = []

        # Degree 2 interactions
        if self.degree >= 2:
            for i in range(n):
                for j in range(i, n):
                    interaction = values[i] * values[j]
                    interactions.append(interaction)
                    if i == j:
                        interaction_names.append(f"{names[i]}^2")
                    else:
                        interaction_names.append(f"{names[i]}*{names[j]}")

        # Degree 3 interactions (selective - only with high-importance features)
        if self.degree >= 3 and n <= 10:
            for i in range(min(n, 5)):  # Top 5 features only
                for j in range(i, min(n, 5)):
                    for k in range(j, min(n, 5)):
                        interaction = values[i] * values[j] * values[k]
                        interactions.append(interaction)
                        interaction_names.append(f"{names[i]}*{names[j]}*{names[k]}")

        # Limit to max features
        if len(interactions) > self.max_features:
            interactions = interactions[: self.max_features]
            interaction_names = interaction_names[: self.max_features]

        self.interaction_names = interaction_names
        return np.array(interactions), interaction_names


class TimeDecayAggregator:
    """
    Aggregate historical data with exponential time decay.
    More recent observations weighted more heavily.
    """

    def __init__(self, half_life_days: float = 30.0):
        """
        Args:
            half_life_days: Days until weight decays to 50%
        """
        self.half_life_days = half_life_days
        self.decay_rate = math.log(2) / half_life_days

    def aggregate(self, values: List[float], days_ago: List[float]) -> float:
        """
        Calculate time-weighted average.

        Args:
            values: Historical values
            days_ago: How many days ago each value occurred

        Returns:
            Time-weighted average
        """
        if not values:
            return 0.0

        weights = [math.exp(-self.decay_rate * d) for d in days_ago]
        total_weight = sum(weights)

        if total_weight == 0:
            return np.mean(values)

        weighted_sum = sum(v * w for v, w in zip(values, weights))
        return weighted_sum / total_weight

    def aggregate_with_variance(
        self, values: List[float], days_ago: List[float]
    ) -> Tuple[float, float]:
        """
        Calculate time-weighted mean and variance.

        Returns:
            (weighted_mean, weighted_variance)
        """
        if not values or len(values) < 2:
            return np.mean(values) if values else 0.0, 0.0

        weights = np.array([math.exp(-self.decay_rate * d) for d in days_ago])
        weights = weights / np.sum(weights)  # Normalize

        values_arr = np.array(values)

        weighted_mean = np.sum(weights * values_arr)
        weighted_var = np.sum(weights * (values_arr - weighted_mean) ** 2)

        return float(weighted_mean), float(weighted_var)


class AdvancedFeatureEngineer:
    """
    Complete feature engineering pipeline combining all advanced techniques.
    """

    def __init__(self, models_dir: str = "models/features"):
        self.logger = logging.getLogger(__name__)
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)

        # Initialize components
        self.team_embeddings = TeamEmbedding(embedding_dim=16)
        self.fourier = FourierFeatures(num_frequencies=3)
        self.target_encoder = TargetEncoder(min_samples_leaf=5, smoothing=5.0)
        self.momentum = MomentumIndicator()
        self.poly_interactions = PolynomialInteractions(degree=2, max_features=30)
        self.time_decay = TimeDecayAggregator(half_life_days=30.0)

        # Load saved state
        self._load_state()

        self.logger.info("Advanced Feature Engineer initialized")

    def engineer_features(
        self, match_data: Dict[str, Any], match_datetime: Optional[datetime] = None
    ) -> FeatureSet:
        """
        Generate complete feature set for a match.

        Args:
            match_data: Raw match data dictionary
            match_datetime: Datetime of the match

        Returns:
            Complete FeatureSet with all engineered features
        """
        feature_names = []

        # 1. Static features (basic team stats)
        static_features, static_names = self._extract_static_features(match_data)
        feature_names.extend(static_names)

        # 2. Embedding features
        embedding_features, embedding_names = self._extract_embedding_features(
            match_data
        )
        feature_names.extend(embedding_names)

        # 3. Temporal features (Fourier encoded time)
        temporal_features, temporal_names = self._extract_temporal_features(
            match_data, match_datetime
        )
        feature_names.extend(temporal_names)

        # 4. Momentum indicators
        momentum_features, momentum_names = self._extract_momentum_features(match_data)
        static_features = np.concatenate([static_features, momentum_features])
        feature_names.extend(momentum_names)

        # 5. Polynomial interactions (on key features only)
        key_features = {
            "home_strength": match_data.get("home_strength", 0.5),
            "away_strength": match_data.get("away_strength", 0.5),
            "home_form": match_data.get("home_form", {}).get("form_score", 50) / 100,
            "away_form": match_data.get("away_form", {}).get("form_score", 50) / 100,
            "home_xg": match_data.get("home_xg", 1.2) / 3.0,
            "away_xg": match_data.get("away_xg", 1.0) / 3.0,
        }
        interaction_features, interaction_names = self.poly_interactions.generate(
            key_features
        )
        feature_names.extend(interaction_names)

        return FeatureSet(
            static_features=static_features,
            temporal_features=temporal_features,
            interaction_features=interaction_features,
            embedding_features=embedding_features,
            feature_names=feature_names,
        )

    def _extract_static_features(
        self, match_data: Dict[str, Any]
    ) -> Tuple[np.ndarray, List[str]]:
        """Extract static numerical features"""
        features = []
        names = []

        # Team strength metrics
        features.append(match_data.get("home_elo", 1500) / 2500)
        names.append("home_elo_norm")
        features.append(match_data.get("away_elo", 1500) / 2500)
        names.append("away_elo_norm")

        elo_diff = (
            match_data.get("home_elo", 1500) - match_data.get("away_elo", 1500)
        ) / 400
        features.append(elo_diff)
        names.append("elo_diff_norm")

        # Attack/defense ratings
        features.append(match_data.get("home_attack", 0.5))
        names.append("home_attack")
        features.append(match_data.get("home_defense", 0.5))
        names.append("home_defense")
        features.append(match_data.get("away_attack", 0.5))
        names.append("away_attack")
        features.append(match_data.get("away_defense", 0.5))
        names.append("away_defense")

        # Form scores
        home_form = match_data.get("home_form", {})
        away_form = match_data.get("away_form", {})
        features.append(home_form.get("form_score", 50) / 100)
        names.append("home_form_score")
        features.append(away_form.get("form_score", 50) / 100)
        names.append("away_form_score")

        # xG metrics
        features.append(match_data.get("home_xg", 1.2) / 3.0)
        names.append("home_xg_norm")
        features.append(match_data.get("away_xg", 1.0) / 3.0)
        names.append("away_xg_norm")

        # Goal metrics
        features.append(match_data.get("home_goals_per_game", 1.3) / 3.0)
        names.append("home_gpg_norm")
        features.append(match_data.get("away_goals_per_game", 1.0) / 3.0)
        names.append("away_gpg_norm")
        features.append(match_data.get("home_conceded_per_game", 1.0) / 3.0)
        names.append("home_conceded_norm")
        features.append(match_data.get("away_conceded_per_game", 1.2) / 3.0)
        names.append("away_conceded_norm")

        # H2H metrics
        h2h = match_data.get("h2h", {})
        features.append(h2h.get("home_win_rate", 0.45))
        names.append("h2h_home_rate")
        features.append(h2h.get("draw_rate", 0.25))
        names.append("h2h_draw_rate")
        features.append(h2h.get("avg_goals", 2.5) / 5.0)
        names.append("h2h_avg_goals")

        # Venue and context
        features.append(match_data.get("venue_strength", 0.15))
        names.append("venue_strength")
        features.append(match_data.get("weather_impact", 0.0))
        names.append("weather_impact")
        features.append(match_data.get("referee_bias", 0.0))
        names.append("referee_bias")

        # Binary flags
        features.append(1.0 if match_data.get("is_derby", False) else 0.0)
        names.append("is_derby")
        features.append(1.0 if match_data.get("european_week", False) else 0.0)
        names.append("european_week")

        # Rest days (normalized)
        features.append(min(match_data.get("home_rest_days", 7), 14) / 14)
        names.append("home_rest_norm")
        features.append(min(match_data.get("away_rest_days", 7), 14) / 14)
        names.append("away_rest_norm")

        return np.array(features), names

    def _extract_embedding_features(
        self, match_data: Dict[str, Any]
    ) -> Tuple[np.ndarray, List[str]]:
        """Extract team embedding features"""
        home_team = match_data.get("home_team", "Unknown")
        away_team = match_data.get("away_team", "Unknown")

        home_emb = self.team_embeddings.get_embedding(home_team)
        away_emb = self.team_embeddings.get_embedding(away_team)

        # Concatenate and add interaction features
        features = np.concatenate(
            [
                home_emb,
                away_emb,
                home_emb - away_emb,  # Difference
                home_emb * away_emb,  # Element-wise product (interaction)
            ]
        )

        names = []
        for prefix in ["home_emb", "away_emb", "diff_emb", "prod_emb"]:
            for i in range(len(home_emb)):
                names.append(f"{prefix}_{i}")

        # Add similarity score
        similarity = self.team_embeddings.team_similarity(home_team, away_team)
        features = np.append(features, similarity)
        names.append("team_similarity")

        # Add predicted goal difference from embeddings
        pred_gd = self.team_embeddings.predict_goal_diff(home_team, away_team)
        features = np.append(features, np.tanh(pred_gd / 3))  # Normalize to -1 to 1
        names.append("emb_pred_goal_diff")

        return features, names

    def _extract_temporal_features(
        self, match_data: Dict[str, Any], match_datetime: Optional[datetime]
    ) -> Tuple[np.ndarray, List[str]]:
        """Extract temporal features with Fourier encoding"""
        if match_datetime is None:
            match_datetime = datetime.now()

        fourier_encoded = self.fourier.encode_datetime(match_datetime)

        features = []
        names = []

        for key, values in fourier_encoded.items():
            features.extend(values)
            for i in range(len(values) // 2):
                names.append(f"{key}_sin_{i + 1}")
                names.append(f"{key}_cos_{i + 1}")

        # Season progress (0 = start, 1 = end)
        season_start = datetime(
            (
                match_datetime.year
                if match_datetime.month >= 8
                else match_datetime.year - 1
            ),
            8,
            1,
        )
        season_end = datetime(
            (
                match_datetime.year
                if match_datetime.month < 8
                else match_datetime.year + 1
            ),
            5,
            30,
        )

        if match_datetime < season_start:
            progress = 0.0
        elif match_datetime > season_end:
            progress = 1.0
        else:
            total_days = (season_end - season_start).days
            elapsed_days = (match_datetime - season_start).days
            progress = elapsed_days / total_days

        features.append(progress)
        names.append("season_progress")

        # Is weekend
        features.append(1.0 if match_datetime.weekday() >= 5 else 0.0)
        names.append("is_weekend")

        # Is evening match (assuming 18:00+ is evening)
        features.append(1.0 if match_datetime.hour >= 18 else 0.0)
        names.append("is_evening")

        return np.array(features), names

    def _extract_momentum_features(
        self, match_data: Dict[str, Any]
    ) -> Tuple[np.ndarray, List[str]]:
        """Extract momentum indicators from form history"""
        features = []
        names = []

        # Home team momentum
        home_form_seq = match_data.get("home_form_sequence", [0.5] * 10)
        home_goals_seq = match_data.get("home_goals_sequence", [1.0] * 10)

        # RSI
        home_rsi = self.momentum.calculate_rsi(home_form_seq)
        features.append(home_rsi / 100)
        names.append("home_rsi")

        # MACD
        home_macd, home_signal = self.momentum.calculate_macd(home_form_seq)
        features.append(np.tanh(home_macd))
        names.append("home_macd")
        features.append(np.tanh(home_signal))
        names.append("home_macd_signal")

        # Trend
        home_r2, home_trend = self.momentum.calculate_trend_strength(home_form_seq)
        features.append(home_r2)
        names.append("home_trend_strength")
        features.append(
            1.0 if home_trend == "up" else (-1.0 if home_trend == "down" else 0.0)
        )
        names.append("home_trend_direction")

        # Away team momentum
        away_form_seq = match_data.get("away_form_sequence", [0.5] * 10)

        away_rsi = self.momentum.calculate_rsi(away_form_seq)
        features.append(away_rsi / 100)
        names.append("away_rsi")

        away_macd, away_signal = self.momentum.calculate_macd(away_form_seq)
        features.append(np.tanh(away_macd))
        names.append("away_macd")
        features.append(np.tanh(away_signal))
        names.append("away_macd_signal")

        away_r2, away_trend = self.momentum.calculate_trend_strength(away_form_seq)
        features.append(away_r2)
        names.append("away_trend_strength")
        features.append(
            1.0 if away_trend == "up" else (-1.0 if away_trend == "down" else 0.0)
        )
        names.append("away_trend_direction")

        # Momentum differential
        features.append((home_rsi - away_rsi) / 100)
        names.append("rsi_diff")
        features.append(np.tanh(home_macd - away_macd))
        names.append("macd_diff")

        return np.array(features), names

    def update_from_result(
        self, home_team: str, away_team: str, home_goals: int, away_goals: int
    ):
        """Update feature engineering models from match result"""
        # Update team embeddings
        self.team_embeddings.update_from_match(
            home_team, away_team, home_goals, away_goals
        )

        # Save state periodically
        self._save_state()

    def _save_state(self):
        """Save feature engineering state to disk"""
        state = {
            "team_embeddings": {
                team: emb.tolist()
                for team, emb in self.team_embeddings.team_embeddings.items()
            },
            "team_biases": self.team_embeddings.team_biases,
            "global_mean": self.team_embeddings.global_mean,
            "target_encodings": self.target_encoder.encodings,
            "global_means": self.target_encoder.global_means,
        }

        state_path = self.models_dir / "feature_state.json"
        with open(state_path, "w") as f:
            json.dump(state, f, indent=2)

    def _load_state(self):
        """Load feature engineering state from disk"""
        state_path = self.models_dir / "feature_state.json"

        if not state_path.exists():
            return

        try:
            with open(state_path, "r") as f:
                state = json.load(f)

            self.team_embeddings.team_embeddings = {
                team: np.array(emb)
                for team, emb in state.get("team_embeddings", {}).items()
            }
            self.team_embeddings.team_biases = state.get("team_biases", {})
            self.team_embeddings.global_mean = state.get("global_mean", 0.0)

            self.target_encoder.encodings = state.get("target_encodings", {})
            self.target_encoder.global_means = state.get("global_means", {})

            self.logger.info("Loaded feature engineering state")

        except Exception as e:
            self.logger.warning(f"Failed to load state: {e}")


def create_feature_engineer() -> AdvancedFeatureEngineer:
    """Factory function to create feature engineer"""
    return AdvancedFeatureEngineer()


# Test the feature engineer
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    engineer = AdvancedFeatureEngineer()

    # Sample match data
    sample_match = {
        "home_team": "Real Madrid CF",
        "away_team": "FC Barcelona",
        "home_elo": 2050,
        "away_elo": 2020,
        "home_attack": 0.92,
        "home_defense": 0.88,
        "away_attack": 0.90,
        "away_defense": 0.82,
        "home_strength": 0.90,
        "away_strength": 0.86,
        "home_form": {"form_score": 78},
        "away_form": {"form_score": 72},
        "home_xg": 2.1,
        "away_xg": 1.8,
        "home_goals_per_game": 2.3,
        "away_goals_per_game": 2.1,
        "h2h": {"home_win_rate": 0.42, "draw_rate": 0.28, "avg_goals": 3.2},
        "venue_strength": 0.25,
        "is_derby": True,
        "home_form_sequence": [0.8, 0.6, 1.0, 0.7, 0.8, 0.9, 0.7, 0.8, 0.6, 0.9],
        "away_form_sequence": [0.7, 0.8, 0.6, 0.9, 0.7, 0.8, 0.5, 0.7, 0.8, 0.6],
    }

    feature_set = engineer.engineer_features(sample_match, datetime.now())

    print("\n🔧 Advanced Feature Engineering Result:")
    print(f"   Static features: {len(feature_set.static_features)} dims")
    print(f"   Temporal features: {len(feature_set.temporal_features)} dims")
    print(f"   Interaction features: {len(feature_set.interaction_features)} dims")
    print(f"   Embedding features: {len(feature_set.embedding_features)} dims")
    print(f"   Total features: {len(feature_set.to_flat_array())} dims")
    print(f"\n   Sample feature names:")
    for name in feature_set.feature_names[:10]:
        print(f"      - {name}")
    print(f"   ... and {len(feature_set.feature_names) - 10} more")
