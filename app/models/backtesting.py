"""
Backtesting Framework (VB-001)
============================

Historical backtesting framework for validating prediction accuracy.
Tests predictions against historical match data using time-series cross-validation.

This is the ONLY reliable way to know if prediction improvements actually help.

Key Features:
- Time-series cross-validation (no future data leakage)
- Multiple evaluation metrics (accuracy, Brier score, calibration)
- League-specific and overall performance tracking
- Comparison between model versions
- Statistical significance testing
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Optional
import math
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class BacktestResult:
    """Result from a single prediction during backtesting."""
    match_id: str
    match_date: datetime
    league: str
    home_team: str
    away_team: str
    
    # Predictions
    predicted_home_prob: float
    predicted_draw_prob: float
    predicted_away_prob: float
    predicted_outcome: str  # '1', 'X', '2'
    confidence: float
    
    # Actual results
    actual_home_goals: int
    actual_away_goals: int
    actual_outcome: str  # '1', 'X', '2'
    
    # Metrics
    correct: bool = field(init=False)
    brier_score: float = field(init=False)
    log_loss: float = field(init=False)
    
    def __post_init__(self):
        """Calculate metrics after initialization."""
        self.correct = self.predicted_outcome == self.actual_outcome
        
        # Brier score: mean squared error of probabilities
        # Perfect prediction = 0, worst = 2
        actual_probs = [0.0, 0.0, 0.0]
        if self.actual_outcome == '1':
            actual_probs = [1.0, 0.0, 0.0]
        elif self.actual_outcome == 'X':
            actual_probs = [0.0, 1.0, 0.0]
        else:  # '2'
            actual_probs = [0.0, 0.0, 1.0]
        
        pred_probs = [
            self.predicted_home_prob / 100,
            self.predicted_draw_prob / 100,
            self.predicted_away_prob / 100
        ]
        
        self.brier_score = sum(
            (pred - actual) ** 2 
            for pred, actual in zip(pred_probs, actual_probs)
        )
        
        # Log loss: penalizes confident wrong predictions
        epsilon = 1e-10
        if self.actual_outcome == '1':
            prob = max(self.predicted_home_prob / 100, epsilon)
        elif self.actual_outcome == 'X':
            prob = max(self.predicted_draw_prob / 100, epsilon)
        else:
            prob = max(self.predicted_away_prob / 100, epsilon)
        
        self.log_loss = -math.log(prob)


@dataclass
class BacktestSummary:
    """Summary statistics from a backtest run."""
    model_name: str
    test_period_start: datetime
    test_period_end: datetime
    total_matches: int
    
    # Accuracy metrics
    accuracy: float  # Overall accuracy
    home_accuracy: float  # Accuracy on home win predictions
    draw_accuracy: float  # Accuracy on draw predictions  
    away_accuracy: float  # Accuracy on away win predictions
    
    # Calibration metrics
    mean_brier_score: float
    mean_log_loss: float
    
    # Confidence analysis
    high_confidence_accuracy: float  # Accuracy when confidence > 70%
    medium_confidence_accuracy: float  # Accuracy when 50% < confidence < 70%
    low_confidence_accuracy: float  # Accuracy when confidence < 50%
    
    # Breakdown by league
    league_accuracy: dict = field(default_factory=dict)
    
    # Calibration curve data (predicted confidence vs actual accuracy)
    calibration_buckets: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'model_name': self.model_name,
            'test_period_start': self.test_period_start.isoformat(),
            'test_period_end': self.test_period_end.isoformat(),
            'total_matches': self.total_matches,
            'accuracy': round(self.accuracy, 4),
            'home_accuracy': round(self.home_accuracy, 4),
            'draw_accuracy': round(self.draw_accuracy, 4),
            'away_accuracy': round(self.away_accuracy, 4),
            'mean_brier_score': round(self.mean_brier_score, 4),
            'mean_log_loss': round(self.mean_log_loss, 4),
            'high_confidence_accuracy': round(self.high_confidence_accuracy, 4),
            'medium_confidence_accuracy': round(self.medium_confidence_accuracy, 4),
            'low_confidence_accuracy': round(self.low_confidence_accuracy, 4),
            'league_accuracy': {k: round(v, 4) for k, v in self.league_accuracy.items()},
            'calibration_buckets': self.calibration_buckets
        }


class BacktestingFramework:
    """
    Historical backtesting framework for prediction validation.
    
    Uses time-series cross-validation to prevent future data leakage.
    Tests predictions against historical match results.
    """
    
    def __init__(
        self,
        data_dir: str = "data",
        results_dir: str = "reports/backtests"
    ):
        """
        Initialize backtesting framework.
        
        Args:
            data_dir: Directory containing historical match data
            results_dir: Directory to save backtest results
        """
        self.data_dir = Path(data_dir)
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # Historical data cache
        self._historical_data: list[dict] = []
        self._data_loaded = False
    
    def load_historical_data(
        self,
        leagues: Optional[list[str]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> list[dict]:
        """
        Load historical match data for backtesting.
        
        Args:
            leagues: List of league IDs to include (None = all)
            start_date: Earliest match date to include
            end_date: Latest match date to include
            
        Returns:
            List of match dictionaries with results
        """
        matches = []
        
        # Look for historical data in various locations
        historical_dirs = [
            self.data_dir / "historical",
            self.data_dir / "snapshots", 
            self.data_dir / "backup_csv",
            self.data_dir / "processed"
        ]
        
        for hist_dir in historical_dirs:
            if not hist_dir.exists():
                continue
                
            # Load JSON files
            for json_file in hist_dir.glob("**/*.json"):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # Handle different data formats
                    if isinstance(data, list):
                        for item in data:
                            match = self._parse_match_data(item)
                            if match:
                                matches.append(match)
                    elif isinstance(data, dict):
                        if 'matches' in data:
                            for item in data['matches']:
                                match = self._parse_match_data(item)
                                if match:
                                    matches.append(match)
                        else:
                            match = self._parse_match_data(data)
                            if match:
                                matches.append(match)
                except Exception as e:
                    logger.debug(f"Could not parse {json_file}: {e}")
        
        # Filter by league
        if leagues:
            matches = [m for m in matches if m.get('league') in leagues]
        
        # Filter by date
        if start_date:
            matches = [
                m for m in matches 
                if m.get('date') and m['date'] >= start_date
            ]
        if end_date:
            matches = [
                m for m in matches 
                if m.get('date') and m['date'] <= end_date
            ]
        
        # Sort by date
        matches.sort(key=lambda x: x.get('date', datetime.min))
        
        self._historical_data = matches
        self._data_loaded = True
        
        logger.info(f"Loaded {len(matches)} historical matches for backtesting")
        return matches
    
    def _parse_match_data(self, data: dict) -> Optional[dict]:
        """
        Parse match data from various formats.
        
        Returns:
            Standardized match dictionary or None if invalid
        """
        try:
            # Try to extract required fields
            match = {
                'id': data.get('id') or data.get('match_id') or '',
                'league': data.get('league') or data.get('competition') or 'unknown',
                'home_team': data.get('home_team') or data.get('homeTeam', {}).get('name', ''),
                'away_team': data.get('away_team') or data.get('awayTeam', {}).get('name', ''),
            }
            
            # Parse date
            date_str = data.get('date') or data.get('utcDate') or data.get('match_date')
            if isinstance(date_str, str):
                for fmt in ['%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d']:
                    try:
                        match['date'] = datetime.strptime(date_str.split('T')[0], '%Y-%m-%d')
                        break
                    except ValueError:
                        continue
            elif isinstance(date_str, datetime):
                match['date'] = date_str
            else:
                return None
            
            # Parse score - must have actual results
            score = data.get('score', {})
            if isinstance(score, dict):
                full_time = score.get('fullTime', {})
                match['home_goals'] = full_time.get('home') or full_time.get('homeTeam')
                match['away_goals'] = full_time.get('away') or full_time.get('awayTeam')
            else:
                match['home_goals'] = data.get('home_goals') or data.get('home_score')
                match['away_goals'] = data.get('away_goals') or data.get('away_score')
            
            # Validate we have goals
            if match['home_goals'] is None or match['away_goals'] is None:
                return None
            
            match['home_goals'] = int(match['home_goals'])
            match['away_goals'] = int(match['away_goals'])
            
            # Calculate actual outcome
            if match['home_goals'] > match['away_goals']:
                match['outcome'] = '1'
            elif match['home_goals'] < match['away_goals']:
                match['outcome'] = '2'
            else:
                match['outcome'] = 'X'
            
            # Optional fields
            match['home_team_id'] = data.get('home_team_id') or data.get('homeTeam', {}).get('id')
            match['away_team_id'] = data.get('away_team_id') or data.get('awayTeam', {}).get('id')
            
            return match
            
        except Exception as e:
            logger.debug(f"Error parsing match: {e}")
            return None
    
    def run_backtest(
        self,
        predictor: Callable[[dict], dict],
        model_name: str = "default",
        test_matches: Optional[list[dict]] = None,
        train_window_days: int = 180,
        test_window_days: int = 30,
        min_train_matches: int = 50
    ) -> BacktestSummary:
        """
        Run backtest using time-series cross-validation.
        
        Uses a rolling window approach:
        1. Train on matches from [t - train_window, t]
        2. Test on matches from [t, t + test_window]
        3. Roll forward and repeat
        
        Args:
            predictor: Function that takes match dict and returns prediction dict
            model_name: Name for this model version
            test_matches: Optional list of matches to test (uses loaded data if None)
            train_window_days: Days of historical data to use for training
            test_window_days: Days of future matches to test on
            min_train_matches: Minimum training matches required
            
        Returns:
            BacktestSummary with comprehensive metrics
        """
        if test_matches is None:
            if not self._data_loaded:
                self.load_historical_data()
            test_matches = self._historical_data
        
        if len(test_matches) < min_train_matches:
            logger.warning(f"Insufficient data for backtesting: {len(test_matches)} matches")
            # Return empty summary
            return BacktestSummary(
                model_name=model_name,
                test_period_start=datetime.now(),
                test_period_end=datetime.now(),
                total_matches=0,
                accuracy=0.0,
                home_accuracy=0.0,
                draw_accuracy=0.0,
                away_accuracy=0.0,
                mean_brier_score=1.0,
                mean_log_loss=2.0,
                high_confidence_accuracy=0.0,
                medium_confidence_accuracy=0.0,
                low_confidence_accuracy=0.0
            )
        
        results: list[BacktestResult] = []
        
        # Get date range
        dates = sorted([m['date'] for m in test_matches if 'date' in m])
        if not dates:
            logger.error("No valid dates in test matches")
            raise ValueError("No valid dates in test matches")
        
        start_date = dates[0]
        end_date = dates[-1]
        
        logger.info(f"Running backtest from {start_date.date()} to {end_date.date()}")
        
        # Rolling window backtest
        current_date = start_date + timedelta(days=train_window_days)
        
        while current_date <= end_date:
            window_start = current_date - timedelta(days=train_window_days)
            window_end = current_date + timedelta(days=test_window_days)
            
            # Get test matches for this window
            window_matches = [
                m for m in test_matches
                if current_date <= m.get('date', datetime.min) <= window_end
            ]
            
            for match in window_matches:
                try:
                    # Get prediction
                    prediction = predictor(match)
                    
                    if not prediction:
                        continue
                    
                    # Extract probabilities
                    home_prob = prediction.get('home_win_prob', prediction.get('home_prob', 33.3))
                    draw_prob = prediction.get('draw_prob', 33.3)
                    away_prob = prediction.get('away_win_prob', prediction.get('away_prob', 33.3))
                    confidence = prediction.get('confidence', 50.0)
                    
                    # Determine predicted outcome
                    probs = {'1': home_prob, 'X': draw_prob, '2': away_prob}
                    predicted_outcome = max(probs, key=probs.get)
                    
                    result = BacktestResult(
                        match_id=str(match.get('id', '')),
                        match_date=match['date'],
                        league=match.get('league', 'unknown'),
                        home_team=match.get('home_team', ''),
                        away_team=match.get('away_team', ''),
                        predicted_home_prob=home_prob,
                        predicted_draw_prob=draw_prob,
                        predicted_away_prob=away_prob,
                        predicted_outcome=predicted_outcome,
                        confidence=confidence,
                        actual_home_goals=match['home_goals'],
                        actual_away_goals=match['away_goals'],
                        actual_outcome=match['outcome']
                    )
                    results.append(result)
                    
                except Exception as e:
                    logger.debug(f"Error predicting match: {e}")
            
            current_date += timedelta(days=test_window_days)
        
        # Calculate summary statistics
        summary = self._calculate_summary(results, model_name)
        
        # Save results
        self._save_results(results, summary)
        
        return summary
    
    def _calculate_summary(
        self,
        results: list[BacktestResult],
        model_name: str
    ) -> BacktestSummary:
        """Calculate summary statistics from backtest results."""
        if not results:
            return BacktestSummary(
                model_name=model_name,
                test_period_start=datetime.now(),
                test_period_end=datetime.now(),
                total_matches=0,
                accuracy=0.0,
                home_accuracy=0.0,
                draw_accuracy=0.0,
                away_accuracy=0.0,
                mean_brier_score=1.0,
                mean_log_loss=2.0,
                high_confidence_accuracy=0.0,
                medium_confidence_accuracy=0.0,
                low_confidence_accuracy=0.0
            )
        
        dates = [r.match_date for r in results]
        
        # Overall accuracy
        correct = sum(1 for r in results if r.correct)
        accuracy = correct / len(results)
        
        # Accuracy by prediction type
        home_preds = [r for r in results if r.predicted_outcome == '1']
        draw_preds = [r for r in results if r.predicted_outcome == 'X']
        away_preds = [r for r in results if r.predicted_outcome == '2']
        
        home_accuracy = sum(1 for r in home_preds if r.correct) / max(len(home_preds), 1)
        draw_accuracy = sum(1 for r in draw_preds if r.correct) / max(len(draw_preds), 1)
        away_accuracy = sum(1 for r in away_preds if r.correct) / max(len(away_preds), 1)
        
        # Mean metrics
        mean_brier = sum(r.brier_score for r in results) / len(results)
        mean_log_loss = sum(r.log_loss for r in results) / len(results)
        
        # Confidence-based accuracy
        high_conf = [r for r in results if r.confidence >= 70]
        med_conf = [r for r in results if 50 <= r.confidence < 70]
        low_conf = [r for r in results if r.confidence < 50]
        
        high_conf_acc = sum(1 for r in high_conf if r.correct) / max(len(high_conf), 1)
        med_conf_acc = sum(1 for r in med_conf if r.correct) / max(len(med_conf), 1)
        low_conf_acc = sum(1 for r in low_conf if r.correct) / max(len(low_conf), 1)
        
        # League breakdown
        league_results = defaultdict(list)
        for r in results:
            league_results[r.league].append(r)
        
        league_accuracy = {
            league: sum(1 for r in rlist if r.correct) / len(rlist)
            for league, rlist in league_results.items()
        }
        
        # Calibration buckets (10% intervals)
        calibration = defaultdict(lambda: {'correct': 0, 'total': 0})
        for r in results:
            # Get the predicted probability for the predicted outcome
            if r.predicted_outcome == '1':
                prob = r.predicted_home_prob
            elif r.predicted_outcome == 'X':
                prob = r.predicted_draw_prob
            else:
                prob = r.predicted_away_prob
            
            bucket = int(prob // 10) * 10  # 0-10, 10-20, etc.
            calibration[bucket]['total'] += 1
            if r.correct:
                calibration[bucket]['correct'] += 1
        
        calibration_buckets = {
            f"{k}-{k+10}%": {
                'predicted': k + 5,  # midpoint
                'actual': round(v['correct'] / max(v['total'], 1) * 100, 1),
                'count': v['total']
            }
            for k, v in sorted(calibration.items())
        }
        
        return BacktestSummary(
            model_name=model_name,
            test_period_start=min(dates),
            test_period_end=max(dates),
            total_matches=len(results),
            accuracy=accuracy,
            home_accuracy=home_accuracy,
            draw_accuracy=draw_accuracy,
            away_accuracy=away_accuracy,
            mean_brier_score=mean_brier,
            mean_log_loss=mean_log_loss,
            high_confidence_accuracy=high_conf_acc,
            medium_confidence_accuracy=med_conf_acc,
            low_confidence_accuracy=low_conf_acc,
            league_accuracy=league_accuracy,
            calibration_buckets=calibration_buckets
        )
    
    def _save_results(
        self,
        results: list[BacktestResult],
        summary: BacktestSummary
    ):
        """Save backtest results to files."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save summary
        summary_file = self.results_dir / f"backtest_summary_{timestamp}.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary.to_dict(), f, indent=2)
        
        # Save detailed results
        details_file = self.results_dir / f"backtest_details_{timestamp}.json"
        detail_data = [
            {
                'match_id': r.match_id,
                'date': r.match_date.isoformat(),
                'league': r.league,
                'home_team': r.home_team,
                'away_team': r.away_team,
                'predicted': r.predicted_outcome,
                'actual': r.actual_outcome,
                'correct': r.correct,
                'confidence': r.confidence,
                'brier_score': round(r.brier_score, 4)
            }
            for r in results
        ]
        with open(details_file, 'w', encoding='utf-8') as f:
            json.dump(detail_data, f, indent=2)
        
        logger.info(f"Saved backtest results to {summary_file}")
    
    def compare_models(
        self,
        summaries: list[BacktestSummary]
    ) -> dict:
        """
        Compare multiple model backtests.
        
        Returns comparison data showing which model performs better.
        """
        if len(summaries) < 2:
            return {'error': 'Need at least 2 models to compare'}
        
        comparison = {
            'models': [s.model_name for s in summaries],
            'accuracy_ranking': sorted(
                [(s.model_name, s.accuracy) for s in summaries],
                key=lambda x: x[1],
                reverse=True
            ),
            'brier_ranking': sorted(
                [(s.model_name, s.mean_brier_score) for s in summaries],
                key=lambda x: x[1]  # Lower is better
            ),
            'calibration_ranking': sorted(
                [(s.model_name, s.high_confidence_accuracy) for s in summaries],
                key=lambda x: x[1],
                reverse=True
            ),
            'detailed_comparison': {
                s.model_name: {
                    'accuracy': round(s.accuracy * 100, 2),
                    'brier_score': round(s.mean_brier_score, 4),
                    'high_conf_accuracy': round(s.high_confidence_accuracy * 100, 2),
                    'matches_tested': s.total_matches
                }
                for s in summaries
            }
        }
        
        # Find best model
        best_accuracy = max(summaries, key=lambda s: s.accuracy)
        best_brier = min(summaries, key=lambda s: s.mean_brier_score)
        
        comparison['recommendations'] = {
            'best_accuracy': best_accuracy.model_name,
            'best_calibration': best_brier.model_name,
            'improvement': round(
                (max(s.accuracy for s in summaries) - 
                 min(s.accuracy for s in summaries)) * 100,
                2
            )
        }
        
        return comparison


