"""
Phase 4: Real-Time Monitoring & Adaptive Adjustment - Comprehensive Test Suite

37 tests covering PerformanceMonitor, DriftAnalyzer, and AdaptiveAdjuster
"""

import pytest
from datetime import datetime
import tempfile
from app.monitoring import PerformanceMonitor, DriftAnalyzer, AdaptiveAdjuster


class TestPerformanceMonitor:
    """Test real-time performance monitoring (14 tests)."""
    
    @pytest.fixture
    def monitor(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield PerformanceMonitor(cache_dir=tmpdir)
    
    def test_init(self, monitor):
        assert monitor.window_size == 50
        assert monitor.system_metrics['total_predictions'] == 0
    
    def test_record_single(self, monitor):
        monitor.record_prediction('la-liga', 'xg', 0.8, 1.0)
        assert monitor.system_metrics['total_predictions'] == 1
        assert 'la-liga' in monitor.league_performance
    
    def test_league_tracking(self, monitor):
        monitor.record_prediction('la-liga', 'xg', 0.8, 1.0)
        monitor.record_prediction('la-liga', 'xg', 0.3, 0.0)
        monitor.record_prediction('la-liga', 'xg', 0.6, 0.0)
        
        stats = monitor.get_league_performance('la-liga')
        assert stats['samples'] == 3
        assert abs(stats['accuracy'] - 2/3) < 0.01
    
    def test_model_tracking(self, monitor):
        monitor.record_prediction('la-liga', 'xg', 0.8, 1.0)
        monitor.record_prediction('la-liga', 'poisson', 0.3, 0.0)
        
        xg = monitor.get_model_performance('xg')
        poisson = monitor.get_model_performance('poisson')
        
        assert xg['samples'] == 1
        assert poisson['samples'] == 1
    
    def test_calibration_error(self, monitor):
        monitor.record_prediction('la-liga', 'xg', 0.9, 1.0)
        monitor.record_prediction('la-liga', 'xg', 0.1, 0.0)
        monitor.record_prediction('la-liga', 'xg', 0.5, 0.5)
        
        stats = monitor.get_league_performance('la-liga')
        # Average error: (0.1 + 0.1 + 0.0) / 3 = 0.0667
        assert abs(stats['calibration_error'] - 0.0667) < 0.01
    
    def test_no_drift_normal(self, monitor):
        for _ in range(15):
            monitor.record_prediction('la-liga', 'xg', 0.8, 1.0)
            monitor.record_prediction('la-liga', 'xg', 0.2, 0.0)
        
        is_drift, severity = monitor.get_drift_status()
        assert severity <= 0.5
    
    def test_drift_detection_accuracy_drop(self, monitor):
        for _ in range(5):
            monitor.record_prediction('la-liga', 'xg', 0.8, 1.0)
        
        for _ in range(10):
            monitor.record_prediction('la-liga', 'xg', 0.8, 0.0)
        
        is_drift, severity = monitor.get_drift_status()
        assert severity > 0.0
    
    def test_recommendations_normal(self, monitor):
        for _ in range(10):
            monitor.record_prediction('la-liga', 'xg', 0.8, 1.0)
            monitor.record_prediction('la-liga', 'xg', 0.2, 0.0)
        
        recs = monitor.get_recommendations()
        assert len(recs) > 0
    
    def test_recommendations_poor(self, monitor):
        for _ in range(10):
            monitor.record_prediction('la-liga', 'xg', 0.8, 0.0)
        
        recs = monitor.get_recommendations()
        assert any("⚠️" in r for r in recs)
    
    def test_recent_window(self, monitor):
        for i in range(10):
            monitor.record_prediction('la-liga', 'xg', 0.5 + i*0.05, 1.0)
        
        window = monitor.get_recent_window('la-liga', window_size=5)
        assert len(window) == 5
    
    def test_system_metrics(self, monitor):
        monitor.record_prediction('la-liga', 'xg', 0.8, 1.0)
        monitor.record_prediction('la-liga', 'xg', 0.3, 0.0)
        
        metrics = monitor.get_system_metrics()
        assert metrics['total_predictions'] == 2
        assert 0.0 <= metrics['overall_accuracy'] <= 1.0
    
    def test_monitor_save(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            m1 = PerformanceMonitor(cache_dir=tmpdir)
            m1.record_prediction('la-liga', 'xg', 0.8, 1.0)
            m1.save_monitor_state()
            
            m2 = PerformanceMonitor(cache_dir=tmpdir)
            assert m2.system_metrics['total_predictions'] > 0
    
    def test_multiple_leagues(self, monitor):
        for league in ['la-liga', 'premier-league', 'bundesliga']:
            monitor.record_prediction(league, 'xg', 0.75, 1.0)
        
        assert len(monitor.league_performance) == 3
    
    def test_multiple_models(self, monitor):
        for model in ['xg', 'poisson', 'elo']:
            monitor.record_prediction('la-liga', model, 0.7, 1.0)
        
        assert len(monitor.model_performance) == 3


class TestDriftAnalyzer:
    """Test statistical drift analysis (6 tests)."""
    
    @pytest.fixture
    def analyzer(self):
        return DriftAnalyzer(reference_window_size=10, test_window_size=5)
    
    def test_analyzer_init(self, analyzer):
        assert analyzer.reference_window_size == 10
        assert analyzer.test_window_size == 5
    
    def test_no_drift_stable(self, analyzer):
        preds = [(0.8, 1.0), (0.2, 0.0)] * 10
        result = analyzer.analyze_drift(preds)
        assert result['drift_detected'] == False
    
    def test_drift_accuracy_change(self, analyzer):
        reference = [(0.8, 1.0), (0.2, 0.0)] * 5
        current = [(0.8, 0.0), (0.2, 1.0)] * 3
        preds = reference + current
        
        result = analyzer.analyze_drift(preds)
        assert result['test_statistic'] > 0.0
    
    def test_insufficient_samples(self, analyzer):
        preds = [(0.5, 1.0)] * 5
        result = analyzer.analyze_drift(preds)
        assert result['drift_detected'] == False
    
    def test_high_accuracy_change(self, analyzer):
        good_preds = [(0.9, 1.0)] * 10
        bad_preds = [(0.1, 1.0)] * 5
        
        result = analyzer.analyze_drift(good_preds + bad_preds)
        assert result['test_statistic'] > 0.1
    
    def test_analyzer_stats(self, analyzer):
        preds = [(0.7, 0.8)] * 20
        result = analyzer.analyze_drift(preds)
        assert 'reference_accuracy' in result
        assert 'current_accuracy' in result


class TestAdaptiveAdjuster:
    """Test adaptive confidence adjustment (17 tests)."""
    
    @pytest.fixture
    def adjuster(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield AdaptiveAdjuster(cache_dir=tmpdir, adaptation_rate=0.1)
    
    def test_init(self, adjuster):
        assert adjuster.adaptation_rate == 0.1
        assert len(adjuster.league_factors) == 5
        assert adjuster.confidence_scale == 1.0
    
    def test_get_league_factor(self, adjuster):
        assert adjuster.get_adapted_league_factor('la-liga') == pytest.approx(1.0)
        assert adjuster.get_adapted_league_factor('premier-league') > 1.0
    
    def test_adapt_league_good_perf(self, adjuster):
        perf = {'la-liga': {'accuracy': 0.75, 'samples': 10}}
        adjuster.adapt_league_factors(perf)
        
        new_factor = adjuster.get_adapted_league_factor('la-liga')
        assert new_factor > 1.0
    
    def test_adapt_league_poor_perf(self, adjuster):
        perf = {'la-liga': {'accuracy': 0.55, 'samples': 10}}
        adjuster.adapt_league_factors(perf)
        
        new_factor = adjuster.get_adapted_league_factor('la-liga')
        assert new_factor < 1.0
    
    def test_adapt_league_insufficient_data(self, adjuster):
        perf = {'la-liga': {'accuracy': 0.9, 'samples': 2}}
        original = adjuster.get_adapted_league_factor('la-liga')
        adjuster.adapt_league_factors(perf)
        
        assert adjuster.get_adapted_league_factor('la-liga') == original
    
    def test_adapt_context_effective(self, adjuster):
        adjuster.adapt_context_weights({'home_away': 0.8})
        assert adjuster.context_weights['home_away'] > 1.0
    
    def test_adapt_context_ineffective(self, adjuster):
        adjuster.adapt_context_weights({'home_away': 0.2})
        assert adjuster.context_weights['home_away'] < 1.0
    
    def test_adapt_bayesian_high_error(self, adjuster):
        adjuster.adapt_bayesian_parameters(calibration_error=0.12, samples=10)
        adjustment = adjuster.get_adapted_bayesian_adjustment()
        assert adjustment < 1.0
    
    def test_adapt_bayesian_low_error(self, adjuster):
        adjuster.adapt_bayesian_parameters(calibration_error=0.05, samples=10)
        adjustment = adjuster.get_adapted_bayesian_adjustment()
        assert adjustment > 1.0
    
    def test_confidence_scale_below_baseline(self, adjuster):
        adjuster.adapt_confidence_scale(drift_severity=0.0, accuracy=0.60)
        assert adjuster.get_confidence_scale() < 1.0
    
    def test_confidence_scale_above_baseline(self, adjuster):
        adjuster.adapt_confidence_scale(drift_severity=0.0, accuracy=0.70)
        assert adjuster.get_confidence_scale() >= 1.0
    
    def test_confidence_scale_with_drift(self, adjuster):
        adjuster.adapt_confidence_scale(drift_severity=0.8, accuracy=0.65)
        assert adjuster.get_confidence_scale() < 1.0
    
    def test_apply_adaptations(self, adjuster):
        adjuster.confidence_scale = 0.95
        adjuster.league_factors['la-liga'] = 1.05
        
        adapted = adjuster.apply_adaptations(0.60, 'la-liga')
        expected = 0.60 * 1.05 * 0.95
        
        assert abs(adapted - expected) < 0.001
    
    def test_apply_adaptations_clamp(self, adjuster):
        adjuster.confidence_scale = 2.0
        adapted = adjuster.apply_adaptations(0.8, 'la-liga')
        assert 0.0 <= adapted <= 1.0
    
    def test_reset_baseline(self, adjuster):
        adjuster.confidence_scale = 0.8
        adjuster.league_factors['la-liga'] = 0.9
        
        adjuster.reset_to_baseline()
        
        assert adjuster.confidence_scale == 1.0
        assert adjuster.league_factors['la-liga'] == pytest.approx(1.0)
    
    def test_adjuster_save(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            a1 = AdaptiveAdjuster(cache_dir=tmpdir)
            a1.confidence_scale = 0.95
            a1.save_adjuster_state()
            
            a2 = AdaptiveAdjuster(cache_dir=tmpdir)
            assert abs(a2.confidence_scale - 0.95) < 0.01


class TestPhase4Integration:
    """Integration tests (4 tests)."""
    
    def test_monitor_and_adjuster(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = PerformanceMonitor(cache_dir=tmpdir)
            adjuster = AdaptiveAdjuster(cache_dir=tmpdir)
            
            for i in range(20):
                conf = 0.6 + (i % 2) * 0.3
                outcome = 1.0 if i % 2 == 0 else 0.0
                monitor.record_prediction('la-liga', 'xg', conf, outcome)
            
            league_stats = monitor.get_league_performance('la-liga')
            metrics = monitor.get_system_metrics()
            
            adjuster.adapt_league_factors({'la-liga': league_stats})
            adjuster.adapt_confidence_scale(metrics['drift_severity'], metrics['overall_accuracy'])
            
            assert adjuster.get_confidence_scale() != 1.0 or metrics['overall_accuracy'] == pytest.approx(0.65)
    
    def test_drift_triggers_adaptation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = PerformanceMonitor(cache_dir=tmpdir)
            adjuster = AdaptiveAdjuster(cache_dir=tmpdir)
            
            for _ in range(5):
                monitor.record_prediction('la-liga', 'xg', 0.8, 1.0)
            
            for _ in range(15):
                monitor.record_prediction('la-liga', 'xg', 0.8, 0.0)
            
            metrics = monitor.get_system_metrics()
            adjuster.adapt_confidence_scale(metrics['drift_severity'], metrics['overall_accuracy'])
            
            assert adjuster.get_confidence_scale() < 1.0
    
    def test_continuous_learning(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = PerformanceMonitor(cache_dir=tmpdir)
            adjuster = AdaptiveAdjuster(cache_dir=tmpdir, adaptation_rate=0.15)
            
            for league in ['la-liga', 'premier-league']:
                for i in range(50):
                    conf = 0.5 + (i % 10) * 0.05
                    outcome = 1.0 if (conf > 0.65 and i % 3 != 0) else 0.0
                    monitor.record_prediction(league, 'xg', conf, outcome)
            
            metrics = monitor.get_system_metrics()
            
            for league in ['la-liga', 'premier-league']:
                league_perf = monitor.get_league_performance(league)
                adjuster.adapt_league_factors({league: league_perf})
            
            adjuster.adapt_confidence_scale(metrics['drift_severity'], metrics['overall_accuracy'])
            
            assert metrics['total_predictions'] == 100
            assert 0.0 <= adjuster.get_confidence_scale() <= 2.0
    
    def test_full_workflow(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = PerformanceMonitor(cache_dir=tmpdir)
            adjuster = AdaptiveAdjuster(cache_dir=tmpdir)
            
            # Simulate real workflow
            for league in ['la-liga', 'bundesliga', 'serie-a']:
                for match in range(30):
                    conf = 0.65 + (match % 5) * 0.02
                    outcome = 1.0 if match < 20 else 0.0
                    monitor.record_prediction(league, 'xg', conf, outcome)
            
            # Get all metrics
            metrics = monitor.get_system_metrics()
            all_leagues = ['la-liga', 'bundesliga', 'serie-a']
            
            # Adapt all factors
            for league in all_leagues:
                stats = monitor.get_league_performance(league)
                adjuster.adapt_league_factors({league: stats})
            
            adjuster.adapt_confidence_scale(metrics['drift_severity'], metrics['overall_accuracy'])
            
            # Verify workflow completed
            assert monitor.system_metrics['total_predictions'] == 90
            assert all(league in monitor.league_performance for league in all_leagues)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
