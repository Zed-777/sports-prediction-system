"""
A/B Testing Infrastructure (VB-002)
====================================

Infrastructure for comparing model versions and running experiments.
Essential for preventing regressions and validating improvements.

Key Features:
- Run parallel predictions with different model configurations
- Statistical comparison of accuracy metrics
- Automatic winner detection
- Experiment tracking and logging
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Callable
from datetime import datetime
import json
import os
import logging
import hashlib
from enum import Enum
import math

logger = logging.getLogger(__name__)


class ExperimentStatus(Enum):
    """Status of an A/B experiment."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    INCONCLUSIVE = "inconclusive"
    STOPPED = "stopped"


@dataclass
class ModelVariant:
    """Configuration for a model variant in an experiment."""
    name: str
    description: str
    config: Dict[str, Any]
    is_control: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'description': self.description,
            'config': self.config,
            'is_control': self.is_control
        }


@dataclass
class PredictionResult:
    """Single prediction result for a variant."""
    match_id: str
    variant_name: str
    predicted_home_prob: float
    predicted_draw_prob: float
    predicted_away_prob: float
    predicted_outcome: str  # '1', 'X', '2'
    confidence: float
    actual_outcome: Optional[str] = None
    is_correct: Optional[bool] = None
    brier_score: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'match_id': self.match_id,
            'variant_name': self.variant_name,
            'predicted_home_prob': self.predicted_home_prob,
            'predicted_draw_prob': self.predicted_draw_prob,
            'predicted_away_prob': self.predicted_away_prob,
            'predicted_outcome': self.predicted_outcome,
            'confidence': self.confidence,
            'actual_outcome': self.actual_outcome,
            'is_correct': self.is_correct,
            'brier_score': self.brier_score,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class VariantMetrics:
    """Performance metrics for a model variant."""
    variant_name: str
    predictions_count: int = 0
    correct_predictions: int = 0
    accuracy: float = 0.0
    avg_brier_score: float = 0.0
    avg_confidence: float = 0.0
    high_confidence_accuracy: float = 0.0  # Accuracy on >65% confidence predictions
    calibration_error: float = 0.0  # Difference between confidence and accuracy
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'variant_name': self.variant_name,
            'predictions_count': self.predictions_count,
            'correct_predictions': self.correct_predictions,
            'accuracy': self.accuracy,
            'avg_brier_score': self.avg_brier_score,
            'avg_confidence': self.avg_confidence,
            'high_confidence_accuracy': self.high_confidence_accuracy,
            'calibration_error': self.calibration_error
        }


@dataclass
class ExperimentResult:
    """Result of an A/B experiment."""
    experiment_id: str
    status: ExperimentStatus
    control_metrics: VariantMetrics
    treatment_metrics: VariantMetrics
    winner: Optional[str] = None  # 'control', 'treatment', None
    improvement_pct: float = 0.0
    statistical_significance: float = 0.0
    sample_size: int = 0
    min_sample_size: int = 30
    conclusion: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'experiment_id': self.experiment_id,
            'status': self.status.value,
            'control_metrics': self.control_metrics.to_dict(),
            'treatment_metrics': self.treatment_metrics.to_dict(),
            'winner': self.winner,
            'improvement_pct': self.improvement_pct,
            'statistical_significance': self.statistical_significance,
            'sample_size': self.sample_size,
            'min_sample_size': self.min_sample_size,
            'conclusion': self.conclusion
        }


@dataclass
class Experiment:
    """An A/B experiment definition."""
    id: str
    name: str
    description: str
    control: ModelVariant
    treatment: ModelVariant
    status: ExperimentStatus = ExperimentStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    min_sample_size: int = 30
    max_sample_size: int = 500
    significance_threshold: float = 0.95
    predictions: List[PredictionResult] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'control': self.control.to_dict(),
            'treatment': self.treatment.to_dict(),
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'min_sample_size': self.min_sample_size,
            'max_sample_size': self.max_sample_size,
            'significance_threshold': self.significance_threshold,
            'predictions_count': len(self.predictions)
        }


