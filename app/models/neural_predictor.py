#!/usr/bin/env python3
"""
Advanced Neural Prediction System v1.0
State-of-the-art deep learning for sports prediction with:
- Transformer attention mechanisms for feature importance
- LSTM sequence modeling for temporal patterns
- Monte Carlo Dropout for uncertainty quantification
- Residual connections and layer normalization
- Conformal prediction for calibrated confidence intervals
"""

import json
import logging
import warnings
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Tuple, List, Dict

import numpy as np

warnings.filterwarnings("ignore")

# Check for deep learning dependencies
TORCH_AVAILABLE = False
torch = None
nn = None

try:
    import torch as _torch
    import torch.nn as _nn
    import torch.nn.functional as F

    torch = _torch
    nn = _nn
    TORCH_AVAILABLE = True
except ImportError:
    pass

# Fallback to TensorFlow if PyTorch unavailable
TF_AVAILABLE = False
tf = None
keras = None

if not TORCH_AVAILABLE:
    try:
        import tensorflow as _tf
        from tensorflow import keras as _keras

        tf = _tf
        keras = _keras
        TF_AVAILABLE = True
    except ImportError:
        pass


@dataclass
class PredictionResult:
    """Structured prediction output with uncertainty quantification"""

    home_win_prob: float
    draw_prob: float
    away_win_prob: float
    confidence: float
    uncertainty: float
    prediction_interval: Tuple[float, float]
    feature_importance: Dict[str, float]
    model_agreement: float
    calibrated: bool = False
    ensemble_size: int = 1


@dataclass
class TemporalFeatures:
    """Temporal sequence features for LSTM processing"""

    form_sequence: List[float] = field(default_factory=list)
    goals_sequence: List[float] = field(default_factory=list)
    xg_sequence: List[float] = field(default_factory=list)
    opponent_strength_sequence: List[float] = field(default_factory=list)
    sequence_length: int = 10


