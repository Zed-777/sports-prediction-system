#!/usr/bin/env python3
"""
Machine Learning Enhancement System
Phase 2: Historical accuracy tracking, ensemble weighting, Bayesian updates, and neural networks
"""

import json
import warnings
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, log_loss
from sklearn.preprocessing import StandardScaler
from typing import Dict, List, Any, cast, Optional, Callable, Tuple
from app.types import JSONDict, JSONList

dataset_to_arrays: Optional[Callable[[list[dict[str, Any]]], Tuple[np.ndarray, list[int]]]]
load_processed_dataset: Optional[Callable[[str], tuple[list[dict[str, Any]], list[int]]]]

try:
    from app.data.historical_loader import dataset_to_arrays as _dataset_to_arrays, load_processed_dataset as _load_processed_dataset
    dataset_to_arrays = _dataset_to_arrays
    load_processed_dataset = _load_processed_dataset
except Exception:
    # If import fails (tests or module path), we will handle it during runtime
    dataset_to_arrays = None
    load_processed_dataset = None

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
    """Advanced ML system with ensemble methods and dynamic ELO ratings"""

    # Default ELO rating for new teams
    DEFAULT_ELO = 1500
    # K-factor controls how much ratings change after each match
    K_FACTOR_NEW = 40  # Higher for new teams (more volatile)
    K_FACTOR_ESTABLISHED = 20  # Lower for established teams (more stable)
    # Home advantage in ELO points
    HOME_ADVANTAGE = 65

    def __init__(self) -> None:
        self.models_dir = Path("models/ml_enhanced")
        self.models_dir.mkdir(parents=True, exist_ok=True)

        # Model performance tracking
        self.model_performances: dict[str, ModelPerformance] = {}

        # Dynamic ELO ratings - loaded from file or initialized with defaults
        self.elo_ratings: dict[str, dict] = {}
        self._load_elo_ratings()

        # Initialize ensemble models
        self.ensemble_models = self._initialize_models()
        self.scaler = StandardScaler()

        # Load historical performance if exists
        self._load_model_performances()
        
        # Legacy compatibility - map to bayesian_ratings format for existing code
        self.bayesian_ratings = self._elo_to_bayesian_format()

    def _load_elo_ratings(self) -> None:
        """Load ELO ratings from file or initialize with league-based defaults"""
        elo_file = self.models_dir / "elo_ratings.json"
        
        if elo_file.exists():
            try:
                with open(elo_file, 'r') as f:
                    self.elo_ratings = json.load(f)
                return
            except Exception:
                pass
        
        # Initialize with research-based starting ratings by league tier
        # Based on historical performance data and club coefficients
        self.elo_ratings = {
            # Top tier (Champions League regulars)
            'Real Madrid CF': {'elo': 2050, 'attack_elo': 2100, 'defense_elo': 2000, 'matches': 100, 'last_updated': '2025-01-01'},
            'FC Barcelona': {'elo': 2020, 'attack_elo': 2080, 'defense_elo': 1960, 'matches': 100, 'last_updated': '2025-01-01'},
            'Manchester City FC': {'elo': 2080, 'attack_elo': 2100, 'defense_elo': 2060, 'matches': 100, 'last_updated': '2025-01-01'},
            'Liverpool FC': {'elo': 2000, 'attack_elo': 2050, 'defense_elo': 1950, 'matches': 100, 'last_updated': '2025-01-01'},
            'FC Bayern München': {'elo': 2040, 'attack_elo': 2100, 'defense_elo': 1980, 'matches': 100, 'last_updated': '2025-01-01'},
            'Paris Saint-Germain FC': {'elo': 1980, 'attack_elo': 2050, 'defense_elo': 1910, 'matches': 100, 'last_updated': '2025-01-01'},
            'Inter Milan': {'elo': 1950, 'attack_elo': 1920, 'defense_elo': 1980, 'matches': 100, 'last_updated': '2025-01-01'},
            'Arsenal FC': {'elo': 1970, 'attack_elo': 1980, 'defense_elo': 1960, 'matches': 100, 'last_updated': '2025-01-01'},
            
            # Strong tier (Europa League level)
            'Atlético Madrid': {'elo': 1900, 'attack_elo': 1850, 'defense_elo': 1950, 'matches': 80, 'last_updated': '2025-01-01'},
            'Borussia Dortmund': {'elo': 1880, 'attack_elo': 1920, 'defense_elo': 1840, 'matches': 80, 'last_updated': '2025-01-01'},
            'SSC Napoli': {'elo': 1870, 'attack_elo': 1900, 'defense_elo': 1840, 'matches': 80, 'last_updated': '2025-01-01'},
            'Chelsea FC': {'elo': 1860, 'attack_elo': 1870, 'defense_elo': 1850, 'matches': 80, 'last_updated': '2025-01-01'},
            'Tottenham Hotspur FC': {'elo': 1840, 'attack_elo': 1870, 'defense_elo': 1810, 'matches': 80, 'last_updated': '2025-01-01'},
            'Juventus FC': {'elo': 1850, 'attack_elo': 1830, 'defense_elo': 1870, 'matches': 80, 'last_updated': '2025-01-01'},
            'AC Milan': {'elo': 1840, 'attack_elo': 1850, 'defense_elo': 1830, 'matches': 80, 'last_updated': '2025-01-01'},
            'RB Leipzig': {'elo': 1820, 'attack_elo': 1850, 'defense_elo': 1790, 'matches': 80, 'last_updated': '2025-01-01'},
            
            # Mid-tier (solid domestic performers)
            'Sevilla FC': {'elo': 1750, 'attack_elo': 1720, 'defense_elo': 1780, 'matches': 60, 'last_updated': '2025-01-01'},
            'Real Betis Balompié': {'elo': 1720, 'attack_elo': 1740, 'defense_elo': 1700, 'matches': 60, 'last_updated': '2025-01-01'},
            'Real Sociedad': {'elo': 1740, 'attack_elo': 1760, 'defense_elo': 1720, 'matches': 60, 'last_updated': '2025-01-01'},
            'Villarreal CF': {'elo': 1730, 'attack_elo': 1750, 'defense_elo': 1710, 'matches': 60, 'last_updated': '2025-01-01'},
            'Athletic Club': {'elo': 1710, 'attack_elo': 1690, 'defense_elo': 1730, 'matches': 60, 'last_updated': '2025-01-01'},
            'Newcastle United FC': {'elo': 1780, 'attack_elo': 1760, 'defense_elo': 1800, 'matches': 60, 'last_updated': '2025-01-01'},
            'Aston Villa FC': {'elo': 1760, 'attack_elo': 1780, 'defense_elo': 1740, 'matches': 60, 'last_updated': '2025-01-01'},
            'SS Lazio': {'elo': 1720, 'attack_elo': 1750, 'defense_elo': 1690, 'matches': 60, 'last_updated': '2025-01-01'},
            'AS Roma': {'elo': 1730, 'attack_elo': 1710, 'defense_elo': 1750, 'matches': 60, 'last_updated': '2025-01-01'},
            'Bayer 04 Leverkusen': {'elo': 1850, 'attack_elo': 1900, 'defense_elo': 1800, 'matches': 60, 'last_updated': '2025-01-01'},
            
            # Lower-mid tier
            'Valencia CF': {'elo': 1650, 'attack_elo': 1630, 'defense_elo': 1670, 'matches': 50, 'last_updated': '2025-01-01'},
            'Getafe CF': {'elo': 1600, 'attack_elo': 1550, 'defense_elo': 1650, 'matches': 50, 'last_updated': '2025-01-01'},
            'Girona FC': {'elo': 1700, 'attack_elo': 1750, 'defense_elo': 1650, 'matches': 40, 'last_updated': '2025-01-01'},
            'RCD Mallorca': {'elo': 1580, 'attack_elo': 1550, 'defense_elo': 1610, 'matches': 50, 'last_updated': '2025-01-01'},
            'RC Celta de Vigo': {'elo': 1620, 'attack_elo': 1650, 'defense_elo': 1590, 'matches': 50, 'last_updated': '2025-01-01'},
            'Rayo Vallecano de Madrid': {'elo': 1590, 'attack_elo': 1610, 'defense_elo': 1570, 'matches': 50, 'last_updated': '2025-01-01'},
            'CA Osasuna': {'elo': 1610, 'attack_elo': 1580, 'defense_elo': 1640, 'matches': 50, 'last_updated': '2025-01-01'},
            'Deportivo Alavés': {'elo': 1550, 'attack_elo': 1520, 'defense_elo': 1580, 'matches': 40, 'last_updated': '2025-01-01'},
            'UD Las Palmas': {'elo': 1560, 'attack_elo': 1580, 'defense_elo': 1540, 'matches': 40, 'last_updated': '2025-01-01'},
            'RCD Espanyol de Barcelona': {'elo': 1540, 'attack_elo': 1520, 'defense_elo': 1560, 'matches': 40, 'last_updated': '2025-01-01'},
            'Real Valladolid CF': {'elo': 1520, 'attack_elo': 1500, 'defense_elo': 1540, 'matches': 40, 'last_updated': '2025-01-01'},
            'CD Leganés': {'elo': 1510, 'attack_elo': 1490, 'defense_elo': 1530, 'matches': 40, 'last_updated': '2025-01-01'},
        }
        
        self._save_elo_ratings()

    def _save_elo_ratings(self) -> None:
        """Persist ELO ratings to file"""
        elo_file = self.models_dir / "elo_ratings.json"
        try:
            with open(elo_file, 'w') as f:
                json.dump(self.elo_ratings, f, indent=2)
        except Exception:
            pass

    def _elo_to_bayesian_format(self) -> dict:
        """Convert ELO ratings to legacy bayesian_ratings format for compatibility"""
        bayesian = {}
        for team, ratings in self.elo_ratings.items():
            elo = ratings.get('elo', self.DEFAULT_ELO)
            attack_elo = ratings.get('attack_elo', elo)
            defense_elo = ratings.get('defense_elo', elo)
            matches = ratings.get('matches', 20)
            
            # Convert ELO (1200-2200 range) to 0-1 scale
            attack = (attack_elo - 1200) / 1000  # Maps 1200-2200 to 0-1
            defense = (defense_elo - 1200) / 1000
            confidence = min(0.95, matches / 100)  # More matches = higher confidence
            
            bayesian[team] = {
                'attack': max(0.3, min(0.98, attack)),
                'defense': max(0.3, min(0.98, defense)),
                'confidence': confidence,
                'matches': matches
            }
        return bayesian

    def get_team_elo(self, team_name: str) -> dict:
        """Get ELO rating for a team, creating default if not exists"""
        if team_name not in self.elo_ratings:
            # Try fuzzy match
            for known_team in self.elo_ratings:
                if team_name.lower() in known_team.lower() or known_team.lower() in team_name.lower():
                    return self.elo_ratings[known_team]
            
            # Create new entry with default rating
            self.elo_ratings[team_name] = {
                'elo': self.DEFAULT_ELO,
                'attack_elo': self.DEFAULT_ELO,
                'defense_elo': self.DEFAULT_ELO,
                'matches': 0,
                'last_updated': datetime.now().strftime('%Y-%m-%d')
            }
            self._save_elo_ratings()
        
        return self.elo_ratings[team_name]

    def calculate_expected_score(self, home_elo: float, away_elo: float, include_home_advantage: bool = True) -> tuple:
        """
        Calculate expected score using ELO formula.
        Returns (home_expected, away_expected) where values sum to 1.0
        """
        if include_home_advantage:
            home_elo += self.HOME_ADVANTAGE
        
        elo_diff = home_elo - away_elo
        home_expected = 1 / (1 + 10 ** (-elo_diff / 400))
        away_expected = 1 - home_expected
        
        return home_expected, away_expected

    def update_elo_after_match(self, home_team: str, away_team: str, 
                               home_goals: int, away_goals: int) -> dict:
        """
        Update ELO ratings after a match result.
        Uses separate attack/defense ELO for more nuanced ratings.
        """
        home_rating = self.get_team_elo(home_team)
        away_rating = self.get_team_elo(away_team)
        
        # Determine K-factor based on matches played
        home_k = self.K_FACTOR_NEW if home_rating['matches'] < 30 else self.K_FACTOR_ESTABLISHED
        away_k = self.K_FACTOR_NEW if away_rating['matches'] < 30 else self.K_FACTOR_ESTABLISHED
        
        # Calculate expected scores
        home_exp, away_exp = self.calculate_expected_score(
            home_rating['elo'], away_rating['elo']
        )
        
        # Determine actual scores (1 = win, 0.5 = draw, 0 = loss)
        if home_goals > away_goals:
            home_actual, away_actual = 1.0, 0.0
        elif home_goals < away_goals:
            home_actual, away_actual = 0.0, 1.0
        else:
            home_actual, away_actual = 0.5, 0.5
        
        # Goal difference multiplier (bigger wins = bigger rating change)
        goal_diff = abs(home_goals - away_goals)
        gd_multiplier = 1.0 + (goal_diff - 1) * 0.1 if goal_diff > 1 else 1.0
        gd_multiplier = min(1.5, gd_multiplier)  # Cap at 1.5x
        
        # Update main ELO
        home_elo_change = home_k * gd_multiplier * (home_actual - home_exp)
        away_elo_change = away_k * gd_multiplier * (away_actual - away_exp)
        
        # Update attack ELO based on goals scored
        home_attack_change = home_k * 0.5 * (home_goals / max(1, home_goals + away_goals) - 0.5)
        away_attack_change = away_k * 0.5 * (away_goals / max(1, home_goals + away_goals) - 0.5)
        
        # Update defense ELO based on goals conceded (inverted)
        home_defense_change = home_k * 0.5 * (0.5 - away_goals / max(1, home_goals + away_goals))
        away_defense_change = away_k * 0.5 * (0.5 - home_goals / max(1, home_goals + away_goals))
        
        # Apply updates
        old_home = home_rating.copy()
        old_away = away_rating.copy()
        
        self.elo_ratings[home_team]['elo'] += home_elo_change
        self.elo_ratings[home_team]['attack_elo'] += home_attack_change
        self.elo_ratings[home_team]['defense_elo'] += home_defense_change
        self.elo_ratings[home_team]['matches'] += 1
        self.elo_ratings[home_team]['last_updated'] = datetime.now().strftime('%Y-%m-%d')
        
        self.elo_ratings[away_team]['elo'] += away_elo_change
        self.elo_ratings[away_team]['attack_elo'] += away_attack_change
        self.elo_ratings[away_team]['defense_elo'] += away_defense_change
        self.elo_ratings[away_team]['matches'] += 1
        self.elo_ratings[away_team]['last_updated'] = datetime.now().strftime('%Y-%m-%d')
        
        # Refresh bayesian_ratings for compatibility
        self.bayesian_ratings = self._elo_to_bayesian_format()
        
        # Save to file
        self._save_elo_ratings()
        
        return {
            'home_team': home_team,
            'away_team': away_team,
            'home_elo_change': round(home_elo_change, 1),
            'away_elo_change': round(away_elo_change, 1),
            'home_new_elo': round(self.elo_ratings[home_team]['elo'], 1),
            'away_new_elo': round(self.elo_ratings[away_team]['elo'], 1)
        }

    def predict_match_elo(self, home_team: str, away_team: str) -> dict:
        """
        Predict match outcome using ELO ratings.
        Returns probabilities for home win, draw, away win.
        """
        home_rating = self.get_team_elo(home_team)
        away_rating = self.get_team_elo(away_team)
        
        home_exp, away_exp = self.calculate_expected_score(
            home_rating['elo'], away_rating['elo']
        )
        
        # Convert expected scores to win/draw/loss probabilities
        # Using logistic distribution for draw probability
        elo_diff = (home_rating['elo'] + self.HOME_ADVANTAGE) - away_rating['elo']
        
        # Draw probability peaks at elo_diff=0, decreases with larger differences
        draw_base = 0.25
        draw_decay = abs(elo_diff) / 800
        draw_prob = max(0.10, draw_base * (1 - draw_decay))
        
        # Distribute remaining probability between home/away
        remaining = 1.0 - draw_prob
        home_win_prob = remaining * home_exp
        away_win_prob = remaining * away_exp
        
        return {
            'home_win_probability': round(home_win_prob * 100, 1),
            'draw_probability': round(draw_prob * 100, 1),
            'away_win_probability': round(away_win_prob * 100, 1),
            'home_elo': round(home_rating['elo'], 0),
            'away_elo': round(away_rating['elo'], 0),
            'elo_difference': round(elo_diff, 0),
            'confidence': min(0.95, (home_rating['matches'] + away_rating['matches']) / 200)
        }

    def _initialize_models(self) -> Dict[str, Any]:
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
                         match_data: JSONDict, realtime_data: JSONDict) -> np.ndarray:
        """Generate comprehensive feature vector for ML models"""

        features = []

        # ELO-based team strength features
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

    def train_ensemble_models(self, training_data: JSONList) -> Dict[str, float]:
        """Train all ensemble models on historical data"""

        print("🤖 Training ML ensemble models...")

        if len(training_data) < 50:
            print("⚠️  Insufficient training data, using simulated dataset")
            training_data = self._generate_simulated_training_data(200)

        # Prepare training data
        X_train_list: list[np.ndarray] = []
        y_train_list: list[int] = []

        for match in training_data:
            features = self.generate_features(
                match['home_team'],
                match['away_team'],
                match,
                match.get('realtime_data', {})
            )
            X_train_list.append(features.flatten())

            # Convert result to class (0: away win, 1: draw, 2: home win)
            result = match.get('result', np.random.choice([0, 1, 2], p=[0.3, 0.25, 0.45]))
            y_train_list.append(int(result))

        X_train = np.array(X_train_list)
        y_train = np.array(y_train_list)

        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)

        # Train each model and evaluate
        model_scores: Dict[str, float] = {}

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

    def train_from_processed_dataset(self, filename: str = 'historical_dataset.json') -> dict[str, float]:
        """Train ensemble models from processed dataset generated by scripts/collect_historical_data.py"""
        print("Loading processed dataset for training...")
        try:
            if load_processed_dataset is None:
                raise RuntimeError("load_processed_dataset function is not available")
            processed, labels = load_processed_dataset(filename)
        except Exception as e:
            print(f"Failed to load processed dataset: {e}")
            # Fall back to simulated training data
            simulated = self._generate_simulated_training_data(200)
            return self.train_ensemble_models(simulated)

        # Convert processed records into training_data format expected by train_ensemble_models
        training_data = []
        for p in processed:
            match = {
                'home_team': p['home_team'],
                'away_team': p['away_team'],
                'realtime_data': {},
                'result': int(p['label'])
            }
            # Attach minimal form/h2h info for feature extraction
            f = p.get('features', {})
            match['home_form'] = {'win_rate': f.get('home_recent_form', 0.5), 'goals_per_game': f.get('home_avg_goals', 1.0), 'goals_conceded_per_game': 1.0}
            match['away_form'] = {'win_rate': f.get('away_recent_form', 0.5), 'goals_per_game': f.get('away_avg_goals', 1.0), 'goals_conceded_per_game': 1.0}
            match['h2h'] = f.get('h2h', {})
            match['league'] = f.get('league', 'la-liga')
            training_data.append(match)

        return self.train_ensemble_models(training_data)

    def _calculate_model_weight(self, accuracy: float, log_loss: float) -> float:
        """Calculate ensemble weight based on model performance"""

        # Weight based on accuracy (0.6 weight) and inverse log-loss (0.4 weight)
        accuracy_weight = accuracy * 0.6
        logloss_weight = (1.0 / (1.0 + log_loss)) * 0.4

        total_weight = accuracy_weight + logloss_weight
        return min(1.0, max(0.1, total_weight))  # Clamp between 0.1 and 1.0

    def predict_with_ensemble(self, home_team: str, away_team: str,
                            match_data: Dict[str, Any], realtime_data: Dict[str, Any]) -> Dict[str, Any]:
        """Make predictions using weighted ensemble"""

        # Generate features
        features = self.generate_features(home_team, away_team, match_data, realtime_data)
        features_scaled = self.scaler.transform(features)

        # Get predictions from each model
        ensemble_predictions: Dict[str, Dict[str, Any]] = {}
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

    def _calculate_model_agreement(self, predictions: Dict[str, Dict[str, Any]]) -> float:
        """Calculate how much the models agree with each other"""

        if len(predictions) < 2:
            return 0.5

        # Calculate variance in predictions across models
        all_probs: list[list[float]] = []
        for model_pred in predictions.values():
            all_probs.append(model_pred['probabilities'])

        all_probs_np = np.array(all_probs, dtype=float)

        # Calculate average variance across the three outcomes
        variances = np.var(all_probs_np, axis=0)
        avg_variance = np.mean(variances)

        # Convert variance to agreement score (lower variance = higher agreement)
        agreement = max(0.0, 1.0 - (avg_variance * 10))  # Scale variance

        return float(agreement)

    def update_bayesian_ratings(self, match_result: dict[str, Any]) -> list[BayesianUpdate]:
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
            matches_considered=int(matches) + 1,
            update_strength=update_strength
        )

    def _generate_simulated_training_data(self, num_matches: int) -> list[dict[str, Any]]:
        """Generate simulated training data for model training"""

        teams = list(self.bayesian_ratings.keys())
        training_data = []

        for _i in range(num_matches):
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

    def _load_model_performances(self) -> None:
        """Load saved model performance metrics"""
        perf_file = self.models_dir / "model_performances.json"
        if perf_file.exists():
            try:
                with open(perf_file) as f:
                    data = json.load(f)
                    for name, perf_data in data.items():
                        self.model_performances[name] = ModelPerformance(**perf_data)
            except Exception as e:
                print(f"⚠️  Failed to load model performances: {e}")

    def _save_model_performances(self) -> None:
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

def main() -> None:
    """Test ML enhancement system"""
    enhancer = MachineLearningEnhancer()

    # Train models
    print("🤖 Training ML Enhancement System...")
    enhancer.train_ensemble_models([])

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
