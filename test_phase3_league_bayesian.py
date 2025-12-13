"""
Phase 3 Testing Suite - League Tuning, Bayesian Updates, Context Weighting

Comprehensive tests for all Phase 3 components including:
- LeagueTuner class and per-league calibration
- BayesianUpdater class and posterior updates
- ContextExtractor and context-aware adjustments
- Integration with EnhancedPredictor
- Regression testing for Phase 1 & 2
"""

import unittest
import json
import os
import tempfile
from datetime import datetime, date, timedelta
from unittest.mock import Mock, patch, MagicMock
import numpy as np

from app.models.league_tuner import LeagueTuner
from app.models.bayesian_updater import BayesianUpdater
from app.utils.context_extractor import ContextExtractor


class TestLeagueTuner(unittest.TestCase):
    """Test LeagueTuner functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.tuner = LeagueTuner(
            leagues=['la-liga', 'premier-league', 'bundesliga', 'serie-a'],
            cache_dir=self.temp_dir
        )
    
    def tearDown(self):
        """Clean up"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_league_tuner_initialization(self):
        """Test LeagueTuner initializes with all leagues"""
        self.assertEqual(len(self.tuner.league_calibrators), 4)
        self.assertEqual(len(self.tuner.league_trackers), 4)
        self.assertIn('la-liga', self.tuner.league_calibrators)
        self.assertIn('premier-league', self.tuner.league_calibrators)
    
    def test_get_league_calibrator(self):
        """Test getting league-specific calibrator"""
        cal = self.tuner.get_league_calibrator('la-liga')
        self.assertIsNotNone(cal)
        self.assertEqual(cal.model_name, 'ensemble_la-liga')
    
    def test_get_league_characteristics(self):
        """Test league characteristics"""
        char = self.tuner.get_league_characteristics('bundesliga')
        self.assertEqual(char['pacing'], 'very_fast')
        self.assertEqual(char['defense'], 'weak')
        self.assertEqual(char['goals'], 3.1)
    
    def test_league_adjustment_high_variance(self):
        """Test confidence adjustment for high-variance league"""
        # Bundesliga has high variance (0.55)
        adjusted, meta = self.tuner.apply_league_adjustment('bundesliga', 0.75)
        # Should reduce confidence due to high variance
        self.assertLess(adjusted, 0.75)
        self.assertIn('goal_variance', meta['adjustments'])
        self.assertEqual(meta['adjustments']['goal_variance'], 0.93)
    
    def test_league_adjustment_low_variance(self):
        """Test confidence adjustment for low-variance league"""
        # Serie A has low variance (0.25)
        adjusted, meta = self.tuner.apply_league_adjustment('serie-a', 0.75)
        # Should increase confidence due to low variance (predictable)
        self.assertGreater(adjusted, 0.75)
        self.assertIn('goal_variance', meta['adjustments'])
        self.assertEqual(meta['adjustments']['goal_variance'], 1.07)
    
    def test_league_adjustment_defensive_strength(self):
        """Test defensive strength adjustment"""
        # La Liga has strong defense
        adjusted, meta = self.tuner.apply_league_adjustment('la-liga', 0.75)
        self.assertGreater(adjusted, 0.75)
        self.assertIn('defense', meta['adjustments'])
        self.assertEqual(meta['adjustments']['defense'], 1.05)
    
    def test_record_league_match(self):
        """Test recording match for league learning"""
        initial_samples = len(self.tuner.league_calibrators['la-liga'].calibration_data.get('predictions', []))
        
        self.tuner.record_league_match('la-liga', 0.75, 1.0)
        
        # Verify recorded
        self.assertGreater(len(self.tuner.league_calibrators['la-liga'].calibration_data.get('predictions', [])), initial_samples)
    
    def test_get_league_statistics(self):
        """Test getting league statistics"""
        # Record some matches
        for i in range(5):
            self.tuner.record_league_match('premier-league', 0.7, float(i % 2))
        
        stats = self.tuner.get_league_statistics('premier-league')
        self.assertIn('league', stats)
        self.assertIn('calibration', stats)
        self.assertIn('model_performance', stats)
        self.assertEqual(stats['calibration']['samples'], 5)
    
    def test_league_persistence(self):
        """Test saving and loading league data"""
        # Record match
        self.tuner.record_league_match('la-liga', 0.75, 1.0)
        
        # Save
        self.tuner.save_league_data()
        
        # Verify files created
        cal_file = os.path.join(self.temp_dir, 'league_calibration_la-liga.json')
        self.assertTrue(os.path.exists(cal_file))
        
        # Load in new instance
        tuner2 = LeagueTuner(
            leagues=['la-liga', 'premier-league'],
            cache_dir=self.temp_dir
        )
        self.assertGreater(len(tuner2.league_calibrators['la-liga'].calibration_data.get('predictions', [])), 0)


