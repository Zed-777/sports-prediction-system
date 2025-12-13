"""
League-Specific Tuning Module for Phase 3

Manages per-league calibration and model weighting to capture league-specific
prediction patterns and characteristics.
"""

import json
import os
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import numpy as np

from app.models.calibration_manager import CalibrationManager, ModelPerformanceTracker


class LeagueTuner:
    """
    Manages league-specific model tuning and calibration.
    
    Each league gets its own:
    - Calibration manager (per-league isotonic regression)
    - Performance tracker (per-league model accuracy)
    - Characteristic adjustments (league pacing, defense, goals)
    
    This captures the fact that different leagues have different:
    - Scoring patterns (Bundesliga high-scoring, Serie A low-scoring)
    - Play styles (Premier League fast, Serie A slow)
    - Defensive strength (varying team quality distribution)
    """
    
    # League characteristics based on historical data
    LEAGUE_CHARACTERISTICS = {
        'la-liga': {
            'pacing': 'moderate',
            'defense': 'strong',
            'goals': 2.4,
            'goal_variance': 0.35,
            'description': 'Strong technical defense, moderate pacing'
        },
        'premier-league': {
            'pacing': 'fast',
            'defense': 'moderate',
            'goals': 2.8,
            'goal_variance': 0.45,
            'description': 'Fast-paced, physical play, moderate predictability'
        },
        'bundesliga': {
            'pacing': 'very_fast',
            'defense': 'weak',
            'goals': 3.1,
            'goal_variance': 0.55,
            'description': 'High-scoring, wide-open play, high variance'
        },
        'serie-a': {
            'pacing': 'slow',
            'defense': 'very_strong',
            'goals': 2.3,
            'goal_variance': 0.25,
            'description': 'Defensive, tactical, very predictable'
        },
        'ligue-1': {
            'pacing': 'moderate',
            'defense': 'moderate',
            'goals': 2.6,
            'goal_variance': 0.40,
            'description': 'Balanced play style'
        }
    }
    
    def __init__(self, leagues: Optional[List[str]] = None, cache_dir: Optional[str] = None):
        """
        Initialize LeagueTuner with per-league managers.
        
        Args:
            leagues: List of league keys to track. Defaults to all known leagues.
            cache_dir: Directory for persistence. Defaults to data/cache/
        """
        self.leagues = leagues or list(self.LEAGUE_CHARACTERISTICS.keys())
        self.cache_dir = cache_dir or 'data/cache'
        
        # Per-league calibration managers
        self.league_calibrators: Dict[str, CalibrationManager] = {
            league: CalibrationManager(model_name=f"ensemble_{league}")
            for league in self.leagues
        }
        
        # Per-league performance trackers
        self.league_trackers: Dict[str, ModelPerformanceTracker] = {
            league: ModelPerformanceTracker(
                model_names=[
                    f"xg_model_{league}",
                    f"poisson_model_{league}",
                    f"elo_model_{league}",
                    f"neural_model_{league}"
                ]
            )
            for league in self.leagues
        }
        
        # Per-league adjustment history
        self.adjustment_history: Dict[str, List[Dict]] = {league: [] for league in self.leagues}
        
        # Load persisted data
        self._load_league_data()
    
    def get_league_calibrator(self, league: str) -> Optional[CalibrationManager]:
        """Get calibration manager for specific league."""
        return self.league_calibrators.get(league)
    
    def get_league_tracker(self, league: str) -> Optional[ModelPerformanceTracker]:
        """Get performance tracker for specific league."""
        return self.league_trackers.get(league)
    
    def get_league_characteristics(self, league: str) -> Dict:
        """Get characteristic adjustments for league."""
        return self.LEAGUE_CHARACTERISTICS.get(
            league,
            self.LEAGUE_CHARACTERISTICS['premier-league']  # Default to Premier League
        )
    
    def get_league_weights(self, league: str) -> Dict[str, float]:
        """
        Get dynamic model weights for specific league.
        
        Returns weights based on per-league performance tracking.
        """
        tracker = self.get_league_tracker(league)
        if tracker:
            return tracker.calculate_dynamic_weights()
        return {}
    
    def record_league_match(
        self,
        league: str,
        prediction: float,
        outcome: float,
        model_predictions: Optional[Dict[str, float]] = None
    ) -> None:
        """
        Record match prediction and outcome for league learning.
        
        Args:
            league: League identifier
            prediction: Predicted probability (0.0-1.0)
            outcome: Actual outcome (0.0 or 1.0)
            model_predictions: Dict of individual model predictions for tracking
        """
        # Record in calibration manager
        cal = self.get_league_calibrator(league)
        if cal:
            cal.add_calibration_sample(prediction, outcome)
        
        # Record individual model performance
        if model_predictions:
            tracker = self.get_league_tracker(league)
            if tracker:
                for model_name, pred in model_predictions.items():
                    tracker.record_prediction(model_name, pred, outcome)
        
        # Track adjustment history
        self.adjustment_history[league].append({
            'timestamp': datetime.now().isoformat(),
            'prediction': prediction,
            'outcome': outcome,
            'calibrator_size': len(cal.calibration_data.get('predictions', [])) if cal else 0
        })
    
    def apply_league_adjustment(self, league: str, confidence: float) -> Tuple[float, Dict]:
        """
        Apply league-specific confidence adjustment.
        
        Adjusts confidence based on:
        - Goal variance (high variance leagues get lower confidence)
        - Defensive profile (defensive leagues get higher confidence)
        - Historical prediction accuracy
        
        Args:
            league: League identifier
            confidence: Raw confidence (0.0-1.0)
        
        Returns:
            Tuple of (adjusted_confidence, adjustment_metadata)
        """
        char = self.get_league_characteristics(league)
        metadata = {
            'league': league,
            'characteristics': char,
            'adjustments': {}
        }
        
        adjusted = confidence
        
        # 1. Goal variance adjustment
        # High-scoring, high-variance leagues (Bundesliga) are harder to predict
        goal_variance = char.get('goal_variance', 0.4)
        if goal_variance > 0.50:  # High variance
            variance_factor = 0.93  # Reduce by 7%
            metadata['adjustments']['goal_variance'] = variance_factor
            adjusted *= variance_factor
        elif goal_variance < 0.30:  # Low variance (predictable)
            variance_factor = 1.07  # Increase by 7%
            metadata['adjustments']['goal_variance'] = variance_factor
            adjusted *= variance_factor
        
        # 2. Defensive strength adjustment
        # Strong defensive leagues are more predictable
        defense = char.get('defense', 'moderate')
        defense_factors = {
            'very_strong': 1.08,
            'strong': 1.05,
            'moderate': 1.0,
            'weak': 0.95,
            'very_weak': 0.90
        }
        defense_factor = defense_factors.get(defense, 1.0)
        metadata['adjustments']['defense'] = defense_factor
        adjusted *= defense_factor
        
        # 3. Pacing adjustment
        # Faster-paced leagues have more volatility
        pacing = char.get('pacing', 'moderate')
        pacing_factors = {
            'very_fast': 0.96,
            'fast': 0.98,
            'moderate': 1.0,
            'slow': 1.02,
            'very_slow': 1.04
        }
        pacing_factor = pacing_factors.get(pacing, 1.0)
        metadata['adjustments']['pacing'] = pacing_factor
        adjusted *= pacing_factor
        
        # 4. Historical calibration adjustment
        # If per-league calibration exists and is trained, use it
        cal = self.get_league_calibrator(league)
        if cal and cal.is_trained and len(cal.calibration_data.get('predictions', [])) > 20:
            # Apply slight boost to calibrated probabilities (they're more reliable)
            calibration_factor = 1.02
            metadata['adjustments']['calibration_boost'] = calibration_factor
            adjusted *= calibration_factor
        
        # Clamp to valid probability range
        adjusted = max(0.0, min(1.0, adjusted))
        metadata['final_adjustment_factor'] = adjusted / confidence if confidence > 0 else 1.0
        
        return adjusted, metadata
    
    def get_league_statistics(self, league: str) -> Dict:
        """
        Get statistics for a specific league.
        
        Returns:
            Dict containing calibration samples, model performance, adjustment history
        """
        cal = self.get_league_calibrator(league)
        tracker = self.get_league_tracker(league)
        
        # Collect metrics for all models in tracker
        model_metrics = {}
        if tracker:
            for model_name in tracker.model_names:
                model_metrics[model_name] = tracker.get_model_metrics(model_name)
        
        stats = {
            'league': league,
            'characteristics': self.get_league_characteristics(league),
            'calibration': {
                'samples': len(cal.calibration_data.get('predictions', [])) if cal else 0,
                'ece': cal.get_calibration_stats().get('ece', 0.0) if cal else 0.0,
                'is_trained': cal.is_trained if cal else False
            },
            'model_performance': model_metrics,
            'adjustment_count': len(self.adjustment_history[league]),
            'recent_adjustments': self.adjustment_history[league][-10:] if self.adjustment_history[league] else []
        }
        
        return stats
    
    def get_all_league_statistics(self) -> Dict[str, Dict]:
        """Get statistics for all leagues."""
        return {league: self.get_league_statistics(league) for league in self.leagues}
    
    def _load_league_data(self) -> None:
        """Load persisted league calibration and performance data."""
        if not self.cache_dir or not os.path.exists(self.cache_dir):
            return
        
        for league in self.leagues:
            # Load calibration data
            cal_file = os.path.join(self.cache_dir, f'league_calibration_{league}.json')
            if os.path.exists(cal_file):
                try:
                    cal = self.get_league_calibrator(league)
                    if cal:
                        cal.load_calibration(cal_file)
                except Exception:
                    pass  # Silently fail if load is corrupted
            
            # Load performance data
            perf_file = os.path.join(self.cache_dir, f'league_performance_{league}.json')
            if os.path.exists(perf_file):
                try:
                    with open(perf_file, 'r') as f:
                        data = json.load(f)
                        tracker = self.get_league_tracker(league)
                        if tracker and 'performance_history' in data:
                            tracker.performance_history = data.get('performance_history', {})
                except Exception:
                    pass  # Silently fail if load is corrupted
    
    def save_league_data(self) -> None:
        """Save per-league calibration and performance data."""
        if not self.cache_dir:
            return
        
        os.makedirs(self.cache_dir, exist_ok=True)
        
        for league in self.leagues:
            # Save calibration data
            cal = self.get_league_calibrator(league)
            if cal:
                try:
                    cal_path = os.path.join(self.cache_dir, f'league_calibration_{league}.json')
                    cal.save_calibration(cal_path)
                except Exception:
                    pass  # Silently fail if save fails
            
            # Save performance data
            tracker = self.get_league_tracker(league)
            if tracker:
                perf_data = {
                    'league': league,
                    'performance_history': tracker.performance_history,
                    'current_weights': tracker.current_weights,
                    'saved_at': datetime.now().isoformat()
                }
                try:
                    with open(os.path.join(self.cache_dir, f'league_performance_{league}.json'), 'w') as f:
                        json.dump(perf_data, f, indent=2)
                except Exception:
                    pass  # Silently fail if save fails