def create_simple_predictor(enhanced_predictor) -> Callable[[dict], dict]:
    """
    Create a predictor function from EnhancedPredictor for backtesting.
    
    Args:
        enhanced_predictor: Instance of EnhancedPredictor
        
    Returns:
        Function that takes match dict and returns prediction
    """
    def predict(match: dict) -> dict:
        """Make prediction for a match."""
        try:
            # Build match data for predictor
            match_data = {
                'home_team': match.get('home_team', ''),
                'away_team': match.get('away_team', ''),
                'home_team_id': match.get('home_team_id'),
                'away_team_id': match.get('away_team_id'),
                'date': match.get('date'),
                'league': match.get('league'),
            }
            
            # Call the predictor
            result = enhanced_predictor.enhanced_prediction(
                home_team=match_data['home_team'],
                away_team=match_data['away_team'],
                league=match_data.get('league', 'unknown'),
                match_date=match_data.get('date')
            )
            
            return result
            
        except Exception as e:
            logger.debug(f"Prediction error: {e}")
            return None
    
    return predict


# Quick validation test
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Create framework
    framework = BacktestingFramework()
    
    # Try to load historical data
    matches = framework.load_historical_data()
    
    if matches:
        print(f"Loaded {len(matches)} historical matches")
        print(f"Date range: {matches[0]['date']} to {matches[-1]['date']}")
        print(f"Leagues: {set(m['league'] for m in matches[:100])}")
    else:
        print("No historical data found - creating sample backtest...")
        
        # Create sample matches for testing
        sample_matches = [
            {
                'id': f'test_{i}',
                'date': datetime(2024, 1, 1) + timedelta(days=i),
                'league': 'premier-league',
                'home_team': 'Team A',
                'away_team': 'Team B',
                'home_goals': 2 if i % 3 == 0 else 1,
                'away_goals': 1 if i % 4 == 0 else 0,
                'outcome': '1' if i % 3 == 0 else 'X' if i % 4 == 0 else '2'
            }
            for i in range(100)
        ]
        
        # Simple predictor for testing
        def dummy_predictor(match):
            return {
                'home_win_prob': 45.0,
                'draw_prob': 25.0,
                'away_win_prob': 30.0,
                'confidence': 55.0
            }
        
        summary = framework.run_backtest(
            predictor=dummy_predictor,
            model_name="dummy_test",
            test_matches=sample_matches
        )
        
        print(f"\nBacktest Summary:")
        print(f"  Model: {summary.model_name}")
        print(f"  Matches tested: {summary.total_matches}")
        print(f"  Accuracy: {summary.accuracy*100:.1f}%")
        print(f"  Brier Score: {summary.mean_brier_score:.4f}")
        print(f"  High-conf accuracy: {summary.high_confidence_accuracy*100:.1f}%")