class TestBayesianUpdater(unittest.TestCase):
    """Test BayesianUpdater functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.updater = BayesianUpdater(
            prior_alpha=2.0,
            prior_beta=2.0,
            learning_rate=0.8,
            cache_dir=self.temp_dir
        )
    
    def tearDown(self):
        """Clean up"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_bayesian_initialization(self):
        """Test Bayesian updater initializes correctly"""
        self.assertEqual(self.updater.prior_alpha, 2.0)
        self.assertEqual(self.updater.prior_beta, 2.0)
        self.assertEqual(self.updater.posterior_alpha, 2.0)
        self.assertEqual(self.updater.posterior_beta, 2.0)
    
    def test_posterior_mean_calculation(self):
        """Test posterior mean calculation"""
        # Initial: alpha=beta=2 → mean=0.5
        mean = self.updater.get_posterior_mean()
        self.assertEqual(mean, 0.5)
        
        # After 10 successful predictions: alpha=12, beta=2 → mean≈0.857
        for _ in range(10):
            self.updater.record_match(0.75, True)
        
        mean = self.updater.get_posterior_mean()
        self.assertGreater(mean, 0.8)
        self.assertLess(mean, 0.9)
    
    def test_posterior_std_decreases_with_samples(self):
        """Test posterior uncertainty decreases with more samples"""
        std_initial = self.updater.get_posterior_std()
        
        # Record 20 matches
        for i in range(20):
            self.updater.record_match(0.7, i % 2 == 0)
        
        std_later = self.updater.get_posterior_std()
        
        # Uncertainty should decrease
        self.assertLess(std_later, std_initial)
    
    def test_record_match_successful(self):
        """Test recording successful prediction"""
        record = self.updater.record_match(0.75, True)
        
        self.assertTrue(record['prediction_correct'])
        self.assertEqual(self.updater.posterior_alpha, 3.0)  # 2+1
        self.assertEqual(self.updater.posterior_beta, 2.0)  # unchanged
        self.assertEqual(self.updater.successful_predictions, 1)
        self.assertEqual(self.updater.total_predictions, 1)
    
    def test_record_match_unsuccessful(self):
        """Test recording unsuccessful prediction"""
        record = self.updater.record_match(0.75, False)
        
        self.assertFalse(record['prediction_correct'])
        self.assertEqual(self.updater.posterior_alpha, 2.0)  # unchanged
        self.assertEqual(self.updater.posterior_beta, 3.0)  # 2+1
        self.assertEqual(self.updater.successful_predictions, 0)
    
    def test_credible_interval_calculation(self):
        """Test credible interval calculation"""
        # Record 20 matches (should be accurate ~60% of time)
        for i in range(20):
            self.updater.record_match(0.7, i % 10 < 6)  # 60% win rate
        
        lower, upper = self.updater.get_posterior_credible_interval(0.95)
        
        # 95% credible interval should contain posterior mean
        mean = self.updater.get_posterior_mean()
        self.assertLess(lower, mean)
        self.assertLess(mean, upper)
    
    def test_confidence_adjustment_insufficient_data(self):
        """Test no adjustment with insufficient samples"""
        adjusted, meta = self.updater.adjust_confidence(0.75)
        
        # Should not adjust with <10 samples
        self.assertEqual(adjusted, 0.75)
        self.assertEqual(meta['reason'], 'insufficient_samples')
    
    def test_confidence_adjustment_with_data(self):
        """Test confidence adjustment after sufficient data"""
        # Record 15 successful matches
        for _ in range(15):
            self.updater.record_match(0.75, True)
        
        adjusted, meta = self.updater.adjust_confidence(0.75)
        
        # Should adjust toward higher posterior mean (system is accurate)
        self.assertGreater(adjusted, 0.75)
        self.assertEqual(meta['samples_used'], 15)
    
    def test_bayesian_statistics(self):
        """Test getting Bayesian statistics"""
        # Record some matches
        for i in range(20):
            self.updater.record_match(0.7, i % 2 == 0)
        
        stats = self.updater.get_bayesian_statistics()
        
        self.assertIn('total_predictions', stats)
        self.assertIn('successful_predictions', stats)
        self.assertIn('overall_accuracy', stats)
        self.assertIn('posterior_mean', stats)
        self.assertIn('posterior_std', stats)
        self.assertIn('credible_interval_95', stats)
        self.assertEqual(stats['total_predictions'], 20)
    
    def test_reset_posterior_keep_history(self):
        """Test reset posterior keeping history"""
        # Record match
        self.updater.record_match(0.75, True)
        self.assertEqual(len(self.updater.match_history), 1)
        
        # Reset
        self.updater.reset_posterior(keep_history=True)
        
        self.assertEqual(self.updater.posterior_alpha, 2.0)
        self.assertEqual(self.updater.posterior_beta, 2.0)
        self.assertEqual(len(self.updater.match_history), 1)  # History kept
    
    def test_reset_posterior_clear_history(self):
        """Test reset posterior clearing history"""
        # Record match
        self.updater.record_match(0.75, True)
        
        # Reset
        self.updater.reset_posterior(keep_history=False)
        
        self.assertEqual(len(self.updater.match_history), 0)
    
    def test_bayesian_persistence(self):
        """Test saving and loading Bayesian state"""
        # Record matches
        for i in range(10):
            self.updater.record_match(0.7, i % 2 == 0)
        
        # Save
        self.updater.save_bayesian_state()
        
        # Verify file created
        state_file = os.path.join(self.temp_dir, 'bayesian_updater_state.json')
        self.assertTrue(os.path.exists(state_file))
        
        # Load in new instance
        updater2 = BayesianUpdater(cache_dir=self.temp_dir)
        self.assertEqual(updater2.total_predictions, 10)


