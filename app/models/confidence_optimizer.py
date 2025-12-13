#!/usr/bin/env python3
"""
Confidence Optimization System v2.0
Advanced confidence calibration for 80%+ prediction accuracy
"""

import logging
import os
import pickle
import warnings
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import numpy as np

warnings.filterwarnings('ignore')

@dataclass
class ConfidenceMetrics:
    """Confidence calibration metrics"""
    calibrated_confidence: float
    uncertainty_bounds: tuple[float, float]
    prediction_stability: float
    data_sufficiency: float
    ensemble_agreement: float
    final_confidence: float

class ConfidenceOptimizer:
    """
    Advanced confidence optimization system for achieving 80%+ accuracy

    Optimization Strategies:
    1. Bayesian Confidence Calibration - Probabilistic uncertainty quantification
    2. Ensemble Agreement Analysis - Multi-model consensus scoring
    3. Data Sufficiency Assessment - Quality vs quantity trade-offs
    4. Historical Performance Calibration - Learning from past predictions
    5. Uncertainty Bounds Calculation - Confidence intervals for predictions
    6. Adaptive Confidence Scaling - Dynamic adjustments based on context
    """

    def __init__(self, calibration_data_path: str = "models/calibration"):
        self.logger = logging.getLogger(__name__)
        self.calibration_path = calibration_data_path
        self.calibration_models: dict[str, Any] = {}
        self.historical_performance: dict[str, dict[str, Any]] = {}
        self.confidence_thresholds = self._initialize_thresholds()

        # Ensure calibration directory exists
        os.makedirs(calibration_data_path, exist_ok=True)

        # Load existing calibration data
        self.load_calibration_models()

    def _initialize_thresholds(self) -> dict[str, float]:
        """Initialize confidence thresholds for different quality levels"""
        return {
            'minimum_viable': 0.4,   # Minimum for any prediction
            'standard_quality': 0.6,  # Standard prediction quality
            'high_quality': 0.75,     # High-confidence predictions
            'excellent_quality': 0.85, # Excellent predictions
            'maximum_achievable': 0.95  # Theoretical maximum
        }

    def optimize_confidence(self, base_confidence: float,
                           prediction_data: dict[str, Any],
                           ensemble_predictions: dict[str, Any] | None = None,
                           validation_result: Any | None = None) -> ConfidenceMetrics:
        """
        Optimize confidence score using multiple advanced techniques

        Args:
            base_confidence: Initial confidence from prediction model
            prediction_data: Complete prediction data and metadata
            ensemble_predictions: Results from ensemble models
            validation_result: Data validation results

        Returns:
            Optimized confidence metrics with uncertainty quantification
        """

        # 1. Bayesian Confidence Calibration
        bayesian_confidence = self._bayesian_calibration(
            base_confidence, prediction_data
        )

        # 2. Ensemble Agreement Analysis
        ensemble_agreement, ensemble_confidence = self._analyze_ensemble_agreement(
            ensemble_predictions, base_confidence
        )

        # 3. Data Sufficiency Assessment
        data_sufficiency = self._assess_data_sufficiency(
            prediction_data, validation_result
        )

        # 4. Historical Performance Calibration
        calibrated_confidence = self._apply_historical_calibration(
            bayesian_confidence, prediction_data
        )

        # 5. Uncertainty Bounds Calculation
        uncertainty_bounds = self._calculate_uncertainty_bounds(
            calibrated_confidence, ensemble_agreement, data_sufficiency
        )

        # 6. Prediction Stability Analysis
        stability_score = self._analyze_prediction_stability(
            prediction_data, ensemble_predictions
        )

        # 7. Final Confidence Integration
        final_confidence = self._integrate_confidence_factors(
            calibrated_confidence,
            ensemble_confidence,
            data_sufficiency,
            stability_score,
            validation_result
        )

        return ConfidenceMetrics(
            calibrated_confidence=calibrated_confidence,
            uncertainty_bounds=uncertainty_bounds,
            prediction_stability=stability_score,
            data_sufficiency=data_sufficiency,
            ensemble_agreement=ensemble_agreement,
            final_confidence=final_confidence
        )

    def _bayesian_calibration(self, base_confidence: float,
                             prediction_data: dict[str, Any]) -> float:
        """
        Apply Bayesian calibration to adjust confidence based on evidence strength

        Uses prior knowledge and data evidence to calibrate confidence
        """

        # Prior confidence (league-specific baseline)
        league = prediction_data.get('league', '').lower()
        prior_confidence = self._get_league_prior_confidence(league)

        # Evidence strength from data quality
        data_quality = float(prediction_data.get('data_quality_score', 75)) / 100.0
        evidence_strength = data_quality ** 2  # Square for stronger effect

        # Bayesian update: P(confident|evidence) ∝ P(evidence|confident) * P(confident)
        # Simplified Bayesian adjustment
        likelihood = float(base_confidence) * evidence_strength
        posterior = float((likelihood * prior_confidence) / (
            likelihood * prior_confidence + (1 - likelihood) * (1 - prior_confidence)
        ))

        # Blend with base confidence (avoid over-adjustment)
        bayesian_confidence = float(0.7 * posterior + 0.3 * base_confidence)

        return min(bayesian_confidence, 0.95)

    def _analyze_ensemble_agreement(self, ensemble_predictions: dict[str, Any] | None,
                                   base_confidence: float) -> tuple[float, float]:
        """
        Analyze agreement between ensemble models for confidence adjustment

        High agreement = higher confidence, low agreement = lower confidence
        """

        if not ensemble_predictions or 'model_predictions' not in ensemble_predictions:
            return 0.5, base_confidence  # Default values when no ensemble available

        model_predictions = ensemble_predictions['model_predictions']

        if len(model_predictions) < 2:
            return 0.5, base_confidence

        # Calculate agreement between models
        agreements = []
        predictions_list = list(model_predictions.values())

        for i in range(len(predictions_list)):
            for j in range(i + 1, len(predictions_list)):
                pred_i = predictions_list[i]
                pred_j = predictions_list[j]

                # Calculate similarity (1 - total variation distance)
                similarity = 1.0 - 0.5 * np.sum(np.abs(pred_i - pred_j))
                agreements.append(similarity)

        # Average agreement
        ensemble_agreement = np.mean(agreements)

        # Confidence boost based on agreement
        agreement_boost = (ensemble_agreement - 0.5) * 0.2  # Up to 10% boost
        ensemble_confidence = min(base_confidence + agreement_boost, 0.95)

        return float(ensemble_agreement), float(ensemble_confidence)

    def _assess_data_sufficiency(self, prediction_data: dict[str, Any],
                                validation_result: Any | None) -> float:
        """
        Assess data sufficiency for confident predictions

        More data = higher confidence potential
        """

        sufficiency_factors = []

        # Match history sufficiency
        home_matches = prediction_data.get('home_performance_analysis', {}).get('home', {}).get('matches', 0)
        away_matches = prediction_data.get('away_performance_analysis', {}).get('away', {}).get('matches', 0)

        # Score based on match count (diminishing returns)
        home_score = min(home_matches / 15.0, 1.0)  # 15+ matches = full score
        away_score = min(away_matches / 15.0, 1.0)
        match_sufficiency = (home_score + away_score) / 2
        sufficiency_factors.append(match_sufficiency)

        # Head-to-head data sufficiency
        h2h_meetings = prediction_data.get('head_to_head_analysis', {}).get('total_meetings', 0)
        h2h_sufficiency = min(h2h_meetings / 8.0, 1.0)  # 8+ meetings = full score
        sufficiency_factors.append(h2h_sufficiency)

        # Data quality sufficiency
        if validation_result and hasattr(validation_result, 'quality_score'):
            quality_sufficiency = validation_result.quality_score / 100.0
            sufficiency_factors.append(quality_sufficiency)

        # Data source diversity
        data_sources_used = prediction_data.get('data_sources_used', 1)
        source_sufficiency = min(data_sources_used / 3.0, 1.0)  # 3+ sources = full score
        sufficiency_factors.append(source_sufficiency)

        return float(np.mean(sufficiency_factors))

    def _apply_historical_calibration(self, base_confidence: float,
                                     prediction_data: dict[str, Any]) -> float:
        """
        Apply calibration based on historical prediction performance

        Learn from past prediction accuracy to adjust current confidence
        """

        # Load historical performance for this prediction type
        prediction_type = self._classify_prediction_type(prediction_data)
        historical_perf = self.historical_performance.get(prediction_type, {})

        if not historical_perf:
            return base_confidence  # No historical data available

        # Get historical accuracy for this confidence range
        confidence_bucket = self._get_confidence_bucket(base_confidence)
        historical_accuracy = historical_perf.get(confidence_bucket, base_confidence)

        # Calibrate: if we historically perform better/worse at this confidence level
        calibration_factor = historical_accuracy / base_confidence if base_confidence > 0 else 1.0

        # Apply calibration with dampening to avoid over-correction
        calibrated = base_confidence * (0.7 + 0.3 * calibration_factor)

        return min(calibrated, 0.95)

    def _calculate_uncertainty_bounds(self, confidence: float,
                                     ensemble_agreement: float,
                                     data_sufficiency: float) -> tuple[float, float]:
        """
        Calculate uncertainty bounds around the confidence estimate

        Returns (lower_bound, upper_bound) for confidence interval
        """

        # Base uncertainty from confidence level (higher confidence = lower uncertainty)
        base_uncertainty = (1 - confidence) * 0.3

        # Increase uncertainty if ensemble disagrees
        agreement_uncertainty = (1 - ensemble_agreement) * 0.2

        # Increase uncertainty if data is insufficient
        sufficiency_uncertainty = (1 - data_sufficiency) * 0.25

        # Total uncertainty
        total_uncertainty = base_uncertainty + agreement_uncertainty + sufficiency_uncertainty

        # Calculate bounds
        lower_bound = max(0.3, confidence - total_uncertainty)
        upper_bound = min(0.95, confidence + total_uncertainty * 0.5)  # Asymmetric bounds

        return (lower_bound, upper_bound)

    def _analyze_prediction_stability(self, prediction_data: dict[str, Any],
                                     ensemble_predictions: dict[str, Any] | None) -> float:
        """
        Analyze prediction stability across different models and inputs

        Stable predictions = higher confidence
        """

        stability_factors = []

        # Check if win probabilities are reasonably separated
        home_prob = prediction_data.get('home_win_probability', 33)
        draw_prob = prediction_data.get('draw_probability', 33)
        away_prob = prediction_data.get('away_win_probability', 33)

        probs = [home_prob, draw_prob, away_prob]
        max_prob = max(probs)

        # Higher separation = more stable prediction
        if max_prob > 50:
            separation_stability = min((max_prob - 33) / 33, 1.0)
        else:
            separation_stability = 0.3  # Low separation = low stability

        stability_factors.append(separation_stability)

        # Check ensemble model agreement (if available)
        if ensemble_predictions and 'model_predictions' in ensemble_predictions:
            model_count = len(ensemble_predictions['model_predictions'])
            if model_count >= 2:
                ensemble_stability = min(model_count / 5.0, 1.0)  # 5+ models = full stability
                stability_factors.append(ensemble_stability)

        # Data consistency stability
        expected_home = prediction_data.get('expected_home_goals', 1)
        expected_away = prediction_data.get('expected_away_goals', 1)

        # Check if goals and probabilities are consistent
        goal_ratio = expected_home / max(expected_away, 0.1)
        prob_ratio = home_prob / max(away_prob, 0.1)

        # Consistency between goal expectations and win probabilities
        consistency = 1.0 - min(abs(np.log(goal_ratio) - np.log(prob_ratio)) / 2.0, 1.0)
        stability_factors.append(consistency)

        return float(np.mean(stability_factors))

    def _integrate_confidence_factors(self, calibrated_confidence: float,
                                     ensemble_confidence: float,
                                     data_sufficiency: float,
                                     stability_score: float,
                                     validation_result: Any | None) -> float:
        """
        Integrate all confidence factors into final optimized confidence
        """

        # Weighted combination of different confidence estimates
        weights = {
            'calibrated': 0.4,      # Historical calibration
            'ensemble': 0.25,       # Ensemble agreement
            'sufficiency': 0.15,    # Data sufficiency
            'stability': 0.2        # Prediction stability
        }

        # Base integrated confidence
        integrated = (
            calibrated_confidence * weights['calibrated'] +
            ensemble_confidence * weights['ensemble'] +
            data_sufficiency * weights['sufficiency'] +
            stability_score * weights['stability']
        )

        # Apply validation result impact
        if validation_result and hasattr(validation_result, 'confidence_impact'):
            validation_multiplier = validation_result.confidence_impact
            integrated *= validation_multiplier

        # Apply data quality bonus
        if validation_result and hasattr(validation_result, 'quality_score'):
            quality_score = validation_result.quality_score
            if quality_score >= 90:
                integrated *= 1.08  # 8% bonus for excellent data
            elif quality_score >= 80:
                integrated *= 1.05  # 5% bonus for good data
            elif quality_score < 60:
                integrated *= 0.9   # 10% penalty for poor data

        # Ensure final confidence is within reasonable bounds
        final_confidence = float(np.clip(integrated,
                      self.confidence_thresholds['minimum_viable'],
                      self.confidence_thresholds['maximum_achievable']))

        return final_confidence

    def _get_league_prior_confidence(self, league: str) -> float:
        """Get prior confidence for specific league based on predictability"""
        league_priors = {
            'premier-league': 0.65,    # High competitiveness = moderate predictability
            'la-liga': 0.70,          # Slightly more predictable
            'bundesliga': 0.68,       # Good balance
            'serie-a': 0.72,          # Tactical league = more predictable
            'ligue-1': 0.60,          # PSG dominance but otherwise unpredictable
        }
        return league_priors.get(league, 0.65)  # Default

    def _classify_prediction_type(self, prediction_data: dict[str, Any]) -> str:
        """Classify prediction type for historical calibration"""

        home_prob = prediction_data.get('home_win_probability', 33)
        draw_prob = prediction_data.get('draw_probability', 33)
        away_prob = prediction_data.get('away_win_probability', 33)

        max_prob = max(home_prob, draw_prob, away_prob)

        if max_prob > 60:
            return 'strong_favorite'
        elif max_prob > 45:
            return 'moderate_favorite'
        else:
            return 'balanced_match'

    def _get_confidence_bucket(self, confidence: float) -> str:
        """Get confidence bucket for historical lookup"""
        if confidence >= 0.8:
            return 'high_confidence'
        elif confidence >= 0.6:
            return 'medium_confidence'
        else:
            return 'low_confidence'

    def update_historical_performance(self, prediction_data: dict[str, Any],
                                     actual_outcome: str,
                                     predicted_confidence: float) -> None:
        """
        Update historical performance data with actual outcomes

        This enables continuous learning and calibration improvement
        """

        prediction_type = self._classify_prediction_type(prediction_data)
        confidence_bucket = self._get_confidence_bucket(predicted_confidence)

        # Determine if prediction was correct
        home_prob = prediction_data.get('home_win_probability', 0)
        draw_prob = prediction_data.get('draw_probability', 0)
        away_prob = prediction_data.get('away_win_probability', 0)

        predicted_outcome = 'home' if home_prob == max(home_prob, draw_prob, away_prob) else \
                           'draw' if draw_prob == max(home_prob, draw_prob, away_prob) else 'away'

        was_correct = predicted_outcome == actual_outcome

        # Update historical performance
        if prediction_type not in self.historical_performance:
            self.historical_performance[prediction_type] = {}

        if confidence_bucket not in self.historical_performance[prediction_type]:
            self.historical_performance[prediction_type][confidence_bucket] = {
                'total_predictions': 0,
                'correct_predictions': 0,
                'accuracy': 0.0
            }

        bucket_data = self.historical_performance[prediction_type][confidence_bucket]
        bucket_data['total_predictions'] += 1
        if was_correct:
            bucket_data['correct_predictions'] += 1

        bucket_data['accuracy'] = bucket_data['correct_predictions'] / bucket_data['total_predictions']

        # Save updated performance data
        self.save_calibration_models()

    def get_confidence_recommendation(self, confidence_metrics: ConfidenceMetrics) -> dict[str, Any]:
        """
        Get actionable recommendations based on confidence analysis
        """

        final_confidence = confidence_metrics.final_confidence
        data_sufficiency = confidence_metrics.data_sufficiency

        key_factors: list[str] = []
        improvement_suggestions: list[str] = []

        recommendations: dict[str, Any] = {
            'confidence_level': 'high' if final_confidence >= 0.8 else
                              'medium' if final_confidence >= 0.6 else 'low',
            'recommendation': '',
            'key_factors': key_factors,
            'improvement_suggestions': improvement_suggestions,
            'reliability_assessment': ''
        }

        # Main recommendation
        if final_confidence >= 0.8:
            recommendations['recommendation'] = 'High confidence prediction - suitable for important decisions'
            recommendations['reliability_assessment'] = 'Very Reliable'
        elif final_confidence >= 0.6:
            recommendations['recommendation'] = 'Moderate confidence prediction - good for general analysis'
            recommendations['reliability_assessment'] = 'Reliable'
        else:
            recommendations['recommendation'] = 'Low confidence prediction - use with caution'
            recommendations['reliability_assessment'] = 'Limited Reliability'

        # Key factors
        if confidence_metrics.ensemble_agreement > 0.8:
            recommendations['key_factors'].append('Strong model agreement')
        if data_sufficiency > 0.8:
            recommendations['key_factors'].append('Comprehensive data available')
        if confidence_metrics.prediction_stability > 0.8:
            recommendations['key_factors'].append('Stable prediction across models')

        # Improvement suggestions
        if data_sufficiency < 0.6:
            recommendations['improvement_suggestions'].append('Collect more historical match data')
        if confidence_metrics.ensemble_agreement < 0.6:
            recommendations['improvement_suggestions'].append('Add more prediction models for validation')
        if confidence_metrics.prediction_stability < 0.6:
            recommendations['improvement_suggestions'].append('Review input data for inconsistencies')

        return recommendations

    def save_calibration_models(self) -> None:
        """Save calibration models and historical performance"""
        try:
            calibration_data = {
                'historical_performance': self.historical_performance,
                'confidence_thresholds': self.confidence_thresholds,
                'last_updated': datetime.now().isoformat()
            }

            with open(os.path.join(self.calibration_path, 'calibration_data.pkl'), 'wb') as f:
                pickle.dump(calibration_data, f)

            self.logger.info("Calibration data saved successfully")

        except Exception as e:
            self.logger.error(f"Failed to save calibration data: {e}")

    def load_calibration_models(self) -> None:
        """Load existing calibration models and historical performance"""
        try:
            calibration_file = os.path.join(self.calibration_path, 'calibration_data.pkl')

            if os.path.exists(calibration_file):
                with open(calibration_file, 'rb') as f:
                    calibration_data = pickle.load(f)

                self.historical_performance = calibration_data.get('historical_performance', {})
                self.confidence_thresholds.update(calibration_data.get('confidence_thresholds', {}))

                self.logger.info("Calibration data loaded successfully")
            else:
                self.logger.info("No existing calibration data found")

        except Exception as e:
            self.logger.warning(f"Failed to load calibration data: {e}")


# Example usage
if __name__ == "__main__":
    optimizer = ConfidenceOptimizer()

    # Example prediction data
    prediction_data = {
        'league': 'premier-league',
        'home_win_probability': 55.0,
        'draw_probability': 25.0,
        'away_win_probability': 20.0,
        'data_quality_score': 85,
        'home_performance_analysis': {'home': {'matches': 12}},
        'away_performance_analysis': {'away': {'matches': 10}},
        'head_to_head_analysis': {'total_meetings': 6},
        'data_sources_used': 2
    }

    # Optimize confidence
    confidence_metrics = optimizer.optimize_confidence(0.65, prediction_data)
    recommendations = optimizer.get_confidence_recommendation(confidence_metrics)

    print("Original Confidence: 65.0%")
    print(f"Optimized Confidence: {confidence_metrics.final_confidence:.1%}")
    print(f"Uncertainty Bounds: {confidence_metrics.uncertainty_bounds[0]:.1%} - {confidence_metrics.uncertainty_bounds[1]:.1%}")
    print(f"Recommendation: {recommendations['recommendation']}")
    print(f"Reliability: {recommendations['reliability_assessment']}")