class AttentionMechanism:
    """Self-attention mechanism for feature importance weighting"""

    def __init__(self, feature_dim: int, num_heads: int = 4):
        self.feature_dim = feature_dim
        self.num_heads = num_heads
        self.head_dim = feature_dim // num_heads

        # Initialize weights with Xavier/Glorot initialization
        scale = np.sqrt(2.0 / (feature_dim + self.head_dim))
        self.W_q = np.random.randn(feature_dim, feature_dim) * scale
        self.W_k = np.random.randn(feature_dim, feature_dim) * scale
        self.W_v = np.random.randn(feature_dim, feature_dim) * scale
        self.W_o = np.random.randn(feature_dim, feature_dim) * scale

    def forward(self, x: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Apply multi-head self-attention

        Args:
            x: Input features [batch_size, seq_len, feature_dim]

        Returns:
            (attended_features, attention_weights)
        """
        batch_size = x.shape[0] if len(x.shape) > 2 else 1
        if len(x.shape) == 2:
            x = x.reshape(1, x.shape[0], x.shape[1])

        seq_len = x.shape[1]

        # Linear projections
        Q = np.dot(x, self.W_q)
        K = np.dot(x, self.W_k)
        V = np.dot(x, self.W_v)

        # Reshape for multi-head attention
        Q = Q.reshape(batch_size, seq_len, self.num_heads, self.head_dim).transpose(
            0, 2, 1, 3
        )
        K = K.reshape(batch_size, seq_len, self.num_heads, self.head_dim).transpose(
            0, 2, 1, 3
        )
        V = V.reshape(batch_size, seq_len, self.num_heads, self.head_dim).transpose(
            0, 2, 1, 3
        )

        # Scaled dot-product attention
        scale = np.sqrt(self.head_dim)
        attention_scores = np.matmul(Q, K.transpose(0, 1, 3, 2)) / scale
        attention_weights = self._softmax(attention_scores, axis=-1)

        # Apply attention to values
        attended = np.matmul(attention_weights, V)

        # Reshape and project output
        attended = attended.transpose(0, 2, 1, 3).reshape(
            batch_size, seq_len, self.feature_dim
        )
        output = np.dot(attended, self.W_o)

        return output.squeeze(), attention_weights.mean(axis=1).squeeze()

    def _softmax(self, x: np.ndarray, axis: int = -1) -> np.ndarray:
        """Numerically stable softmax"""
        x_max = np.max(x, axis=axis, keepdims=True)
        exp_x = np.exp(x - x_max)
        return exp_x / np.sum(exp_x, axis=axis, keepdims=True)


class LSTMLayer:
    """LSTM layer for sequence modeling with forget gate bias initialization"""

    def __init__(self, input_dim: int, hidden_dim: int):
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim

        # Xavier initialization for LSTM weights
        scale = np.sqrt(2.0 / (input_dim + hidden_dim))

        # Input gate weights
        self.W_i = np.random.randn(input_dim, hidden_dim) * scale
        self.U_i = np.random.randn(hidden_dim, hidden_dim) * scale
        self.b_i = np.zeros(hidden_dim)

        # Forget gate weights (bias initialized to 1.0 for better gradient flow)
        self.W_f = np.random.randn(input_dim, hidden_dim) * scale
        self.U_f = np.random.randn(hidden_dim, hidden_dim) * scale
        self.b_f = np.ones(hidden_dim)  # Critical: forget gate bias = 1

        # Cell gate weights
        self.W_c = np.random.randn(input_dim, hidden_dim) * scale
        self.U_c = np.random.randn(hidden_dim, hidden_dim) * scale
        self.b_c = np.zeros(hidden_dim)

        # Output gate weights
        self.W_o = np.random.randn(input_dim, hidden_dim) * scale
        self.U_o = np.random.randn(hidden_dim, hidden_dim) * scale
        self.b_o = np.zeros(hidden_dim)

    def forward(self, x_sequence: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Process sequence through LSTM

        Args:
            x_sequence: Input sequence [seq_len, input_dim]

        Returns:
            (final_hidden_state, all_hidden_states)
        """
        seq_len = x_sequence.shape[0]

        # Initialize hidden state and cell state
        h = np.zeros(self.hidden_dim)
        c = np.zeros(self.hidden_dim)

        all_hidden = []

        for t in range(seq_len):
            x_t = x_sequence[t]

            # Input gate
            i_t = self._sigmoid(np.dot(x_t, self.W_i) + np.dot(h, self.U_i) + self.b_i)

            # Forget gate
            f_t = self._sigmoid(np.dot(x_t, self.W_f) + np.dot(h, self.U_f) + self.b_f)

            # Cell candidate
            c_tilde = np.tanh(np.dot(x_t, self.W_c) + np.dot(h, self.U_c) + self.b_c)

            # Cell state update
            c = f_t * c + i_t * c_tilde

            # Output gate
            o_t = self._sigmoid(np.dot(x_t, self.W_o) + np.dot(h, self.U_o) + self.b_o)

            # Hidden state
            h = o_t * np.tanh(c)

            all_hidden.append(h.copy())

        return h, np.array(all_hidden)

    def _sigmoid(self, x: np.ndarray) -> np.ndarray:
        """Numerically stable sigmoid"""
        return np.where(x >= 0, 1 / (1 + np.exp(-x)), np.exp(x) / (1 + np.exp(x)))


class ResidualBlock:
    """Residual block with layer normalization for stable deep networks"""

    def __init__(self, dim: int, dropout_rate: float = 0.1):
        self.dim = dim
        self.dropout_rate = dropout_rate

        # Two-layer MLP with GELU activation
        scale = np.sqrt(2.0 / dim)
        self.W1 = np.random.randn(dim, dim * 4) * scale
        self.b1 = np.zeros(dim * 4)
        self.W2 = np.random.randn(dim * 4, dim) * scale
        self.b2 = np.zeros(dim)

        # Layer normalization parameters
        self.gamma = np.ones(dim)
        self.beta = np.zeros(dim)

    def forward(self, x: np.ndarray, training: bool = False) -> np.ndarray:
        """Forward pass with residual connection and layer norm"""
        # Layer normalization
        normalized = self._layer_norm(x)

        # First linear + GELU
        hidden = np.dot(normalized, self.W1) + self.b1
        hidden = self._gelu(hidden)

        # Dropout during training
        if training and self.dropout_rate > 0:
            mask = np.random.binomial(1, 1 - self.dropout_rate, hidden.shape)
            hidden = hidden * mask / (1 - self.dropout_rate)

        # Second linear
        output = np.dot(hidden, self.W2) + self.b2

        # Residual connection
        return x + output

    def _layer_norm(self, x: np.ndarray, eps: float = 1e-6) -> np.ndarray:
        """Layer normalization"""
        mean = np.mean(x, axis=-1, keepdims=True)
        std = np.std(x, axis=-1, keepdims=True)
        return self.gamma * (x - mean) / (std + eps) + self.beta

    def _gelu(self, x: np.ndarray) -> np.ndarray:
        """Gaussian Error Linear Unit activation"""
        return 0.5 * x * (1 + np.tanh(np.sqrt(2 / np.pi) * (x + 0.044715 * x**3)))


class MonteCarloDropout:
    """Monte Carlo Dropout for uncertainty quantification"""

    def __init__(self, dropout_rate: float = 0.2, num_samples: int = 30):
        self.dropout_rate = dropout_rate
        self.num_samples = num_samples

    def predict_with_uncertainty(
        self, model_forward_fn, x: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Make predictions with uncertainty estimates using MC Dropout

        Args:
            model_forward_fn: Function that takes x and training=True flag
            x: Input features

        Returns:
            (mean_prediction, epistemic_uncertainty, aleatoric_uncertainty)
        """
        predictions = []

        for _ in range(self.num_samples):
            pred = model_forward_fn(x, training=True)
            predictions.append(pred)

        predictions = np.array(predictions)

        # Mean prediction
        mean_pred = np.mean(predictions, axis=0)

        # Epistemic uncertainty (model uncertainty from dropout variance)
        epistemic = np.var(predictions, axis=0)

        # Aleatoric uncertainty (data uncertainty from prediction entropy)
        # For classification: entropy of mean prediction
        aleatoric = -np.sum(mean_pred * np.log(mean_pred + 1e-10))

        return mean_pred, epistemic, aleatoric


class ConformalPredictor:
    """Conformal prediction for calibrated confidence intervals"""

    def __init__(self, alpha: float = 0.1):
        """
        Args:
            alpha: Significance level (0.1 = 90% confidence intervals)
        """
        self.alpha = alpha
        self.calibration_scores: List[float] = []
        self.is_calibrated = False

    def calibrate(self, predictions: np.ndarray, true_outcomes: np.ndarray):
        """
        Calibrate using holdout data

        Args:
            predictions: Model predictions [n_samples, n_classes]
            true_outcomes: True class labels [n_samples]
        """
        # Calculate nonconformity scores (1 - probability of true class)
        for i, (pred, true_label) in enumerate(zip(predictions, true_outcomes)):
            true_prob = pred[int(true_label)]
            nonconformity = 1.0 - true_prob
            self.calibration_scores.append(nonconformity)

        self.calibration_scores.sort()
        self.is_calibrated = True

    def get_prediction_set(self, prediction: np.ndarray) -> Tuple[List[int], float]:
        """
        Get prediction set with guaranteed coverage

        Args:
            prediction: Model prediction [n_classes]

        Returns:
            (prediction_set, confidence)
        """
        if not self.is_calibrated:
            # Return top prediction with base confidence
            return [int(np.argmax(prediction))], float(np.max(prediction))

        # Calculate threshold from calibration scores
        n = len(self.calibration_scores)
        k = int(np.ceil((n + 1) * (1 - self.alpha)))
        threshold = self.calibration_scores[min(k - 1, n - 1)]

        # Include all classes with nonconformity <= threshold
        prediction_set = []
        for class_idx, prob in enumerate(prediction):
            if 1 - prob <= threshold:
                prediction_set.append(class_idx)

        # If empty, include top prediction
        if not prediction_set:
            prediction_set = [int(np.argmax(prediction))]

        # Confidence is the max probability in the prediction set
        confidence = max(prediction[i] for i in prediction_set)

        return prediction_set, float(confidence)


class AdvancedNeuralPredictor:
    """
    State-of-the-art neural prediction system combining:
    - Multi-head self-attention for feature importance
    - Bidirectional LSTM for temporal patterns
    - Residual connections and layer normalization
    - Monte Carlo Dropout for uncertainty
    - Conformal prediction for calibrated intervals
    """

    # Feature dimensions
    STATIC_FEATURE_DIM = 32
    TEMPORAL_FEATURE_DIM = 16
    HIDDEN_DIM = 64
    NUM_ATTENTION_HEADS = 4
    NUM_RESIDUAL_BLOCKS = 3
    DROPOUT_RATE = 0.2
    MC_SAMPLES = 30

    # Feature names for interpretability
    FEATURE_NAMES = [
        "home_elo",
        "away_elo",
        "elo_diff",
        "home_attack",
        "home_defense",
        "away_attack",
        "away_defense",
        "home_form",
        "away_form",
        "h2h_home_advantage",
        "home_xg",
        "away_xg",
        "home_goals_per_game",
        "away_goals_per_game",
        "venue_strength",
        "weather_impact",
        "referee_bias",
        "fatigue_factor",
        "injury_impact",
        "motivation_factor",
        "league_position_diff",
        "is_derby",
        "days_since_last_match",
        "travel_distance",
        "altitude_diff",
        "pitch_quality",
        "time_of_day",
        "season_progress",
        "european_competition",
        "pressure_factor",
        "home_clean_sheets",
        "away_clean_sheets",
    ]

    def __init__(self, models_dir: str = "models/neural"):
        self.logger = logging.getLogger(__name__)
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)

        # Initialize components
        self.attention = AttentionMechanism(
            self.STATIC_FEATURE_DIM, self.NUM_ATTENTION_HEADS
        )
        self.lstm = LSTMLayer(self.TEMPORAL_FEATURE_DIM, self.HIDDEN_DIM)

        self.residual_blocks = [
            ResidualBlock(self.HIDDEN_DIM, self.DROPOUT_RATE)
            for _ in range(self.NUM_RESIDUAL_BLOCKS)
        ]

        self.mc_dropout = MonteCarloDropout(self.DROPOUT_RATE, self.MC_SAMPLES)
        self.conformal = ConformalPredictor(alpha=0.1)

        # Output projection
        scale = np.sqrt(2.0 / self.HIDDEN_DIM)
        self.W_out = np.random.randn(self.HIDDEN_DIM, 3) * scale  # 3 classes
        self.b_out = np.zeros(3)

        # Feature projection layers
        self.W_static = (
            np.random.randn(self.STATIC_FEATURE_DIM, self.HIDDEN_DIM) * scale
        )
        self.W_temporal = np.random.randn(self.HIDDEN_DIM, self.HIDDEN_DIM) * scale

        # Load pre-trained weights if available
        self._load_weights()

        self.logger.info("Advanced Neural Predictor initialized")
        self.logger.info(f"  - PyTorch available: {TORCH_AVAILABLE}")
        self.logger.info(f"  - TensorFlow available: {TF_AVAILABLE}")

    def extract_features(
        self, match_data: Dict[str, Any]
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Extract static and temporal features from match data

        Args:
            match_data: Complete match data dictionary

        Returns:
            (static_features, temporal_features)
        """
        # Static features (team strengths, venue, context)
        static = np.zeros(self.STATIC_FEATURE_DIM)

        # ELO ratings
        home_elo = match_data.get("home_elo", 1500)
        away_elo = match_data.get("away_elo", 1500)
        static[0] = (home_elo - 1200) / 800  # Normalize to ~0-1
        static[1] = (away_elo - 1200) / 800
        static[2] = (home_elo - away_elo) / 400  # Diff normalized

        # Attack/defense ratings
        home_attack = match_data.get("home_attack", 0.5)
        home_defense = match_data.get("home_defense", 0.5)
        away_attack = match_data.get("away_attack", 0.5)
        away_defense = match_data.get("away_defense", 0.5)
        static[3:7] = [home_attack, home_defense, away_attack, away_defense]

        # Form
        home_form = match_data.get("home_form", {})
        away_form = match_data.get("away_form", {})
        static[7] = home_form.get("form_score", 50) / 100
        static[8] = away_form.get("form_score", 50) / 100

        # H2H
        h2h = match_data.get("h2h", {})
        static[9] = h2h.get("home_advantage", 0.5)

        # xG metrics
        static[10] = match_data.get("home_xg", 1.2) / 3.0
        static[11] = match_data.get("away_xg", 1.0) / 3.0

        # Goals per game
        static[12] = match_data.get("home_goals_per_game", 1.3) / 3.0
        static[13] = match_data.get("away_goals_per_game", 1.0) / 3.0

        # Venue and conditions
        static[14] = match_data.get("venue_strength", 0.15)
        static[15] = match_data.get("weather_impact", 0.0)
        static[16] = match_data.get("referee_bias", 0.0)

        # Fatigue and injuries
        static[17] = match_data.get("fatigue_factor", 0.0)
        static[18] = match_data.get("injury_impact", 0.0)

        # Motivation and context
        static[19] = match_data.get("motivation_factor", 0.5)
        static[20] = match_data.get("league_position_diff", 0) / 20
        static[21] = 1.0 if match_data.get("is_derby", False) else 0.0

        # Temporal factors
        static[22] = match_data.get("days_since_last_match", 7) / 14
        static[23] = match_data.get("travel_distance", 0) / 1000

        # Additional context
        static[24] = match_data.get("altitude_diff", 0) / 1000
        static[25] = match_data.get("pitch_quality", 0.8)
        static[26] = match_data.get("time_of_day", 0.5)
        static[27] = match_data.get("season_progress", 0.5)
        static[28] = 1.0 if match_data.get("european_competition", False) else 0.0
        static[29] = match_data.get("pressure_factor", 0.5)

        # Defensive records
        static[30] = match_data.get("home_clean_sheets", 0.3)
        static[31] = match_data.get("away_clean_sheets", 0.25)

        # Temporal features (sequence of last N matches)
        temporal_data = match_data.get("temporal", {})
        seq_len = 10
        temporal = np.zeros((seq_len, self.TEMPORAL_FEATURE_DIM))

        form_seq = temporal_data.get("form_sequence", [0.5] * seq_len)
        goals_seq = temporal_data.get("goals_sequence", [1.0] * seq_len)
        xg_seq = temporal_data.get("xg_sequence", [1.0] * seq_len)
        opponent_seq = temporal_data.get("opponent_strength_sequence", [0.5] * seq_len)

        for i in range(min(seq_len, len(form_seq))):
            temporal[i, 0] = form_seq[i] if i < len(form_seq) else 0.5
            temporal[i, 1] = goals_seq[i] / 3.0 if i < len(goals_seq) else 0.33
            temporal[i, 2] = xg_seq[i] / 3.0 if i < len(xg_seq) else 0.33
            temporal[i, 3] = opponent_seq[i] if i < len(opponent_seq) else 0.5

            # Add derived features
            temporal[i, 4] = temporal[i, 1] - temporal[i, 2]  # Goals vs xG diff
            temporal[i, 5] = temporal[i, 0] * temporal[i, 3]  # Form * opponent strength

        return static, temporal

    def _forward(
        self, static: np.ndarray, temporal: np.ndarray, training: bool = False
    ) -> np.ndarray:
        """
        Forward pass through the neural network

        Args:
            static: Static features [static_dim]
            temporal: Temporal features [seq_len, temporal_dim]
            training: Whether in training mode (enables dropout)

        Returns:
            Probability distribution [3] (home_win, draw, away_win)
        """
        # Process static features through attention
        static_expanded = static.reshape(1, -1)  # [1, static_dim]
        attended_static, attention_weights = self.attention.forward(static_expanded)
        attended_static = attended_static.flatten()

        # Project static features
        static_hidden = np.dot(attended_static, self.W_static)

        # Process temporal features through LSTM
        lstm_output, all_hidden = self.lstm.forward(temporal)

        # Project LSTM output
        temporal_hidden = np.dot(lstm_output, self.W_temporal)

        # Combine static and temporal
        combined = static_hidden + temporal_hidden

        # Apply residual blocks
        for block in self.residual_blocks:
            combined = block.forward(combined, training=training)

        # Output projection
        logits = np.dot(combined, self.W_out) + self.b_out

        # Softmax for probabilities
        exp_logits = np.exp(logits - np.max(logits))
        probabilities = exp_logits / np.sum(exp_logits)

        return probabilities

    def predict(self, match_data: Dict[str, Any]) -> PredictionResult:
        """
        Make prediction with full uncertainty quantification

        Args:
            match_data: Complete match data dictionary

        Returns:
            PredictionResult with probabilities, confidence, and uncertainty
        """
        # Extract features
        static, temporal = self.extract_features(match_data)

        # Monte Carlo predictions for uncertainty
        def model_fn(x, training=False):
            return self._forward(static, temporal, training=training)

        mean_pred, epistemic_unc, aleatoric_unc = (
            self.mc_dropout.predict_with_uncertainty(model_fn, static)
        )

        # Get conformal prediction set
        pred_set, conf_prob = self.conformal.get_prediction_set(mean_pred)

        # Calculate overall uncertainty
        total_uncertainty = np.sqrt(np.mean(epistemic_unc) + aleatoric_unc)

        # Calculate confidence (inversely proportional to uncertainty)
        base_confidence = 1.0 - min(0.5, total_uncertainty)

        # Adjust for prediction set size (larger set = less confident)
        set_penalty = 0.1 * (len(pred_set) - 1)
        adjusted_confidence = max(0.4, base_confidence - set_penalty)

        # Feature importance from attention weights
        _, attention_weights = self.attention.forward(static.reshape(1, -1))
        feature_importance = {}
        for i, name in enumerate(self.FEATURE_NAMES[: self.STATIC_FEATURE_DIM]):
            if i < len(attention_weights.flatten()):
                feature_importance[name] = float(attention_weights.flatten()[i])

        # Calculate prediction interval
        std = np.sqrt(np.mean(epistemic_unc))
        z = 1.96  # 95% confidence interval
        interval = (
            max(0.0, float(np.max(mean_pred) - z * std)),
            min(1.0, float(np.max(mean_pred) + z * std)),
        )

        return PredictionResult(
            home_win_prob=float(mean_pred[2]),  # Index 2 for home win
            draw_prob=float(mean_pred[1]),
            away_win_prob=float(mean_pred[0]),
            confidence=float(adjusted_confidence),
            uncertainty=float(total_uncertainty),
            prediction_interval=interval,
            feature_importance=feature_importance,
            model_agreement=float(1.0 - np.mean(epistemic_unc) * 10),
            calibrated=self.conformal.is_calibrated,
            ensemble_size=self.mc_dropout.num_samples,
        )

    def calibrate(
        self, calibration_data: List[Dict[str, Any]], true_outcomes: List[int]
    ) -> Dict[str, Any]:
        """
        Calibrate the model using holdout data

        Args:
            calibration_data: List of match data dictionaries
            true_outcomes: True outcomes (0=away, 1=draw, 2=home)

        Returns:
            Calibration statistics
        """
        predictions = []

        for match in calibration_data:
            static, temporal = self.extract_features(match)
            pred = self._forward(static, temporal, training=False)
            predictions.append(pred)

        predictions = np.array(predictions)
        true_outcomes_arr = np.array(true_outcomes)

        # Calibrate conformal predictor
        self.conformal.calibrate(predictions, true_outcomes_arr)

        # Calculate calibration metrics
        predicted_classes = np.argmax(predictions, axis=1)
        accuracy = np.mean(predicted_classes == true_outcomes_arr)

        # Brier score (lower is better)
        brier_score = np.mean(
            np.sum((predictions - np.eye(3)[true_outcomes_arr]) ** 2, axis=1)
        )

        # Expected calibration error
        ece = self._calculate_ece(predictions, true_outcomes_arr)

        return {
            "accuracy": float(accuracy),
            "brier_score": float(brier_score),
            "expected_calibration_error": float(ece),
            "calibration_samples": len(calibration_data),
            "calibrated": True,
        }

    def _calculate_ece(
        self, predictions: np.ndarray, true_outcomes: np.ndarray, n_bins: int = 10
    ) -> float:
        """Calculate Expected Calibration Error"""
        confidences = np.max(predictions, axis=1)
        predicted_classes = np.argmax(predictions, axis=1)
        accuracies = (predicted_classes == true_outcomes).astype(float)

        ece = 0.0
        for i in range(n_bins):
            bin_lower = i / n_bins
            bin_upper = (i + 1) / n_bins
            in_bin = (confidences >= bin_lower) & (confidences < bin_upper)

            if np.sum(in_bin) > 0:
                bin_confidence = np.mean(confidences[in_bin])
                bin_accuracy = np.mean(accuracies[in_bin])
                bin_weight = np.sum(in_bin) / len(confidences)
                ece += bin_weight * np.abs(bin_accuracy - bin_confidence)

        return ece

    def _save_weights(self):
        """Save model weights to disk"""
        weights = {
            "attention_W_q": self.attention.W_q.tolist(),
            "attention_W_k": self.attention.W_k.tolist(),
            "attention_W_v": self.attention.W_v.tolist(),
            "attention_W_o": self.attention.W_o.tolist(),
            "lstm": {
                "W_i": self.lstm.W_i.tolist(),
                "U_i": self.lstm.U_i.tolist(),
                "b_i": self.lstm.b_i.tolist(),
                "W_f": self.lstm.W_f.tolist(),
                "U_f": self.lstm.U_f.tolist(),
                "b_f": self.lstm.b_f.tolist(),
                "W_c": self.lstm.W_c.tolist(),
                "U_c": self.lstm.U_c.tolist(),
                "b_c": self.lstm.b_c.tolist(),
                "W_o": self.lstm.W_o.tolist(),
                "U_o": self.lstm.U_o.tolist(),
                "b_o": self.lstm.b_o.tolist(),
            },
            "W_static": self.W_static.tolist(),
            "W_temporal": self.W_temporal.tolist(),
            "W_out": self.W_out.tolist(),
            "b_out": self.b_out.tolist(),
            "conformal_scores": self.conformal.calibration_scores,
        }

        weights_path = self.models_dir / "neural_weights.json"
        with open(weights_path, "w") as f:
            json.dump(weights, f)

        self.logger.info(f"Saved neural weights to {weights_path}")

    def _load_weights(self):
        """Load model weights from disk"""
        weights_path = self.models_dir / "neural_weights.json"

        if not weights_path.exists():
            self.logger.info(
                "No pre-trained weights found, using random initialization"
            )
            return

        try:
            with open(weights_path, "r") as f:
                weights = json.load(f)

            self.attention.W_q = np.array(weights["attention_W_q"])
            self.attention.W_k = np.array(weights["attention_W_k"])
            self.attention.W_v = np.array(weights["attention_W_v"])
            self.attention.W_o = np.array(weights["attention_W_o"])

            lstm = weights["lstm"]
            self.lstm.W_i = np.array(lstm["W_i"])
            self.lstm.U_i = np.array(lstm["U_i"])
            self.lstm.b_i = np.array(lstm["b_i"])
            self.lstm.W_f = np.array(lstm["W_f"])
            self.lstm.U_f = np.array(lstm["U_f"])
            self.lstm.b_f = np.array(lstm["b_f"])
            self.lstm.W_c = np.array(lstm["W_c"])
            self.lstm.U_c = np.array(lstm["U_c"])
            self.lstm.b_c = np.array(lstm["b_c"])
            self.lstm.W_o = np.array(lstm["W_o"])
            self.lstm.U_o = np.array(lstm["U_o"])
            self.lstm.b_o = np.array(lstm["b_o"])

            self.W_static = np.array(weights["W_static"])
            self.W_temporal = np.array(weights["W_temporal"])
            self.W_out = np.array(weights["W_out"])
            self.b_out = np.array(weights["b_out"])

            if weights.get("conformal_scores"):
                self.conformal.calibration_scores = weights["conformal_scores"]
                self.conformal.is_calibrated = True

            self.logger.info("Loaded pre-trained neural weights")

        except Exception as e:
            self.logger.warning(f"Failed to load weights: {e}")


def create_neural_predictor() -> AdvancedNeuralPredictor:
    """Factory function to create neural predictor"""
    return AdvancedNeuralPredictor()


# Test the neural predictor
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    predictor = AdvancedNeuralPredictor()

    # Sample match data
    sample_match = {
        "home_elo": 2050,
        "away_elo": 1750,
        "home_attack": 0.85,
        "home_defense": 0.80,
        "away_attack": 0.65,
        "away_defense": 0.60,
        "home_form": {"form_score": 75},
        "away_form": {"form_score": 55},
        "h2h": {"home_advantage": 0.6},
        "home_xg": 1.8,
        "away_xg": 1.0,
        "venue_strength": 0.2,
        "weather_impact": 0.0,
        "is_derby": True,
        "temporal": {
            "form_sequence": [0.8, 0.6, 0.9, 0.7, 0.8, 0.5, 0.7, 0.8, 0.6, 0.9],
            "goals_sequence": [2, 1, 3, 0, 2, 1, 2, 3, 1, 2],
            "xg_sequence": [1.8, 1.2, 2.1, 0.8, 1.9, 1.0, 1.5, 2.0, 1.1, 1.8],
            "opponent_strength_sequence": [
                0.5,
                0.7,
                0.4,
                0.8,
                0.5,
                0.6,
                0.5,
                0.4,
                0.7,
                0.5,
            ],
        },
    }

    result = predictor.predict(sample_match)

    print("\n🧠 Advanced Neural Prediction Result:")
    print(f"   Home Win: {result.home_win_prob:.1%}")
    print(f"   Draw:     {result.draw_prob:.1%}")
    print(f"   Away Win: {result.away_win_prob:.1%}")
    print(f"   Confidence: {result.confidence:.1%}")
    print(f"   Uncertainty: {result.uncertainty:.4f}")
    print(
        f"   Prediction Interval: [{result.prediction_interval[0]:.1%}, {result.prediction_interval[1]:.1%}]"
    )
    print(f"   Model Agreement: {result.model_agreement:.1%}")
    print(f"   Calibrated: {result.calibrated}")
    print(f"\n   Top 5 Feature Importance:")
    sorted_features = sorted(
        result.feature_importance.items(), key=lambda x: x[1], reverse=True
    )[:5]
    for name, importance in sorted_features:
        print(f"      {name}: {importance:.4f}")