class TestContextExtractor(unittest.TestCase):
    """Test ContextExtractor functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.extractor = ContextExtractor(cache_dir=self.temp_dir)
    
    def tearDown(self):
        """Clean up"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_season_phase_early(self):
        """Test early season phase detection"""
        early_date = date(2025, 8, 15)
        phase = self.extractor.get_season_phase(early_date)
        self.assertEqual(phase, 'early')
    
    def test_season_phase_buildup(self):
        """Test buildup season phase detection"""
        buildup_date = date(2025, 10, 15)
        phase = self.extractor.get_season_phase(buildup_date)
        self.assertEqual(phase, 'buildup')
    
    def test_season_phase_midseason(self):
        """Test midseason phase detection"""
        midseason_date = date(2025, 12, 15)
        phase = self.extractor.get_season_phase(midseason_date)
        self.assertEqual(phase, 'midseason')
    
    def test_season_phase_second_half(self):
        """Test second half phase detection"""
        second_half_date = date(2026, 2, 15)
        phase = self.extractor.get_season_phase(second_half_date)
        self.assertEqual(phase, 'second_half')
    
    def test_home_away_adjustment_elite_home(self):
        """Test home/away adjustment for elite team at home"""
        factor, meta = self.extractor.calculate_home_away_adjustment(
            is_home=True,
            home_team_level='elite',
            away_team_level='average'
        )
        
        self.assertEqual(factor, 1.05)
        self.assertEqual(meta['is_home'], True)
    
    def test_home_away_adjustment_weak_away(self):
        """Test home/away adjustment for weak team away"""
        factor, meta = self.extractor.calculate_home_away_adjustment(
            is_home=False,
            home_team_level='average',
            away_team_level='weak'
        )
        
        self.assertEqual(factor, 0.94)
        self.assertEqual(meta['is_home'], False)
    
    def test_season_phase_adjustment(self):
        """Test season phase adjustment"""
        # Early season should reduce confidence
        early_date = date(2025, 8, 15)
        factor, meta = self.extractor.calculate_season_phase_adjustment(early_date)
        self.assertEqual(factor, 0.95)
        self.assertEqual(meta['phase'], 'early')
    
    def test_competition_level_adjustment_mismatch(self):
        """Test competition level adjustment for mismatched teams"""
        # Title contender vs relegation team
        factor, meta = self.extractor.calculate_competition_level_adjustment(
            home_level='title_contender',
            away_level='relegation'
        )
        
        # Should increase confidence for obvious winner
        self.assertEqual(factor, 1.10)
    
    def test_competition_level_adjustment_balanced(self):
        """Test competition level adjustment for balanced match"""
        # Mid-table vs mid-table
        factor, meta = self.extractor.calculate_competition_level_adjustment(
            home_level='mid_table',
            away_level='mid_table'
        )
        
        # Should be neutral
        self.assertEqual(factor, 1.0)
    
    def test_venue_performance_no_data(self):
        """Test venue adjustment with no historical data"""
        factor, meta = self.extractor.calculate_venue_performance_adjustment(
            venue='Santiago Bernabeu',
            team='Real Madrid',
            is_home=True
        )
        
        self.assertEqual(factor, 1.0)
        self.assertEqual(meta['reason'], 'no_historical_data')
    
    def test_record_venue_match(self):
        """Test recording venue match for learning"""
        self.extractor.record_match_at_venue(
            venue='Wanda Metropolitano',
            home_team='Atletico Madrid',
            away_team='Barcelona',
            home_won=True
        )
        
        # Verify recorded
        venue_key = 'Wanda Metropolitano_Atletico Madrid'
        self.assertIn(venue_key, self.extractor.venue_performance)
        self.assertEqual(self.extractor.venue_performance[venue_key]['wins'], 1)
    
    def test_apply_all_context_adjustments(self):
        """Test applying all context adjustments together"""
        test_date = date(2025, 10, 15)
        
        adjusted, meta = self.extractor.apply_all_context_adjustments(
            confidence=0.75,
            is_home=True,
            home_team_level='strong',
            away_team_level='average',
            match_date=test_date,
            home_competition_level='title_contender',
            away_competition_level='mid_table',
            venue='Camp Nou',
            team='Barcelona'
        )
        
        # Should have applied all adjustments
        self.assertIn('home_away', meta['adjustments'])
        self.assertIn('season_phase', meta['adjustments'])
        self.assertIn('competition_level', meta['adjustments'])
        self.assertIn('venue', meta['adjustments'])
        
        # Final confidence should be valid
        self.assertGreaterEqual(adjusted, 0.0)
        self.assertLessEqual(adjusted, 1.0)


