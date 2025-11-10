#!/usr/bin/env python3
"""
Machine Learning Enhancement System
Phase 2: Historical accuracy tracking, ensemble weighting, Bayesian updates, and neural networks
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import json
from dataclasses import dataclass
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, log_loss
from sklearn.preprocessing import StandardScaler
import joblib
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

@dataclass
class ModelPerformance:
    """Track model performance metrics"""
    model_name: str
    accuracy: float
    log_loss: float
    predictions_made: int
    last_updated: str
    weight: float  # Ensemble weight based on performance

@dataclass
class BayesianUpdate:
    """Bayesian rating update information"""
    team_name: str
    old_rating: float
    new_rating: float
    confidence: float
    matches_considered: int
    update_strength: float

class MachineLearningEnhancer:
    """Advanced ML system with ensemble methods and Bayesian updates"""
    
    def __init__(self):
        self.models_dir = Path("models/ml_enhanced")
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        # Model performance tracking
        self.model_performances: Dict[str, ModelPerformance] = {}
        
        # Bayesian team ratings (start with base ratings)
        self.bayesian_ratings = {
            'FC Barcelona': {'attack': 0.90, 'defense': 0.82, 'confidence': 0.8, 'matches': 50},
            'Real Madrid CF': {'attack': 0.92, 'defense': 0.88, 'confidence': 0.8, 'matches': 50},
            'Atlético Madrid': {'attack': 0.78, 'defense': 0.92, 'confidence': 0.8, 'matches': 45},
            'Sevilla FC': {'attack': 0.75, 'defense': 0.78, 'confidence': 0.7, 'matches': 40},
            'Villarreal CF': {'attack': 0.78, 'defense': 0.75, 'confidence': 0.7, 'matches': 38},
            'Real Betis Balompié': {'attack': 0.72, 'defense': 0.68, 'confidence': 0.6, 'matches': 35},
            'Athletic Bilbao': {'attack': 0.70, 'defense': 0.80, 'confidence': 0.6, 'matches': 35},
            'Valencia CF': {'attack': 0.68, 'defense': 0.70, 'confidence': 0.5, 'matches': 30},
            'Real Sociedad': {'attack': 0.75, 'defense': 0.78, 'confidence': 0.6, 'matches': 35},
            'RCD Mallorca': {'attack': 0.60, 'defense': 0.65, 'confidence': 0.4, 'matches': 25},
            'Girona FC': {'attack': 0.65, 'defense': 0.62, 'confidence': 0.3, 'matches': 20},
            'RCD Espanyol de Barcelona': {'attack': 0.55, 'defense': 0.60, 'confidence': 0.4, 'matches': 25},
            'Real Oviedo': {'attack': 0.58, 'defense': 0.62, 'confidence': 0.3, 'matches': 20}
        }
        
        # Initialize ensemble models
        self.ensemble_models = self._initialize_models()
        self.scaler = StandardScaler()
        
        # Load historical performance if exists
        self._load_model_performances()
        
    def _initialize_models(self) -> Dict:
        """Initialize the ensemble of ML models"""
        
        models = {
            'gradient_boosting': GradientBoostingClassifier(
                n_estimators=100, max_depth=6, learning_rate=0.1, random_state=42
            ),
            'random_forest': RandomForestClassifier(
                n_estimators=100, max_depth=8, random_state=42
            ),
            'logistic_regression': LogisticRegression(
                max_iter=1000, random_state=42
            )
        }
        
        return models
    
    def generate_features(self, home_team: str, away_team: str, 
                         match_data: Dict, realtime_data: Dict) -> np.ndarray:
        """Generate comprehensive feature vector for ML models"""
        
        features = []
        
        # Basic team strength features
        home_ratings = self.bayesian_ratings.get(home_team, {'attack': 0.5, 'defense': 0.5})
        away_ratings = self.bayesian_ratings.get(away_team, {'attack': 0.5, 'defense': 0.5})
        
        features.extend([
            home_ratings['attack'],
            home_ratings['defense'],
            away_ratings['attack'],
            away_ratings['defense'],
            home_ratings['attack'] - away_ratings['defense'],  # Attack vs Defense matchup
            away_ratings['attack'] - home_ratings['defense']   # Attack vs Defense matchup
        ])
        
        # Form features
        if 'real_time_enhancements' in realtime_data:
            enhancements = realtime_data['real_time_enhancements']
            
            # Recent form
            home_form = enhancements.get('home_team_form', {})
            away_form = enhancements.get('away_team_form', {})
            
            features.extend([
                home_form.get('form_rating', 0.5),
                away_form.get('form_rating', 0.5),
                home_form.get('goals_per_game', 1.0),
                away_form.get('goals_per_game', 1.0),
                home_form.get('xg_performance', 1.0),
                away_form.get('xg_performance', 1.0)
            ])
            
            # Player availability
            availability = enhancements.get('player_availability', {})
            features.extend([
                availability.get('home_availability_multiplier', 1.0),
                availability.get('away_availability_multiplier', 1.0)
            ])
            
            # Weather impact
            weather = enhancements.get('weather_conditions', {})
            features.extend([
                weather.get('temperature', 18.0) / 40.0,  # Normalize
                weather.get('playing_impact', 0.0)
            ])
            
            # Referee bias
            referee = enhancements.get('referee_profile', {})
            features.extend([
                referee.get('home_bias', 0.0),
                referee.get('strictness', 0.5)
            ])
        else:
            # Fallback features
            features.extend([0.5, 0.5, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 18.0/40.0, 0.0, 0.0, 0.5])
        
        # Historical head-to-head (simulated)
        h2h_home_wins = np.random.beta(2, 2)  # Historical home win rate
        h2h_draws = np.random.beta(1.5, 3)    # Historical draw rate
        
        features.extend([h2h_home_wins, h2h_draws])
        
        # Seasonal context
        current_month = datetime.now().month
        features.extend([
            np.sin(2 * np.pi * current_month / 12),  # Seasonal sine
            np.cos(2 * np.pi * current_month / 12)   # Seasonal cosine
        ])
        
        # Match importance (simulated based on league position)
        match_importance = np.random.uniform(0.3, 1.0)
        features.append(match_importance)
        
        return np.array(features).reshape(1, -1)
    
    def train_ensemble_models(self, training_data: List[Dict]) -> Dict[str, float]:
        """Train all ensemble models on historical data"""
        
        print("🤖 Training ML ensemble models...")
        
        if len(training_data) < 50:
            print("⚠️  Insufficient training data, using simulated dataset")
            training_data = self._generate_simulated_training_data(200)
        
        # Prepare training data
        X_train = []
        y_train = []
        
        for match in training_data:
            features = self.generate_features(
                match['home_team'], 
                match['away_team'], 
                match, 
                match.get('realtime_data', {})
            )
            X_train.append(features.flatten())
            
            # Convert result to class (0: away win, 1: draw, 2: home win)
            result = match.get('result', np.random.choice([0, 1, 2], p=[0.3, 0.25, 0.45]))
            y_train.append(result)
        
        X_train = np.array(X_train)
        y_train = np.array(y_train)
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        
        # Train each model and evaluate
        model_scores = {}
        
        for name, model in self.ensemble_models.items():
            print(f"  Training {name}...")
            
            # Train model
            model.fit(X_train_scaled, y_train)
            
            # Evaluate on training data (in production, use cross-validation)
            y_pred = model.predict(X_train_scaled)
            y_pred_proba = model.predict_proba(X_train_scaled)
            
            accuracy = accuracy_score(y_train, y_pred)
            logloss = log_loss(y_train, y_pred_proba)
            
            # Update model performance
            self.model_performances[name] = ModelPerformance(
                model_name=name,
                accuracy=float(accuracy),
                log_loss=float(logloss),
                predictions_made=len(y_train),
                last_updated=datetime.now().isoformat(),
                weight=self._calculate_model_weight(float(accuracy), float(logloss))
            )
            
            model_scores[name] = accuracy
            
            # Save model
            model_file = self.models_dir / f"{name}_model.joblib"
            joblib.dump(model, model_file)
            
            print(f"    ✅ {name}: {accuracy:.3f} accuracy, {logloss:.3f} log-loss")
        
        # Save scaler
        scaler_file = self.models_dir / "feature_scaler.joblib"
        joblib.dump(self.scaler, scaler_file)
        
        # Save model performances
        self._save_model_performances()
        
        return model_scores
    
    def _calculate_model_weight(self, accuracy: float, log_loss: float) -> float:
        """Calculate ensemble weight based on model performance"""
        
        # Weight based on accuracy (0.6 weight) and inverse log-loss (0.4 weight)
        accuracy_weight = accuracy * 0.6
        logloss_weight = (1.0 / (1.0 + log_loss)) * 0.4
        
        total_weight = accuracy_weight + logloss_weight
        return min(1.0, max(0.1, total_weight))  # Clamp between 0.1 and 1.0
    
    def predict_with_ensemble(self, home_team: str, away_team: str, 
                            match_data: Dict, realtime_data: Dict) -> Dict:
        """Make predictions using weighted ensemble"""
        
        # Generate features
        features = self.generate_features(home_team, away_team, match_data, realtime_data)
        features_scaled = self.scaler.transform(features)
        
        # Get predictions from each model
        ensemble_predictions = {}
        weighted_probabilities = np.zeros(3)  # [away_win, draw, home_win]
        total_weight = 0.0
        
        for name, model in self.ensemble_models.items():
            try:
                # Get model prediction probabilities
                model_proba = model.predict_proba(features_scaled)[0]
                
                # Get model weight
                weight = self.model_performances.get(name, ModelPerformance(
                    name, 0.5, 1.0, 0, datetime.now().isoformat(), 0.5
                )).weight
                
                # Weighted average
                weighted_probabilities += model_proba * weight
                total_weight += weight
                
                ensemble_predictions[name] = {
                    'probabilities': model_proba.tolist(),
                    'weight': weight,
                    'confidence': weight  # Use weight as confidence proxy
                }
                
            except Exception as e:
                print(f"⚠️  Model {name} prediction failed: {e}")
                continue
        
        # Normalize weighted probabilities
        if total_weight > 0:
            final_probabilities = weighted_probabilities / total_weight
        else:
            final_probabilities = np.array([0.3, 0.25, 0.45])  # Fallback
        
        # Calculate ensemble confidence
        # Higher confidence when models agree, lower when they disagree
        model_agreement = self._calculate_model_agreement(ensemble_predictions)
        ensemble_confidence = 0.5 + (model_agreement * 0.4)  # 0.5 to 0.9 range
        
        return {
            'ensemble_probabilities': {
                'away_win_prob': round(final_probabilities[0], 3),
                'draw_prob': round(final_probabilities[1], 3),
                'home_win_prob': round(final_probabilities[2], 3)
            },
            'ensemble_confidence': round(ensemble_confidence, 3),
            'individual_models': ensemble_predictions,
            'model_agreement_score': round(model_agreement, 3),
            'total_models_used': len(ensemble_predictions)
        }
    
    def _calculate_model_agreement(self, predictions: Dict) -> float:
        """Calculate how much the models agree with each other"""
        
        if len(predictions) < 2:
            return 0.5
        
        # Calculate variance in predictions across models
        all_probs = []
        for model_pred in predictions.values():
            all_probs.append(model_pred['probabilities'])
        
        all_probs = np.array(all_probs)
        
        # Calculate average variance across the three outcomes
        variances = np.var(all_probs, axis=0)
        avg_variance = np.mean(variances)
        
        # Convert variance to agreement score (lower variance = higher agreement)
        agreement = max(0.0, 1.0 - (avg_variance * 10))  # Scale variance
        
        return agreement
    
    def update_bayesian_ratings(self, match_result: Dict) -> List[BayesianUpdate]:
        """Update team ratings using Bayesian inference"""
        
        home_team = match_result['home_team']
        away_team = match_result['away_team']
        home_score = match_result['home_score']
        away_score = match_result['away_score']
        
        updates = []
        
        # Update home team
        home_update = self._bayesian_team_update(
            home_team, home_score, away_score, is_home=True
        )
        updates.append(home_update)
        
        # Update away team
        away_update = self._bayesian_team_update(
            away_team, away_score, home_score, is_home=False
        )
        updates.append(away_update)
        
        print(f"🔄 Bayesian updates: {home_team} ({home_update.old_rating:.3f}→{home_update.new_rating:.3f}), "
              f"{away_team} ({away_update.old_rating:.3f}→{away_update.new_rating:.3f})")
        
        return updates
    
    def _bayesian_team_update(self, team_name: str, goals_for: int, goals_against: int, 
                            is_home: bool) -> BayesianUpdate:
        """Perform Bayesian update for a single team"""
        
        if team_name not in self.bayesian_ratings:
            # Initialize new team
            self.bayesian_ratings[team_name] = {
                'attack': 0.55, 'defense': 0.55, 'confidence': 0.1, 'matches': 0
            }
        
        current = self.bayesian_ratings[team_name]
        old_attack = current['attack']
        old_defense = current['defense']
        
        # Calculate expected performance vs actual
        expected_goals_for = old_attack * 1.5  # Expected goals (simplified)
        expected_goals_against = (1.0 - old_defense) * 1.5
        
        # Home advantage adjustment
        if is_home:
            expected_goals_for *= 1.15
            expected_goals_against *= 0.9
        
        # Performance relative to expectation
        attack_performance = goals_for / max(0.1, expected_goals_for)
        defense_performance = expected_goals_against / max(0.1, goals_against + 0.1)
        
        # Bayesian update strength (more matches = smaller updates)
        matches = current['matches']
        update_strength = 1.0 / (1.0 + matches * 0.1)  # Decay update strength
        
        # Update ratings
        new_attack = old_attack + (attack_performance - 1.0) * update_strength * 0.1
        new_defense = old_defense + (defense_performance - 1.0) * update_strength * 0.1
        
        # Clamp ratings
        new_attack = max(0.2, min(0.98, new_attack))
        new_defense = max(0.2, min(0.98, new_defense))
        
        # Update confidence based on number of matches
        new_confidence = min(0.9, current['confidence'] + 0.02)
        
        # Update stored ratings
        self.bayesian_ratings[team_name] = {
            'attack': new_attack,
            'defense': new_defense,
            'confidence': new_confidence,
            'matches': matches + 1
        }
        
        # Calculate overall rating change
        old_rating = (old_attack + old_defense) / 2
        new_rating = (new_attack + new_defense) / 2
        
        return BayesianUpdate(
            team_name=team_name,
            old_rating=old_rating,
            new_rating=new_rating,
            confidence=new_confidence,
            matches_considered=matches + 1,
            update_strength=update_strength
        )
    
    def _generate_simulated_training_data(self, num_matches: int) -> List[Dict]:
        """Generate simulated training data for model training"""
        
        teams = list(self.bayesian_ratings.keys())
        training_data = []
        
        for i in range(num_matches):
            home_team = np.random.choice(teams)
            away_team = np.random.choice([t for t in teams if t != home_team])
            
            # Simulate match result based on team strengths
            home_strength = (self.bayesian_ratings[home_team]['attack'] + 
                           self.bayesian_ratings[home_team]['defense']) / 2
            away_strength = (self.bayesian_ratings[away_team]['attack'] + 
                           self.bayesian_ratings[away_team]['defense']) / 2
            
            strength_diff = home_strength - away_strength + 0.1  # Home advantage
            
            if strength_diff > 0.15:
                result = np.random.choice([0, 1, 2], p=[0.15, 0.25, 0.60])
            elif strength_diff > 0.05:
                result = np.random.choice([0, 1, 2], p=[0.25, 0.30, 0.45])
            else:
                result = np.random.choice([0, 1, 2], p=[0.35, 0.35, 0.30])
            
            match_data = {
                'home_team': home_team,
                'away_team': away_team,
                'result': result,
                'realtime_data': {
                    'real_time_enhancements': {
                        'home_team_form': {'form_rating': np.random.uniform(0.2, 0.8)},
                        'away_team_form': {'form_rating': np.random.uniform(0.2, 0.8)},
                        'player_availability': {
                            'home_availability_multiplier': np.random.uniform(0.8, 1.0),
                            'away_availability_multiplier': np.random.uniform(0.8, 1.0)
                        },
                        'weather_conditions': {'playing_impact': np.random.uniform(0.0, 0.2)},
                        'referee_profile': {'home_bias': np.random.uniform(-0.1, 0.1)}
                    }
                }
            }
            
            training_data.append(match_data)
        
        return training_data
    
    def _load_model_performances(self):
        """Load saved model performance metrics"""
        perf_file = self.models_dir / "model_performances.json"
        if perf_file.exists():
            try:
                with open(perf_file, 'r') as f:
                    data = json.load(f)
                    for name, perf_data in data.items():
                        self.model_performances[name] = ModelPerformance(**perf_data)
            except Exception as e:
                print(f"⚠️  Failed to load model performances: {e}")
    
    def _save_model_performances(self):
        """Save model performance metrics"""
        perf_file = self.models_dir / "model_performances.json"
        data = {}
        for name, perf in self.model_performances.items():
            data[name] = {
                'model_name': perf.model_name,
                'accuracy': perf.accuracy,
                'log_loss': perf.log_loss,
                'predictions_made': perf.predictions_made,
                'last_updated': perf.last_updated,
                'weight': perf.weight
            }
        
        with open(perf_file, 'w') as f:
            json.dump(data, f, indent=2)

def main():
    """Test ML enhancement system"""
    enhancer = MachineLearningEnhancer()
    
    # Train models
    print("🤖 Training ML Enhancement System...")
    scores = enhancer.train_ensemble_models([])
    
    # Test prediction
    sample_match = {
        'id': 544293,
        'homeTeam': {'name': 'FC Barcelona'},
        'awayTeam': {'name': 'Girona FC'}
    }
    
    sample_realtime = {
        'real_time_enhancements': {
            'home_team_form': {'form_rating': 0.8, 'goals_per_game': 2.1, 'xg_performance': 2.0},
            'away_team_form': {'form_rating': 0.6, 'goals_per_game': 1.2, 'xg_performance': 1.1},
            'player_availability': {
                'home_availability_multiplier': 0.95,
                'away_availability_multiplier': 0.85
            },
            'weather_conditions': {'temperature': 22.0, 'playing_impact': 0.0},
            'referee_profile': {'home_bias': 0.02, 'strictness': 0.75}
        }
    }
    
    prediction = enhancer.predict_with_ensemble(
        'FC Barcelona', 'Girona FC', sample_match, sample_realtime
    )
    
    print("\n🎯 ML Ensemble Prediction:")
    print(json.dumps(prediction, indent=2))

if __name__ == "__main__":
    main()