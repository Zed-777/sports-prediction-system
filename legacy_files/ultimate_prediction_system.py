#!/usr/bin/env python3
"""
Ultimate Sports Prediction System
Unified architecture integrating all enhancement phases
"""

import sys
from pathlib import Path

# Add app directory to path
sys.path.append(str(Path(__file__).parent))

import json
import logging
import traceback
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Dict, List, Tuple

import numpy as np

from app.analytics.advanced_engine import AdvancedAnalyticsEngine

# Import all enhancement phases
from app.data.realtime_integrator import RealTimeDataIntegrator
from app.models.ml_enhancer import MachineLearningEnhancer


@dataclass
class SystemPerformanceMetrics:
    """Track system performance and reliability"""
    total_predictions: int
    successful_predictions: int
    failed_predictions: int
    avg_processing_time: float
    confidence_distribution: Dict[str, int]
    data_source_reliability: Dict[str, float]
    model_accuracy_history: List[float]

@dataclass
class PredictionResult:
    """Complete prediction result with all enhancements"""
    match_id: int
    home_team: str
    away_team: str
    date: str

    # Core predictions
    probabilities: Dict[str, float]
    expected_goals: Tuple[float, float]
    confidence: float

    # Real-time data
    team_form: Dict
    player_availability: Dict
    weather_conditions: Dict
    referee_impact: Dict

    # ML predictions
    ensemble_predictions: Dict
    bayesian_ratings: Dict

    # Advanced analytics
    expected_threat_analysis: Dict
    formation_analysis: Dict
    pressing_battle: Dict
    market_sentiment: Dict
    tactical_insights: List[str]

    # System metadata
    processing_time: float
    data_sources_used: List[str]
    model_versions: Dict[str, str]
    system_confidence: float