class TestPhase3Integration(unittest.TestCase):
    """Test Phase 3 integration with EnhancedPredictor"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_phase3_components_initialization(self):
        """Test all Phase 3 components can be initialized together"""
        tuner = LeagueTuner(cache_dir=self.temp_dir)
        updater = BayesianUpdater(cache_dir=self.temp_dir)
        extractor = ContextExtractor(cache_dir=self.temp_dir)
        
        # Verify all initialized
        self.assertIsNotNone(tuner)
        self.assertIsNotNone(updater)
        self.assertIsNotNone(extractor)
    
    def test_phase3_workflow_sequence(self):
        """Test realistic Phase 3 workflow"""
        tuner = LeagueTuner(cache_dir=self.temp_dir)
        updater = BayesianUpdater(cache_dir=self.temp_dir)
        extractor = ContextExtractor(cache_dir=self.temp_dir)
        
        # Simulate prediction workflow
        raw_confidence = 0.75
        
        # 1. League tuning
        league_adjusted, _ = tuner.apply_league_adjustment('premier-league', raw_confidence)
        
        # 2. Bayesian (need samples first)
        for _ in range(15):
            updater.record_match(0.7, True)
        bayesian_adjusted, _ = updater.adjust_confidence(league_adjusted)
        
        # 3. Context weighting
        final_adjusted, _ = extractor.apply_all_context_adjustments(
            confidence=bayesian_adjusted,
            is_home=True,
            match_date=date(2025, 10, 15)
        )
        
        # Verify result
        self.assertGreaterEqual(final_adjusted, 0.0)
        self.assertLessEqual(final_adjusted, 1.0)
    
    def test_phase3_persistence_workflow(self):
        """Test Phase 3 data persistence workflow"""
        # Create and save
        tuner1 = LeagueTuner(cache_dir=self.temp_dir)
        updater1 = BayesianUpdater(cache_dir=self.temp_dir)
        extractor1 = ContextExtractor(cache_dir=self.temp_dir)
        
        tuner1.record_league_match('la-liga', 0.75, 1.0)
        updater1.record_match(0.75, True)
        extractor1.record_match_at_venue('Bernabeu', 'Real Madrid', 'Barca', True)
        
        tuner1.save_league_data()
        updater1.save_bayesian_state()
        extractor1.save_venue_performance()
        
        # Load in new instances
        tuner2 = LeagueTuner(cache_dir=self.temp_dir)
        updater2 = BayesianUpdater(cache_dir=self.temp_dir)
        extractor2 = ContextExtractor(cache_dir=self.temp_dir)
        
        # Verify data persisted
        self.assertGreater(len(tuner2.league_calibrators['la-liga'].calibration_data.get('predictions', [])), 0)
        self.assertEqual(updater2.total_predictions, 1)
        self.assertIn('Bernabeu_Real Madrid', extractor2.venue_performance)


class TestPhase3Regressions(unittest.TestCase):
    """Test that Phase 3 doesn't break Phase 1 & 2"""
    
    def test_phase3_doesnt_break_phase2(self):
        """Test Phase 3 integration doesn't break calibration"""
        from app.models.calibration_manager import CalibrationManager
        
        # Phase 2 should still work
        cal = CalibrationManager()
        cal.add_calibration_sample(0.75, 1.0)
        
        # Phase 3 shouldn't affect Phase 2
        tuner = LeagueTuner()
        adjusted_p3, _ = tuner.apply_league_adjustment('premier-league', 0.75)
        
        # Both should produce valid results
        self.assertGreater(len(cal.calibration_data.get('predictions', [])), 0)
        self.assertGreater(adjusted_p3, 0.0)
        self.assertLess(adjusted_p3, 1.0)


if __name__ == '__main__':
    unittest.main()
