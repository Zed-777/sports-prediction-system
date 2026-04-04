"""Tests for app/models/ensemble_disagreement.py (TODO #12)
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from app.models.ensemble_disagreement import (
    DisagreementLevel,
    DisagreementReport,
    EnsembleDisagreementDetector,
    _entropy,
    _js_divergence,
    disagreement_from_named,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pred(h: float, d: float, a: float) -> dict:
    return {"home_win_prob": h, "draw_prob": d, "away_win_prob": a}


def _perfect_agreement():
    """Three models returning identical predictions."""
    return [_pred(0.55, 0.25, 0.20)] * 3


def _total_disagreement():
    """Each model predicts a different winner."""
    return [
        _pred(0.70, 0.20, 0.10),  # model A: home wins
        _pred(0.20, 0.60, 0.20),  # model B: draw
        _pred(0.15, 0.20, 0.65),  # model C: away wins
    ]


def _moderate_disagreement():
    """Models agree on winner but spread varies."""
    return [
        _pred(0.55, 0.25, 0.20),
        _pred(0.48, 0.30, 0.22),
        _pred(0.60, 0.22, 0.18),
    ]


# ---------------------------------------------------------------------------
# Math helpers
# ---------------------------------------------------------------------------


class TestEntropy:
    def test_uniform_distribution_maximum_entropy(self):
        # Uniform over 3 → H = ln(3)
        e = _entropy(np.array([1 / 3, 1 / 3, 1 / 3]))
        assert e == pytest.approx(math.log(3), rel=1e-6)

    def test_certain_distribution_zero_entropy(self):
        e = _entropy(np.array([1.0, 0.0, 0.0]))
        assert e == pytest.approx(0.0, abs=1e-6)


class TestJSDivergence:
    def test_identical_distributions_zero(self):
        p = np.array([0.5, 0.3, 0.2])
        assert _js_divergence(p, p) == pytest.approx(0.0, abs=1e-9)

    def test_opposite_distributions_max(self):
        p = np.array([1.0, 0.0, 0.0])
        q = np.array([0.0, 1.0, 0.0])
        jsd = _js_divergence(p, q)
        # Max JSD = ln(2) ≈ 0.693
        assert 0.0 < jsd <= math.log(2) + 1e-9

    def test_symmetric(self):
        p = np.array([0.6, 0.3, 0.1])
        q = np.array([0.2, 0.5, 0.3])
        assert _js_divergence(p, q) == pytest.approx(_js_divergence(q, p), rel=1e-9)

    def test_positive(self):
        p = np.array([0.5, 0.3, 0.2])
        q = np.array([0.4, 0.4, 0.2])
        assert _js_divergence(p, q) >= 0.0


# ---------------------------------------------------------------------------
# EnsembleDisagreementDetector — trivial cases
# ---------------------------------------------------------------------------


class TestTrivialCases:
    def test_empty_list(self):
        det = EnsembleDisagreementDetector()
        report = det.analyse([])
        assert report.n_models == 0
        assert report.level == DisagreementLevel.UNANIMOUS
        assert report.confidence_penalty == pytest.approx(0.0)

    def test_single_model(self):
        det = EnsembleDisagreementDetector()
        report = det.analyse([_pred(0.55, 0.25, 0.20)])
        assert report.n_models == 1
        assert report.level == DisagreementLevel.UNANIMOUS
        assert report.winner_agreement is True


# ---------------------------------------------------------------------------
# EnsembleDisagreementDetector — agreement scenarios
# ---------------------------------------------------------------------------


class TestPerfectAgreement:
    def test_identical_models_unanimous(self):
        det = EnsembleDisagreementDetector()
        report = det.analyse(_perfect_agreement())
        assert report.n_models == 3
        assert report.winner_agreement is True
        assert report.level in (DisagreementLevel.UNANIMOUS, DisagreementLevel.LOW)
        assert report.confidence_penalty < 0.05
        assert report.composite_score < 0.15

    def test_mean_probs_correct(self):
        det = EnsembleDisagreementDetector()
        report = det.analyse(_perfect_agreement())
        assert report.mean_probs["home_win_prob"] == pytest.approx(0.55, abs=1e-6)
        assert report.mean_probs["draw_prob"] == pytest.approx(0.25, abs=1e-6)


class TestTotalDisagreement:
    def test_each_model_different_winner(self):
        det = EnsembleDisagreementDetector()
        report = det.analyse(_total_disagreement())
        assert not report.winner_agreement
        assert report.winner_consensus_pct == pytest.approx(1 / 3, abs=1e-6)
        assert report.level in (DisagreementLevel.HIGH, DisagreementLevel.SEVERE)
        assert report.confidence_penalty >= 0.10

    def test_composite_score_high(self):
        det = EnsembleDisagreementDetector()
        report = det.analyse(_total_disagreement())
        assert report.composite_score > 0.40


class TestModerateDisagreement:
    def test_agrees_on_winner_but_moderate_level(self):
        det = EnsembleDisagreementDetector()
        report = det.analyse(_moderate_disagreement())
        assert report.majority_winner == "home_win_prob"
        # Composite should be lower than total_disagreement
        report_total = det.analyse(_total_disagreement())
        assert report.composite_score < report_total.composite_score


# ---------------------------------------------------------------------------
# Specific metrics
# ---------------------------------------------------------------------------


class TestMetrics:
    def test_winner_consensus_pct_two_of_three(self):
        preds = [
            _pred(0.60, 0.25, 0.15),  # home
            _pred(0.55, 0.25, 0.20),  # home
            _pred(0.30, 0.25, 0.45),  # away
        ]
        det = EnsembleDisagreementDetector()
        report = det.analyse(preds)
        assert not report.winner_agreement
        assert report.majority_winner == "home_win_prob"
        assert report.winner_consensus_pct == pytest.approx(2 / 3, abs=1e-6)

    def test_mean_js_zero_for_identical_models(self):
        det = EnsembleDisagreementDetector()
        report = det.analyse(_perfect_agreement())
        assert report.mean_js_divergence == pytest.approx(0.0, abs=1e-9)

    def test_max_pairwise_l1_zero_for_identical(self):
        det = EnsembleDisagreementDetector()
        report = det.analyse(_perfect_agreement())
        assert report.max_pairwise_l1 == pytest.approx(0.0, abs=1e-9)

    def test_max_pairwise_l1_positive(self):
        det = EnsembleDisagreementDetector()
        report = det.analyse(_total_disagreement())
        assert report.max_pairwise_l1 > 0

    def test_variances_zero_for_identical(self):
        det = EnsembleDisagreementDetector()
        report = det.analyse(_perfect_agreement())
        assert all(v == pytest.approx(0.0, abs=1e-9) for v in report.variances.values())


# ---------------------------------------------------------------------------
# apply_to_prediction
# ---------------------------------------------------------------------------


class TestApplyToPrediction:
    def test_confidence_reduced_by_penalty(self):
        det = EnsembleDisagreementDetector()
        base = {"home_win_prob": 0.55, "draw_prob": 0.25, "away_win_prob": 0.20,
                "confidence": 0.72}
        result = det.apply_to_prediction(base, _total_disagreement())
        assert result["confidence"] < 0.72
        assert "ensemble_disagreement" in result

    def test_no_confidence_key_no_crash(self):
        det = EnsembleDisagreementDetector()
        base = {"home_win_prob": 0.55, "draw_prob": 0.25, "away_win_prob": 0.20}
        result = det.apply_to_prediction(base, _total_disagreement())
        assert "ensemble_disagreement" in result
        assert "confidence" not in result

    def test_ensemble_disagreement_fields(self):
        det = EnsembleDisagreementDetector()
        base = {"confidence": 0.70}
        result = det.apply_to_prediction(base, _moderate_disagreement())
        ed = result["ensemble_disagreement"]
        assert "level" in ed
        assert "composite_score" in ed
        assert "n_models" in ed
        assert "winner_agreement" in ed

    def test_confidence_not_negative(self):
        det = EnsembleDisagreementDetector(
            custom_penalties={DisagreementLevel.SEVERE: 0.99},
        )
        base = {"confidence": 0.20}
        result = det.apply_to_prediction(base, _total_disagreement())
        assert result.get("confidence", 0) >= 0.0


# ---------------------------------------------------------------------------
# analyse_named
# ---------------------------------------------------------------------------


class TestAnalyseNamed:
    def test_analyse_named(self):
        det = EnsembleDisagreementDetector()
        named = {
            "poisson": _pred(0.55, 0.25, 0.20),
            "elo":     _pred(0.50, 0.28, 0.22),
        }
        report = det.analyse_named(named)
        assert report.n_models == 2

    def test_disagreement_from_named_helper(self):
        named = {
            "poisson": _pred(0.55, 0.25, 0.20),
            "xg":      _pred(0.40, 0.30, 0.30),
        }
        report = disagreement_from_named(named)
        assert isinstance(report, DisagreementReport)


# ---------------------------------------------------------------------------
# Report structure
# ---------------------------------------------------------------------------


class TestReportStructure:
    def test_summary_string(self):
        det = EnsembleDisagreementDetector()
        report = det.analyse(_moderate_disagreement())
        s = report.summary()
        assert "models" in s
        assert "composite=" in s

    def test_all_levels_covered(self):
        """Quickly exercise all DisagreementLevel values."""
        for level in DisagreementLevel:
            assert level.confidence_penalty >= 0.0
            assert isinstance(level.should_block, bool)

    def test_severe_level_blocks(self):
        assert DisagreementLevel.SEVERE.should_block is True

    def test_moderate_level_does_not_block(self):
        assert DisagreementLevel.MODERATE.should_block is False

    def test_normalised_probs_dont_crash(self):
        """Non-normalised input should work fine."""
        det = EnsembleDisagreementDetector()
        preds = [
            {"home_win_prob": 2.0, "draw_prob": 1.0, "away_win_prob": 1.0},  # sums to 4
            {"home_win_prob": 0.5, "draw_prob": 0.3, "away_win_prob": 0.2},
        ]
        report = det.analyse(preds)
        assert isinstance(report.composite_score, float)
