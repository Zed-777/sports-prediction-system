#!/usr/bin/env python3
"""
Integration test for all 7 enhancement phases.
Tests the complete prediction pipeline with sample match data.
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestPhaseIntegration:
    """Test all 7 enhancement phases working together."""

    @pytest.fixture
    def predictor(self):
        """Create an EnhancedPredictor instance."""
        from enhanced_predictor import EnhancedPredictor

        return EnhancedPredictor("test_key")

    @pytest.fixture
    def sample_match(self):
        """Sample match data for testing."""
        return {
            "homeTeam": {"name": "Manchester City", "shortName": "MCI"},
            "awayTeam": {"name": "Liverpool", "shortName": "LIV"},
            "utcDate": "2025-01-20T15:00:00Z",
            "competition": {"name": "Premier League", "code": "PL"},
            "odds": {"home": 2.10, "draw": 3.50, "away": 3.20},
            "home_missing_players": ["Erling Haaland"],
            "away_missing_players": [],
        }

    def test_phase1_quick_wins_loaded(self, predictor):
        """Test Phase 1 - Quick Wins module is loaded."""
        assert predictor.prediction_enhancer is not None
        # Check for the actual method name
        assert hasattr(predictor.prediction_enhancer, "enhance_prediction")

    def test_phase2_xg_integration_loaded(self, predictor):
        """Test Phase 2 - xG Integration module is loaded."""
        assert predictor.xg_adjuster is not None
        assert hasattr(predictor.xg_adjuster, "adjust_prediction")

    def test_phase3_model_improvements_loaded(self, predictor):
        """Test Phase 3 - Model Improvements module is loaded."""
        assert predictor.model_enhancement_suite is not None
        assert hasattr(predictor.model_enhancement_suite, "enhance_prediction")

    def test_phase4_advanced_predictions_loaded(self, predictor):
        """Test Phase 4 - Advanced Predictions module is loaded."""
        assert predictor.advanced_predictions is not None
        # AdvancedPredictionSuite wraps BTTS via .btts attribute
        assert hasattr(predictor.advanced_predictions, "btts")
        assert hasattr(predictor.advanced_predictions, "full_prediction")

    def test_phase5_advanced_stats_loaded(self, predictor):
        """Test Phase 5 - Advanced Stats module is loaded."""
        assert predictor.advanced_stats is not None
        # AdvancedStatsAnalyzer has full_analysis method
        assert hasattr(predictor.advanced_stats, "full_analysis")

    def test_phase6_odds_movement_loaded(self, predictor):
        """Test Phase 6 - Odds Movement module is loaded."""
        assert predictor.odds_tracker is not None
        assert hasattr(predictor.odds_tracker, "record_and_analyze")

    def test_phase7_player_impact_loaded(self, predictor):
        """Test Phase 7 - Player Impact module is loaded."""
        assert predictor.player_impact is not None
        assert hasattr(predictor.player_impact, "analyze_match_impact")

    def test_all_phases_count(self, predictor):
        """Test that all 7 phases are loaded."""
        phases = [
            predictor.prediction_enhancer,
            predictor.xg_adjuster,
            predictor.model_enhancement_suite,
            predictor.advanced_predictions,
            predictor.advanced_stats,
            predictor.odds_tracker,
            predictor.player_impact,
        ]
        loaded = sum(1 for p in phases if p is not None)
        assert loaded == 7, f"Expected 7 phases, got {loaded}"


class TestModuleImports:
    """Test that all 10 enhancement modules can be imported."""

    def test_prediction_enhancements_import(self):
        """Test prediction_enhancements module imports."""
        from app.models.prediction_enhancements import PredictionEnhancer

        enhancer = PredictionEnhancer()
        assert enhancer is not None

    def test_prediction_tracker_import(self):
        """Test prediction_tracker module imports."""
        from app.models.prediction_tracker import PredictionTracker
        import tempfile
        import os

        # Use a temp file for SQLite
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            tracker = PredictionTracker(db_path)
            assert tracker is not None

    def test_backtesting_import(self):
        """Test backtesting module imports."""
        from app.models.backtesting import BacktestingFramework

        framework = BacktestingFramework()
        assert framework is not None

    def test_xg_integration_import(self):
        """Test xg_integration module imports."""
        from app.models.xg_integration import XGPredictionAdjuster

        adjuster = XGPredictionAdjuster()
        assert adjuster is not None

    def test_model_improvements_import(self):
        """Test model_improvements module imports."""
        from app.models.model_improvements import ModelEnhancementSuite

        suite = ModelEnhancementSuite()
        assert suite is not None

    def test_advanced_predictions_import(self):
        """Test advanced_predictions module imports."""
        from app.models.advanced_predictions import AdvancedPredictionSuite

        suite = AdvancedPredictionSuite()
        assert suite is not None

    def test_advanced_stats_import(self):
        """Test advanced_stats module imports."""
        from app.models.advanced_stats import AdvancedStatsAnalyzer

        analyzer = AdvancedStatsAnalyzer()
        assert analyzer is not None

    def test_odds_movement_import(self):
        """Test odds_movement module imports."""
        from app.models.odds_movement import OddsIntegrationSuite

        suite = OddsIntegrationSuite()
        assert suite is not None

    def test_ab_testing_import(self):
        """Test ab_testing module imports."""
        from app.models.ab_testing import ABTestingFramework

        framework = ABTestingFramework()
        assert framework is not None

    def test_player_impact_import(self):
        """Test player_impact module imports."""
        from app.models.player_impact import PlayerImpactSuite

        suite = PlayerImpactSuite()
        assert suite is not None


class TestEnhancementFeatures:
    """Test specific enhancement features work correctly."""

    def test_overconfidence_capping(self):
        """Test CC-005: Overconfidence capping works."""
        from app.models.prediction_enhancements import ConfidenceCapper

        capper = ConfidenceCapper()

        # High probability should be capped - returns tuple (home, draw, away)
        capped = capper.cap_probabilities(0.90, 0.05, 0.05)
        assert capped[0] < 0.90, "90% should be capped lower"
        assert capped[0] >= 0.70, "Should not cap too aggressively"

    def test_btts_prediction(self):
        """Test NF-004: BTTS prediction."""
        from app.models.advanced_predictions import BTTSPredictor

        predictor = BTTSPredictor()

        result = predictor.predict_btts(
            expected_home_goals=1.8, expected_away_goals=1.2
        )
        # Check for actual key names in result
        assert "btts_yes_probability" in result or "btts_yes" in result
        assert "btts_no_probability" in result or "btts_no" in result

    def test_over_under_prediction(self):
        """Test NF-005: Over/Under lines."""
        from app.models.advanced_predictions import OverUnderPredictor

        predictor = OverUnderPredictor()

        result = predictor.predict_over_under(
            expected_home_goals=1.5, expected_away_goals=1.0
        )
        # Check result has data
        assert result is not None
        assert len(result) > 0

    def test_player_impact_calculation(self):
        """Test DQ-002: Player impact scoring."""
        from app.models.player_impact import PlayerImpactSuite

        suite = PlayerImpactSuite()

        # Register a key player with correct signature
        suite.register_player(
            player_id="haaland_001",
            player_name="Erling Haaland",
            team_id="mci_001",
            team_name="Manchester City",
            position="FWD",
            stats={
                "goals": 25,
                "assists": 5,
                "minutes": 2500,
                "xg": 22.0,
                "matches": 30,
            },
        )

        # Analyze impact when missing with correct signature
        result = suite.analyze_match_impact(
            home_team_id="mci_001",
            home_team_name="Manchester City",
            away_team_id="liv_001",
            away_team_name="Liverpool",
            home_expected_goals=2.0,
            away_expected_goals=1.5,
            home_prob=0.45,
            draw_prob=0.28,
            away_prob=0.27,
            home_unavailable=[{"player_id": "haaland_001", "name": "Erling Haaland"}],
            away_unavailable=[],
        )

        assert "home_impact" in result
        assert "analysis_applied" in result

    def test_odds_movement_tracking(self):
        """Test RT-001: Odds movement tracking."""
        from app.models.odds_movement import OddsIntegrationSuite

        suite = OddsIntegrationSuite()

        result = suite.record_and_analyze(
            match_id="test_match_001",
            home_team="Man City",
            away_team="Liverpool",
            home_odds=2.10,
            draw_odds=3.50,
            away_odds=3.20,
            home_prob=0.45,
            draw_prob=0.28,
            away_prob=0.27,
        )

        assert "adjusted_home_prob" in result
        assert "market_implied" in result
        assert "movement" in result


class TestPredictionPipeline:
    """Test the complete prediction pipeline."""

    def test_enhanced_prediction_format(self):
        """Test that enhanced predictions have expected format."""
        from enhanced_predictor import EnhancedPredictor

        predictor = EnhancedPredictor("test_key")

        # Create minimal mock match data with required fields
        match = {
            "homeTeam": {"id": 1, "name": "Test Home", "shortName": "TH"},
            "awayTeam": {"id": 2, "name": "Test Away", "shortName": "TA"},
            "utcDate": "2025-01-20T15:00:00Z",
            "competition": {"name": "Test League", "code": "PL"},
        }

        # Get base prediction using enhanced_prediction method with competition_code
        result = predictor.enhanced_prediction(match, competition_code="PL")

        # Check required fields exist
        assert "home_win_prob" in result
        assert "draw_prob" in result
        assert "away_win_prob" in result

        # Probabilities should sum to ~100 (percentages) or ~1.0 (decimals)
        total = result["home_win_prob"] + result["draw_prob"] + result["away_win_prob"]
        # Accept either percentage format (95-105) or decimal format (0.95-1.05)
        assert (95 <= total <= 105) or (0.95 <= total <= 1.05), (
            f"Probabilities sum to {total}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