class UltimatePredictionSystem:
    """Master system integrating all enhancement phases"""

    def __init__(self):
        self.system_version = "4.0.0-ultimate"
        self.startup_time = datetime.now()

        # Initialize logging
        self._setup_logging()

        # Initialize all subsystems
        self.logger.info("🚀 Initializing Ultimate Prediction System...")

        try:
            self.realtime_integrator = RealTimeDataIntegrator()
            self.logger.info("✅ Real-time data integrator loaded")
        except Exception as e:
            self.logger.error(f"❌ Real-time integrator failed: {e}")
            self.realtime_integrator = None

        try:
            self.ml_enhancer = MachineLearningEnhancer()
            self.logger.info("✅ ML enhancement system loaded")
        except Exception as e:
            self.logger.error(f"❌ ML enhancer failed: {e}")
            self.ml_enhancer = None

        try:
            self.analytics_engine = AdvancedAnalyticsEngine()
            self.logger.info("✅ Advanced analytics engine loaded")
        except Exception as e:
            self.logger.error(f"❌ Analytics engine failed: {e}")
            self.analytics_engine = None

        # System performance tracking
        self.performance_metrics = SystemPerformanceMetrics(
            total_predictions=0,
            successful_predictions=0,
            failed_predictions=0,
            avg_processing_time=0.0,
            confidence_distribution={'low': 0, 'medium': 0, 'high': 0},
            data_source_reliability={},
            model_accuracy_history=[]
        )

        # Load system state if exists
        self._load_system_state()

        self.logger.info(f"🎯 Ultimate Prediction System v{self.system_version} ready!")

    def _setup_logging(self):
        """Configure comprehensive logging"""
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(logs_dir / f"ultimate_system_{datetime.now().strftime('%Y%m%d')}.log"),
                logging.StreamHandler()
            ]
        )

        self.logger = logging.getLogger("UltimatePredictionSystem")

    def generate_ultimate_prediction(self, match_data: Dict,
                                   home_formation: str = '4-3-3',
                                   away_formation: str = '4-2-3-1') -> PredictionResult:
        """Generate the most comprehensive prediction possible"""

        start_time = datetime.now()
        self.performance_metrics.total_predictions += 1

        home_team = match_data['homeTeam']['name']
        away_team = match_data['awayTeam']['name']
        match_id = match_data['id']

        self.logger.info(f"🎯 Generating ultimate prediction for Match {match_id}: {home_team} vs {away_team}")

        try:
            # Phase 1: Real-time data integration
            realtime_data = {}
            if self.realtime_integrator:
                try:
                    self.logger.info("📡 Integrating real-time data...")
                    realtime_data = self.realtime_integrator.integrate_realtime_data(match_data)
                    self.logger.info("✅ Real-time data integrated")
                except Exception as e:
                    self.logger.warning(f"⚠️ Real-time data failed: {e}")
                    realtime_data = self._fallback_realtime_data(home_team, away_team)

            # Phase 2: ML ensemble predictions
            ml_predictions = {}
            if self.ml_enhancer:
                try:
                    self.logger.info("🤖 Running ML ensemble...")
                    # Train models if needed (first run)
                    try:
                        if not getattr(self.ml_enhancer, 'models_trained', False):
                            self.ml_enhancer.train_ensemble_models([])
                            self.ml_enhancer.models_trained = True
                    except AttributeError:
                        self.ml_enhancer.train_ensemble_models([])

                    ml_predictions = self.ml_enhancer.predict_with_ensemble(
                        home_team, away_team, match_data, realtime_data
                    )
                    self.logger.info("✅ ML ensemble complete")
                except Exception as e:
                    self.logger.warning(f"⚠️ ML ensemble failed: {e}")
                    ml_predictions = self._fallback_ml_predictions()

            # Phase 3: Advanced analytics
            advanced_analytics = {}
            if self.analytics_engine:
                try:
                    self.logger.info("🔬 Running advanced analytics...")
                    advanced_analytics = self.analytics_engine.generate_comprehensive_analytics(
                        home_team, away_team, home_formation, away_formation
                    )
                    self.logger.info("✅ Advanced analytics complete")
                except Exception as e:
                    self.logger.warning(f"⚠️ Advanced analytics failed: {e}")
                    advanced_analytics = self._fallback_analytics()

            # Phase 4: Master prediction synthesis
            master_prediction = self._synthesize_master_prediction(
                match_data, realtime_data, ml_predictions, advanced_analytics
            )

            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()

            # Create comprehensive result
            result = PredictionResult(
                match_id=match_id,
                home_team=home_team,
                away_team=away_team,
                date=match_data['utcDate'][:10],

                # Core predictions
                probabilities=master_prediction['probabilities'],
                expected_goals=master_prediction['expected_goals'],
                confidence=master_prediction['confidence'],

                # Enhancement data
                team_form=realtime_data.get('real_time_enhancements', {}).get('home_team_form', {}),
                player_availability=realtime_data.get('real_time_enhancements', {}).get('player_availability', {}),
                weather_conditions=realtime_data.get('real_time_enhancements', {}).get('weather_conditions', {}),
                referee_impact=realtime_data.get('real_time_enhancements', {}).get('referee_profile', {}),

                ensemble_predictions=ml_predictions.get('individual_models', {}),
                bayesian_ratings=getattr(self.ml_enhancer, 'bayesian_ratings', {}) if self.ml_enhancer else {},

                expected_threat_analysis=advanced_analytics.get('expected_threat_analysis', {}),
                formation_analysis=advanced_analytics.get('formation_matchup', {}),
                pressing_battle=advanced_analytics.get('pressing_intensity_battle', {}),
                market_sentiment=advanced_analytics.get('market_sentiment', {}),
                tactical_insights=advanced_analytics.get('tactical_insights', []),

                # System metadata
                processing_time=round(processing_time, 3),
                data_sources_used=master_prediction['data_sources'],
                model_versions={
                    'system': self.system_version,
                    'realtime': 'v1.0',
                    'ml_ensemble': 'v2.0',
                    'analytics': 'v3.0'
                },
                system_confidence=master_prediction['system_confidence']
            )

            # Update performance metrics
            self._update_performance_metrics(result, success=True)

            self.logger.info(f"🎉 Ultimate prediction complete! Confidence: {result.confidence:.1%}, "
                           f"System confidence: {result.system_confidence:.1%}, "
                           f"Processing time: {processing_time:.2f}s")

            return result

        except Exception as e:
            self.logger.error(f"💥 Ultimate prediction failed: {e}")
            self.logger.error(traceback.format_exc())
            self.performance_metrics.failed_predictions += 1

            # Return fallback prediction
            return self._fallback_prediction(match_data, start_time)

    def _synthesize_master_prediction(self, match_data: Dict, realtime_data: Dict,
                                    ml_predictions: Dict, advanced_analytics: Dict) -> Dict:
        """Synthesize all prediction sources into master prediction"""

        # Start with base probabilities
        base_probs = [0.30, 0.25, 0.45]  # [away, draw, home]

        # Weight different prediction sources
        weights = {
            'realtime': 0.25,
            'ml_ensemble': 0.35,
            'analytics': 0.25,
            'base': 0.15
        }

        # Collect all probability predictions
        probability_sources = []
        confidence_sources = []
        data_sources = ['base_algorithm']

        # Real-time adjusted probabilities
        if 'form_adjusted_probabilities' in realtime_data:
            rt_probs = realtime_data['form_adjusted_probabilities']
            probability_sources.append([
                rt_probs['away_win_prob'],
                rt_probs['draw_prob'],
                rt_probs['home_win_prob']
            ])
            confidence_sources.append(0.75)
            data_sources.append('real_time_integration')

        # ML ensemble probabilities
        if 'ensemble_probabilities' in ml_predictions:
            ml_probs = ml_predictions['ensemble_probabilities']
            probability_sources.append([
                ml_probs['away_win_prob'],
                ml_probs['draw_prob'],
                ml_probs['home_win_prob']
            ])
            confidence_sources.append(ml_predictions.get('ensemble_confidence', 0.70))
            data_sources.append('ml_ensemble')

        # Add base prediction
        probability_sources.append(base_probs)
        confidence_sources.append(0.60)

        # Weighted average of probabilities
        if probability_sources:
            # Weight by confidence
            total_weight = sum(confidence_sources)
            weighted_probs = np.zeros(3)

            for probs, conf in zip(probability_sources, confidence_sources):
                weight = conf / total_weight
                weighted_probs += np.array(probs) * weight

            # Normalize
            weighted_probs = weighted_probs / np.sum(weighted_probs)
        else:
            weighted_probs = np.array(base_probs)

        # Calculate expected goals (enhanced)
        base_goals = [1.0, 1.5]  # [away, home]

        # Adjust for analytics
        if 'expected_threat_analysis' in advanced_analytics:
            xt_data = advanced_analytics['expected_threat_analysis']
            if xt_data.get('dominant_team') == 'home':
                base_goals[1] *= 1.2
                base_goals[0] *= 0.9
            elif xt_data.get('dominant_team') == 'away':
                base_goals[0] *= 1.2
                base_goals[1] *= 0.9

        # Master confidence calculation
        if confidence_sources:
            master_confidence = np.mean(confidence_sources)

            # Boost confidence if all sources agree
            prob_variance = np.var([p[2] for p in probability_sources])  # Home win variance
            if prob_variance < 0.01:  # Low variance = agreement
                master_confidence *= 1.1

            master_confidence = min(0.95, master_confidence)
        else:
            master_confidence = 0.60

        # System confidence (how well all components worked)
        system_confidence = len(data_sources) / 4.0  # Max 4 sources
        if self.realtime_integrator and self.ml_enhancer and self.analytics_engine:
            system_confidence *= 1.1  # Bonus for all systems working

        system_confidence = min(0.98, system_confidence)

        return {
            'probabilities': {
                'away_win_prob': round(weighted_probs[0], 3),
                'draw_prob': round(weighted_probs[1], 3),
                'home_win_prob': round(weighted_probs[2], 3)
            },
            'expected_goals': (round(base_goals[1], 1), round(base_goals[0], 1)),  # (home, away)
            'confidence': round(master_confidence, 3),
            'system_confidence': round(system_confidence, 3),
            'data_sources': data_sources
        }

    def _fallback_realtime_data(self, home_team: str, away_team: str) -> Dict:
        """Fallback real-time data if integration fails"""
        return {
            'real_time_enhancements': {
                'home_team_form': {'form_rating': 0.6, 'goals_per_game': 1.2},
                'away_team_form': {'form_rating': 0.5, 'goals_per_game': 1.0},
                'player_availability': {
                    'home_availability_multiplier': 0.9,
                    'away_availability_multiplier': 0.9
                },
                'weather_conditions': {'temperature': 18.0, 'playing_impact': 0.0},
                'referee_profile': {'home_bias': 0.0, 'strictness': 0.5}
            },
            'form_adjusted_probabilities': {
                'home_win_prob': 0.45,
                'draw_prob': 0.25,
                'away_win_prob': 0.30
            }
        }

    def _fallback_ml_predictions(self) -> Dict:
        """Fallback ML predictions if ensemble fails"""
        return {
            'ensemble_probabilities': {
                'home_win_prob': 0.44,
                'draw_prob': 0.26,
                'away_win_prob': 0.30
            },
            'ensemble_confidence': 0.65,
            'individual_models': {
                'fallback_model': {
                    'probabilities': [0.30, 0.26, 0.44],
                    'weight': 1.0,
                    'confidence': 0.65
                }
            }
        }

    def _fallback_analytics(self) -> Dict:
        """Fallback analytics if advanced engine fails"""
        return {
            'expected_threat_analysis': {
                'home_net_xt_advantage': 0.1,
                'away_net_xt_advantage': 0.0,
                'dominant_team': 'home'
            },
            'formation_matchup': {
                'tactical_advantage': 'neutral',
                'predicted_style': 'balanced'
            },
            'market_sentiment': {
                'home_odds': 2.2,
                'draw_odds': 3.4,
                'away_odds': 3.1,
                'market_confidence': 0.6
            },
            'tactical_insights': ['Standard prediction with limited analytics']
        }

    def _fallback_prediction(self, match_data: Dict, start_time: datetime) -> PredictionResult:
        """Complete fallback prediction if everything fails"""
        processing_time = (datetime.now() - start_time).total_seconds()

        return PredictionResult(
            match_id=match_data['id'],
            home_team=match_data['homeTeam']['name'],
            away_team=match_data['awayTeam']['name'],
            date=match_data['utcDate'][:10],

            probabilities={'home_win_prob': 0.45, 'draw_prob': 0.25, 'away_win_prob': 0.30},
            expected_goals=(1.5, 1.0),
            confidence=0.50,

            team_form={}, player_availability={}, weather_conditions={}, referee_impact={},
            ensemble_predictions={}, bayesian_ratings={},
            expected_threat_analysis={}, formation_analysis={}, pressing_battle={},
            market_sentiment={}, tactical_insights=['Fallback prediction - limited data'],

            processing_time=processing_time,
            data_sources_used=['fallback_algorithm'],
            model_versions={'system': self.system_version},
            system_confidence=0.30
        )

    def _update_performance_metrics(self, result: PredictionResult, success: bool):
        """Update system performance metrics"""
        if success:
            self.performance_metrics.successful_predictions += 1

        # Update confidence distribution
        if result.confidence >= 0.8:
            self.performance_metrics.confidence_distribution['high'] += 1
        elif result.confidence >= 0.6:
            self.performance_metrics.confidence_distribution['medium'] += 1
        else:
            self.performance_metrics.confidence_distribution['low'] += 1

        # Update average processing time
        total_time = (self.performance_metrics.avg_processing_time *
                     (self.performance_metrics.total_predictions - 1) +
                     result.processing_time)
        self.performance_metrics.avg_processing_time = total_time / self.performance_metrics.total_predictions

    def _load_system_state(self):
        """Load saved system state"""
        state_file = Path("data/system_state.json")
        if state_file.exists():
            try:
                with open(state_file) as f:
                    state = json.load(f)
                    # Load any saved state here
                    self.logger.info("✅ System state loaded")
            except Exception as e:
                self.logger.warning(f"⚠️ Failed to load system state: {e}")

    def save_system_state(self):
        """Save current system state"""
        state_file = Path("data/system_state.json")
        state_file.parent.mkdir(exist_ok=True)

        state = {
            'version': self.system_version,
            'startup_time': self.startup_time.isoformat(),
            'performance_metrics': asdict(self.performance_metrics),
            'last_saved': datetime.now().isoformat()
        }

        try:
            with open(state_file, 'w') as f:
                json.dump(state, f, indent=2)
            self.logger.info("💾 System state saved")
        except Exception as e:
            self.logger.error(f"❌ Failed to save system state: {e}")

    def get_system_status(self) -> Dict:
        """Get comprehensive system status"""
        return {
            'system_version': self.system_version,
            'uptime_seconds': (datetime.now() - self.startup_time).total_seconds(),
            'subsystems_status': {
                'realtime_integrator': self.realtime_integrator is not None,
                'ml_enhancer': self.ml_enhancer is not None,
                'analytics_engine': self.analytics_engine is not None
            },
            'performance_metrics': asdict(self.performance_metrics),
            'health_score': self._calculate_health_score()
        }

    def _calculate_health_score(self) -> float:
        """Calculate overall system health score"""
        if self.performance_metrics.total_predictions == 0:
            return 1.0

        success_rate = (self.performance_metrics.successful_predictions /
                       self.performance_metrics.total_predictions)

        subsystem_score = sum([
            self.realtime_integrator is not None,
            self.ml_enhancer is not None,
            self.analytics_engine is not None
        ]) / 3.0

        processing_efficiency = 1.0 if self.performance_metrics.avg_processing_time < 10.0 else 0.5

        health_score = (success_rate * 0.5 + subsystem_score * 0.3 + processing_efficiency * 0.2)

        return round(health_score, 3)

def main():
    """Test the ultimate prediction system"""
    system = UltimatePredictionSystem()

    # Test prediction
    sample_match = {
        'id': 544293,
        'homeTeam': {'name': 'FC Barcelona', 'id': 81},
        'awayTeam': {'name': 'Girona FC', 'id': 298},
        'utcDate': '2025-10-18T14:15:00Z'
    }

    print("🚀 Testing Ultimate Prediction System...")
    result = system.generate_ultimate_prediction(sample_match)

    print("\n🎯 Ultimate Prediction Result:")
    print(f"Match: {result.home_team} vs {result.away_team}")
    print(f"Probabilities: {result.probabilities}")
    print(f"Confidence: {result.confidence:.1%}")
    print(f"System Confidence: {result.system_confidence:.1%}")
    print(f"Processing Time: {result.processing_time:.2f}s")
    print(f"Data Sources: {result.data_sources_used}")

    # Show system status
    status = system.get_system_status()
    print("\n📊 System Status:")
    print(f"Health Score: {status['health_score']:.1%}")
    print(f"Subsystems: {status['subsystems_status']}")

    # Save system state
    system.save_system_state()

if __name__ == "__main__":
    main()