class ABTestingFramework:
    """
    A/B testing infrastructure for model comparison.
    
    VB-002: A/B Testing Infrastructure
    - Run parallel predictions with different configurations
    - Track accuracy metrics for each variant
    - Statistical significance testing
    - Automatic winner detection
    """
    
    def __init__(self, storage_dir: str = "data/experiments"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
        self.experiments: Dict[str, Experiment] = {}
        self._load_experiments()
    
    def _load_experiments(self):
        """Load saved experiments from storage."""
        try:
            experiments_file = os.path.join(self.storage_dir, "experiments.json")
            if os.path.exists(experiments_file):
                with open(experiments_file, 'r') as f:
                    data = json.load(f)
                for exp_id, exp_data in data.items():
                    self.experiments[exp_id] = self._experiment_from_dict(exp_data)
        except Exception as e:
            logger.debug(f"Failed to load experiments: {e}")
    
    def _save_experiments(self):
        """Save experiments to storage."""
        try:
            experiments_file = os.path.join(self.storage_dir, "experiments.json")
            data = {exp_id: exp.to_dict() for exp_id, exp in self.experiments.items()}
            with open(experiments_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.debug(f"Failed to save experiments: {e}")
    
    def _experiment_from_dict(self, data: Dict) -> Experiment:
        """Reconstruct experiment from dict."""
        return Experiment(
            id=data['id'],
            name=data['name'],
            description=data['description'],
            control=ModelVariant(
                name=data['control']['name'],
                description=data['control']['description'],
                config=data['control']['config'],
                is_control=True
            ),
            treatment=ModelVariant(
                name=data['treatment']['name'],
                description=data['treatment']['description'],
                config=data['treatment']['config']
            ),
            status=ExperimentStatus(data['status']),
            created_at=datetime.fromisoformat(data['created_at']),
            started_at=datetime.fromisoformat(data['started_at']) if data.get('started_at') else None,
            completed_at=datetime.fromisoformat(data['completed_at']) if data.get('completed_at') else None,
            min_sample_size=data.get('min_sample_size', 30),
            max_sample_size=data.get('max_sample_size', 500),
            significance_threshold=data.get('significance_threshold', 0.95)
        )
    
    def _generate_experiment_id(self, name: str) -> str:
        """Generate unique experiment ID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name_hash = hashlib.md5(name.encode()).hexdigest()[:6]
        return f"exp_{timestamp}_{name_hash}"
    
    def create_experiment(
        self,
        name: str,
        description: str,
        control_config: Dict[str, Any],
        treatment_config: Dict[str, Any],
        control_name: str = "control",
        treatment_name: str = "treatment",
        min_sample_size: int = 30,
        max_sample_size: int = 500
    ) -> Experiment:
        """
        Create a new A/B experiment.
        
        Args:
            name: Experiment name
            description: Description of what's being tested
            control_config: Configuration for control variant (existing model)
            treatment_config: Configuration for treatment variant (new model)
            control_name: Name for control variant
            treatment_name: Name for treatment variant
            min_sample_size: Minimum predictions before evaluation
            max_sample_size: Maximum predictions before forcing conclusion
            
        Returns:
            Created Experiment object
        """
        exp_id = self._generate_experiment_id(name)
        
        experiment = Experiment(
            id=exp_id,
            name=name,
            description=description,
            control=ModelVariant(
                name=control_name,
                description="Control (existing model)",
                config=control_config,
                is_control=True
            ),
            treatment=ModelVariant(
                name=treatment_name,
                description="Treatment (new model)",
                config=treatment_config
            ),
            min_sample_size=min_sample_size,
            max_sample_size=max_sample_size
        )
        
        self.experiments[exp_id] = experiment
        self._save_experiments()
        
        logger.info(f"Created experiment: {exp_id} - {name}")
        return experiment
    
    def start_experiment(self, experiment_id: str) -> Experiment:
        """Start an experiment (set to running status)."""
        if experiment_id not in self.experiments:
            raise ValueError(f"Experiment {experiment_id} not found")
        
        exp = self.experiments[experiment_id]
        exp.status = ExperimentStatus.RUNNING
        exp.started_at = datetime.now()
        self._save_experiments()
        
        logger.info(f"Started experiment: {experiment_id}")
        return exp
    
    def record_prediction(
        self,
        experiment_id: str,
        variant_name: str,
        match_id: str,
        home_prob: float,
        draw_prob: float,
        away_prob: float,
        confidence: float
    ) -> PredictionResult:
        """
        Record a prediction for an experiment variant.
        
        Args:
            experiment_id: Experiment to record for
            variant_name: 'control' or 'treatment'
            match_id: Unique match identifier
            home_prob: Predicted home win probability
            draw_prob: Predicted draw probability
            away_prob: Predicted away win probability
            confidence: Prediction confidence
            
        Returns:
            Created PredictionResult
        """
        if experiment_id not in self.experiments:
            raise ValueError(f"Experiment {experiment_id} not found")
        
        # Determine predicted outcome
        if home_prob >= draw_prob and home_prob >= away_prob:
            predicted = '1'
        elif away_prob >= home_prob and away_prob >= draw_prob:
            predicted = '2'
        else:
            predicted = 'X'
        
        result = PredictionResult(
            match_id=match_id,
            variant_name=variant_name,
            predicted_home_prob=home_prob,
            predicted_draw_prob=draw_prob,
            predicted_away_prob=away_prob,
            predicted_outcome=predicted,
            confidence=confidence
        )
        
        self.experiments[experiment_id].predictions.append(result)
        self._save_experiments()
        
        return result
    
    def record_actual_result(
        self,
        experiment_id: str,
        match_id: str,
        actual_outcome: str,  # '1', 'X', '2'
        home_goals: int = 0,
        away_goals: int = 0
    ):
        """
        Record actual match result and update predictions.
        
        Args:
            experiment_id: Experiment to update
            match_id: Match to update
            actual_outcome: '1' for home, 'X' for draw, '2' for away
            home_goals: Home team goals (for Brier score)
            away_goals: Away team goals (for Brier score)
        """
        if experiment_id not in self.experiments:
            return
        
        exp = self.experiments[experiment_id]
        
        for pred in exp.predictions:
            if pred.match_id == match_id:
                pred.actual_outcome = actual_outcome
                pred.is_correct = pred.predicted_outcome == actual_outcome
                
                # Calculate Brier score
                actual_probs = {'1': 0.0, 'X': 0.0, '2': 0.0}
                actual_probs[actual_outcome] = 1.0
                
                pred.brier_score = (
                    (pred.predicted_home_prob - actual_probs['1']) ** 2 +
                    (pred.predicted_draw_prob - actual_probs['X']) ** 2 +
                    (pred.predicted_away_prob - actual_probs['2']) ** 2
                ) / 3
        
        self._save_experiments()
        
        # Check if experiment should be evaluated
        self._check_experiment_completion(experiment_id)
    
    def _calculate_variant_metrics(
        self,
        predictions: List[PredictionResult],
        variant_name: str
    ) -> VariantMetrics:
        """Calculate metrics for a variant."""
        variant_preds = [p for p in predictions if p.variant_name == variant_name and p.actual_outcome is not None]
        
        if not variant_preds:
            return VariantMetrics(variant_name=variant_name)
        
        total = len(variant_preds)
        correct = sum(1 for p in variant_preds if p.is_correct)
        accuracy = correct / total if total > 0 else 0
        
        # Brier scores
        brier_scores = [p.brier_score for p in variant_preds if p.brier_score is not None]
        avg_brier = sum(brier_scores) / len(brier_scores) if brier_scores else 0
        
        # Confidence
        confidences = [p.confidence for p in variant_preds]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        # High confidence accuracy (>65%)
        high_conf_preds = [p for p in variant_preds if p.confidence > 0.65]
        high_conf_correct = sum(1 for p in high_conf_preds if p.is_correct)
        high_conf_accuracy = high_conf_correct / len(high_conf_preds) if high_conf_preds else 0
        
        # Calibration error
        calibration_error = abs(avg_confidence - accuracy)
        
        return VariantMetrics(
            variant_name=variant_name,
            predictions_count=total,
            correct_predictions=correct,
            accuracy=round(accuracy, 4),
            avg_brier_score=round(avg_brier, 4),
            avg_confidence=round(avg_confidence, 4),
            high_confidence_accuracy=round(high_conf_accuracy, 4),
            calibration_error=round(calibration_error, 4)
        )
    
    def _calculate_significance(
        self,
        control_correct: int,
        control_total: int,
        treatment_correct: int,
        treatment_total: int
    ) -> float:
        """
        Calculate statistical significance using two-proportion z-test.
        
        Returns:
            Confidence level (0-1) that treatment is different from control
        """
        if control_total == 0 or treatment_total == 0:
            return 0.0
        
        p1 = control_correct / control_total
        p2 = treatment_correct / treatment_total
        
        # Pooled proportion
        p_pool = (control_correct + treatment_correct) / (control_total + treatment_total)
        
        if p_pool == 0 or p_pool == 1:
            return 0.0
        
        # Standard error
        se = math.sqrt(p_pool * (1 - p_pool) * (1/control_total + 1/treatment_total))
        
        if se == 0:
            return 0.0
        
        # Z-score
        z = abs(p2 - p1) / se
        
        # Approximate p-value to confidence (simplified)
        # Using standard normal approximation
        if z > 2.576:
            return 0.99
        elif z > 1.96:
            return 0.95
        elif z > 1.645:
            return 0.90
        elif z > 1.28:
            return 0.80
        else:
            return 0.5 + (z / 5)  # Rough approximation
    
    def _check_experiment_completion(self, experiment_id: str):
        """Check if experiment should be completed and evaluate."""
        exp = self.experiments[experiment_id]
        
        if exp.status != ExperimentStatus.RUNNING:
            return
        
        # Count predictions with results
        completed_preds = [p for p in exp.predictions if p.actual_outcome is not None]
        control_preds = [p for p in completed_preds if p.variant_name == exp.control.name]
        treatment_preds = [p for p in completed_preds if p.variant_name == exp.treatment.name]
        
        sample_size = min(len(control_preds), len(treatment_preds))
        
        # Check if we have enough data
        if sample_size >= exp.min_sample_size:
            result = self.evaluate_experiment(experiment_id)
            
            # Auto-complete if significant or max reached
            if result.statistical_significance >= exp.significance_threshold:
                exp.status = ExperimentStatus.COMPLETED
                exp.completed_at = datetime.now()
                self._save_experiments()
            elif sample_size >= exp.max_sample_size:
                exp.status = ExperimentStatus.INCONCLUSIVE
                exp.completed_at = datetime.now()
                self._save_experiments()
    
    def evaluate_experiment(self, experiment_id: str) -> ExperimentResult:
        """
        Evaluate current experiment results.
        
        Args:
            experiment_id: Experiment to evaluate
            
        Returns:
            ExperimentResult with metrics and conclusion
        """
        if experiment_id not in self.experiments:
            raise ValueError(f"Experiment {experiment_id} not found")
        
        exp = self.experiments[experiment_id]
        
        # Calculate metrics for each variant
        control_metrics = self._calculate_variant_metrics(exp.predictions, exp.control.name)
        treatment_metrics = self._calculate_variant_metrics(exp.predictions, exp.treatment.name)
        
        sample_size = min(control_metrics.predictions_count, treatment_metrics.predictions_count)
        
        # Calculate significance
        significance = self._calculate_significance(
            control_metrics.correct_predictions,
            control_metrics.predictions_count,
            treatment_metrics.correct_predictions,
            treatment_metrics.predictions_count
        )
        
        # Determine winner
        winner = None
        improvement = 0.0
        
        if control_metrics.accuracy > 0:
            improvement = (treatment_metrics.accuracy - control_metrics.accuracy) / control_metrics.accuracy * 100
        
        if significance >= exp.significance_threshold:
            if treatment_metrics.accuracy > control_metrics.accuracy:
                winner = "treatment"
            elif control_metrics.accuracy > treatment_metrics.accuracy:
                winner = "control"
        
        # Generate conclusion
        if sample_size < exp.min_sample_size:
            conclusion = f"Insufficient data: {sample_size}/{exp.min_sample_size} predictions needed"
        elif winner == "treatment":
            conclusion = f"Treatment wins! +{improvement:.1f}% accuracy improvement with {significance:.0%} confidence"
        elif winner == "control":
            conclusion = f"Control wins! Treatment shows {improvement:.1f}% accuracy change with {significance:.0%} confidence"
        else:
            conclusion = f"Inconclusive: {significance:.0%} confidence, {improvement:+.1f}% difference"
        
        return ExperimentResult(
            experiment_id=experiment_id,
            status=exp.status,
            control_metrics=control_metrics,
            treatment_metrics=treatment_metrics,
            winner=winner,
            improvement_pct=round(improvement, 2),
            statistical_significance=round(significance, 3),
            sample_size=sample_size,
            min_sample_size=exp.min_sample_size,
            conclusion=conclusion
        )
    
    def get_experiment(self, experiment_id: str) -> Optional[Experiment]:
        """Get experiment by ID."""
        return self.experiments.get(experiment_id)
    
    def list_experiments(
        self,
        status: Optional[ExperimentStatus] = None
    ) -> List[Experiment]:
        """List all experiments, optionally filtered by status."""
        if status:
            return [e for e in self.experiments.values() if e.status == status]
        return list(self.experiments.values())
    
    def stop_experiment(self, experiment_id: str) -> Experiment:
        """Stop an experiment early."""
        if experiment_id not in self.experiments:
            raise ValueError(f"Experiment {experiment_id} not found")
        
        exp = self.experiments[experiment_id]
        exp.status = ExperimentStatus.STOPPED
        exp.completed_at = datetime.now()
        self._save_experiments()
        
        return exp


class ExperimentRunner:
    """Helper class to run predictions through an experiment."""
    
    def __init__(self, framework: ABTestingFramework):
        self.framework = framework
    
    def run_parallel_prediction(
        self,
        experiment_id: str,
        match_id: str,
        control_predictor: Callable,
        treatment_predictor: Callable,
        match_data: Dict[str, Any]
    ) -> Tuple[PredictionResult, PredictionResult]:
        """
        Run prediction through both control and treatment models.
        
        Args:
            experiment_id: Active experiment ID
            match_id: Unique match identifier
            control_predictor: Function that returns (home_prob, draw_prob, away_prob, confidence)
            treatment_predictor: Function that returns (home_prob, draw_prob, away_prob, confidence)
            match_data: Match data to pass to predictors
            
        Returns:
            Tuple of (control_result, treatment_result)
        """
        exp = self.framework.get_experiment(experiment_id)
        if not exp:
            raise ValueError(f"Experiment {experiment_id} not found")
        
        # Run control prediction
        c_home, c_draw, c_away, c_conf = control_predictor(match_data)
        control_result = self.framework.record_prediction(
            experiment_id=experiment_id,
            variant_name=exp.control.name,
            match_id=match_id,
            home_prob=c_home,
            draw_prob=c_draw,
            away_prob=c_away,
            confidence=c_conf
        )
        
        # Run treatment prediction
        t_home, t_draw, t_away, t_conf = treatment_predictor(match_data)
        treatment_result = self.framework.record_prediction(
            experiment_id=experiment_id,
            variant_name=exp.treatment.name,
            match_id=match_id,
            home_prob=t_home,
            draw_prob=t_draw,
            away_prob=t_away,
            confidence=t_conf
        )
        
        return control_result, treatment_result


# Test when run directly
if __name__ == '__main__':
    print("=== A/B Testing Framework Test ===\n")
    
    framework = ABTestingFramework(storage_dir="data/experiments_test")
    
    # Create experiment
    exp = framework.create_experiment(
        name="Phase 3 Model Test",
        description="Testing Phase 3 enhancements vs baseline",
        control_config={'use_phase3': False},
        treatment_config={'use_phase3': True}
    )
    print(f"Created experiment: {exp.id}")
    
    # Start experiment
    framework.start_experiment(exp.id)
    print(f"Started experiment")
    
    # Simulate some predictions
    import random
    random.seed(42)
    
    for i in range(40):
        match_id = f"match_{i+1}"
        
        # Control predictions (baseline)
        c_home = random.uniform(0.3, 0.5)
        c_draw = random.uniform(0.2, 0.35)
        c_away = 1 - c_home - c_draw
        c_conf = random.uniform(0.55, 0.70)
        
        framework.record_prediction(
            exp.id, "control", match_id,
            c_home, c_draw, c_away, c_conf
        )
        
        # Treatment predictions (slightly better)
        t_home = c_home + random.uniform(-0.02, 0.05)
        t_draw = c_draw + random.uniform(-0.02, 0.03)
        t_away = 1 - t_home - t_draw
        t_conf = c_conf + random.uniform(0, 0.05)
        
        framework.record_prediction(
            exp.id, "treatment", match_id,
            t_home, t_draw, t_away, t_conf
        )
        
        # Simulate actual results
        outcomes = ['1', 'X', '2']
        actual = random.choices(outcomes, weights=[0.45, 0.28, 0.27])[0]
        
        framework.record_actual_result(exp.id, match_id, actual)
    
    # Evaluate
    result = framework.evaluate_experiment(exp.id)
    
    print(f"\n=== Experiment Results ===")
    print(f"Sample Size: {result.sample_size}")
    print(f"Control Accuracy: {result.control_metrics.accuracy:.1%}")
    print(f"Treatment Accuracy: {result.treatment_metrics.accuracy:.1%}")
    print(f"Improvement: {result.improvement_pct:+.1f}%")
    print(f"Significance: {result.statistical_significance:.0%}")
    print(f"Winner: {result.winner or 'None yet'}")
    print(f"\nConclusion: {result.conclusion}")
    
    # Cleanup test files
    import shutil
    shutil.rmtree("data/experiments_test", ignore_errors=True)
    
    print("\n✅ A/B Testing Framework working!")
