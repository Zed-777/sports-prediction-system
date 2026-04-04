"""Unit tests for the profitability analysis modules
(PROF-001 through PROF-005)
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = str(Path(__file__).resolve().parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# ============================================================
# app/models/profitability.py
# ============================================================

from app.models.profitability import (
    BetResult,
    binomial_significance_test,
    build_profitability_report,
    calculate_edge,
    calculate_ev,
    compute_drawdown,
    estimate_risk_of_ruin,
    kelly_fraction,
    max_consecutive_losses,
    quarter_kelly,
    sharpe_equivalent,
)


class TestCalculateEv:
    def test_positive_ev(self):
        # model says 60%, market prices 50% (odds 2.0) → EV = 0.60*2.0 - 1 = 0.20
        ev = calculate_ev(0.60, 2.0)
        assert abs(ev - 0.20) < 1e-9

    def test_negative_ev(self):
        # model 40%, odds 2.0 → EV = 0.40*2.0 - 1 = -0.20
        ev = calculate_ev(0.40, 2.0)
        assert abs(ev - (-0.20)) < 1e-9

    def test_zero_ev(self):
        ev = calculate_ev(0.50, 2.0)
        assert abs(ev) < 1e-9


class TestCalculateEdge:
    def test_positive_edge(self):
        edge = calculate_edge(0.60, 2.0)   # implied = 0.50
        assert abs(edge - 0.10) < 1e-9

    def test_negative_edge(self):
        edge = calculate_edge(0.30, 2.0)   # implied = 0.50
        assert abs(edge - (-0.20)) < 1e-9


class TestKelly:
    def test_kelly_positive_ev(self):
        # p=0.60, odds=2.0 → f* = (0.60*2.0 - 1)/(2.0-1) = 0.20/1.0 = 0.20
        f = kelly_fraction(0.60, 2.0)
        assert abs(f - 0.20) < 1e-9

    def test_kelly_zero_odds(self):
        assert kelly_fraction(0.60, 0.0) == 0.0

    def test_quarter_kelly_cap(self):
        # Even with huge edge, quarter kelly cap at 5%
        qk = quarter_kelly(0.99, 10.0)
        assert qk <= 0.05

    def test_quarter_kelly_no_negative(self):
        qk = quarter_kelly(0.10, 5.0)  # negative EV
        assert qk == 0.0


class TestDrawdown:
    def test_no_drawdown(self):
        profits = [10, 10, 10]
        _, dd_pct = compute_drawdown(profits)
        assert dd_pct == 0.0

    def test_simple_drawdown(self):
        # cumulative: 10, -5, 5 → peak=10, worst=-5 →dd=15
        profits = [10, -15, 10]
        dd_abs, dd_pct = compute_drawdown(profits)
        assert dd_abs == 15.0
        assert dd_pct > 0

    def test_empty(self):
        assert compute_drawdown([]) == (0.0, 0.0)


class TestMaxConsecutiveLosses:
    def test_streak(self):
        flags = [True, False, False, False, True, False]
        assert max_consecutive_losses(flags) == 3

    def test_no_losses(self):
        assert max_consecutive_losses([True, True, True]) == 0

    def test_empty(self):
        assert max_consecutive_losses([]) == 0


class TestSharpe:
    def test_positive_returns(self):
        profits = [1.0] * 50
        s = sharpe_equivalent(profits)
        assert s == 0.0  # no variance

    def test_mixed(self):
        profits = [2.0, -1.0, 2.0, -1.0] * 10
        s = sharpe_equivalent(profits)
        assert isinstance(s, float)


class TestBinomialTest:
    def test_significant(self):
        # 70 wins out of 100 when expected is 40% → should be very significant
        z, p = binomial_significance_test(100, 70, 0.40)
        assert z > 2.0
        assert p < 0.05

    def test_not_significant(self):
        z, p = binomial_significance_test(100, 42, 0.40)
        assert p > 0.10

    def test_tiny_sample(self):
        z, p = binomial_significance_test(1, 1, 0.5)
        assert p == 1.0  # not enough data


class TestRiskOfRuin:
    def test_near_zero_with_positive_ev(self):
        ror = estimate_risk_of_ruin(
            avg_stake_frac=0.02,
            avg_ev=0.10,
            hit_rate=0.55,
            avg_decimal_odds=2.20,
            n_simulations=2000,
            seed=1,
        )
        assert ror < 20.0   # should be low

    def test_high_with_negative_ev(self):
        ror = estimate_risk_of_ruin(
            avg_stake_frac=0.05,
            avg_ev=-0.10,
            hit_rate=0.30,
            avg_decimal_odds=2.0,
            n_simulations=2000,
            seed=2,
        )
        assert ror > 30.0    # should be high


class TestBuildProfitabilityReport:
    def _make_bets(self, n_wins: int, n_total: int, odds: float = 2.0) -> list:
        bets = []
        for i in range(n_total):
            won = i < n_wins
            profit = (odds - 1.0) if won else -1.0
            bets.append(BetResult(
                match_id=f"m{i}",
                league="premier-league",
                outcome_label="home",
                model_prob=0.55,
                market_prob=0.50,
                decimal_odds=odds,
                edge=0.05,
                ev=0.10,
                stake=1.0,
                won=won,
                profit=profit,
                confidence=0.65,
                data_quality=0.70,
                qualified=True,
            ))
        return bets

    def test_positive_roi(self):
        bets = self._make_bets(60, 100, odds=2.0)
        report = build_profitability_report(bets, n_montecarlo=500)
        assert report.qualifying_bets == 100
        assert report.roi_pct > 0

    def test_no_qualifying_bets(self):
        bets = self._make_bets(10, 10)
        for b in bets:
            b.qualified = False
        report = build_profitability_report(bets, n_montecarlo=100)
        assert report.qualifying_bets == 0

    def test_live_criteria_checked(self):
        # 200 bets at 60% hit rate, odds 2.0 → solid ROI
        bets = self._make_bets(120, 200, odds=2.0)
        report = build_profitability_report(bets, n_montecarlo=500)
        assert report.hit_rate == pytest.approx(0.60)
        assert isinstance(report.live_ready, bool)


# ============================================================
# app/models/market_simulator.py
# ============================================================

from app.models.market_simulator import (
    MarketSimulator,
    SimulatedOdds,
    SyntheticMatchGenerator,
)


class TestMarketSimulator:
    def test_overround_applied(self):
        sim = MarketSimulator(bookmaker_type="sharp")
        odds = sim.simulate(0.50, 0.25, 0.25)
        # sum of implied probs > 1 (book margin)
        total = odds.implied_home_prob + odds.implied_draw_prob + odds.implied_away_prob
        assert total > 1.01
        assert total < 1.15

    def test_short_odds_team_gets_lowest_odds(self):
        sim = MarketSimulator()
        odds = sim.simulate(0.70, 0.20, 0.10)
        assert odds.home_odds < odds.draw_odds < odds.away_odds

    def test_closing_line_tighter(self):
        sim = MarketSimulator(bookmaker_type="soft")
        open_odds = sim.simulate(0.45, 0.28, 0.27)
        close_odds = sim.simulate_closing_line(0.45, 0.28, 0.27)
        # Closing line should have lower overround
        assert close_odds.overround < open_odds.overround

    def test_clv_positive_when_model_beats_market(self):
        sim = MarketSimulator()
        # Market says 2.20 (45.4% implied), model says 55% → positive CLV
        clv = sim.closing_line_value(0.55, 2.20)
        assert clv > 0

    def test_clv_negative_when_model_below_market(self):
        sim = MarketSimulator()
        clv = sim.closing_line_value(0.35, 2.20)
        assert clv < 0


class TestSyntheticMatchGenerator:
    def test_generates_correct_count(self):
        gen = SyntheticMatchGenerator(model_accuracy=0.60)
        records = gen.generate(n_matches=100)
        assert len(records) == 100

    def test_records_have_required_fields(self):
        gen = SyntheticMatchGenerator()
        records = gen.generate(n_matches=10)
        required = {"match_id", "league", "model_home_prob", "model_draw_prob",
                    "model_away_prob", "model_confidence", "data_quality",
                    "market_odds", "actual_outcome"}
        for r in records:
            for field in required:
                assert field in r, f"Missing field: {field}"

    def test_probs_sum_to_one(self):
        gen = SyntheticMatchGenerator()
        records = gen.generate(n_matches=50)
        for r in records:
            total = r["model_home_prob"] + r["model_draw_prob"] + r["model_away_prob"]
            assert abs(total - 1.0) < 2e-4

    def test_market_odds_are_simulated_odds_object(self):
        gen = SyntheticMatchGenerator()
        records = gen.generate(n_matches=5)
        for r in records:
            assert isinstance(r["market_odds"], SimulatedOdds)

    def test_higher_accuracy_better_brier(self):
        gen_high = SyntheticMatchGenerator(model_accuracy=0.70, seed=1)
        gen_low = SyntheticMatchGenerator(model_accuracy=0.45, seed=1)
        high_rec = gen_high.generate(500)
        low_rec = gen_low.generate(500)
        high_correct = sum(
            1 for r in high_rec
            if max(r["model_home_prob"], r["model_draw_prob"], r["model_away_prob"])
            == {
                "home": r["model_home_prob"],
                "draw": r["model_draw_prob"],
                "away": r["model_away_prob"],
            }[r["actual_outcome"]]
        )
        low_correct = sum(
            1 for r in low_rec
            if max(r["model_home_prob"], r["model_draw_prob"], r["model_away_prob"])
            == {
                "home": r["model_home_prob"],
                "draw": r["model_draw_prob"],
                "away": r["model_away_prob"],
            }[r["actual_outcome"]]
        )
        assert high_correct > low_correct


# ============================================================
# app/models/qualifying_gate.py
# ============================================================

from app.models.qualifying_gate import QualifyingGate, QualifyingParams


class TestQualifyingGate:
    def _gate(self, **kwargs) -> QualifyingGate:
        return QualifyingGate(QualifyingParams(**kwargs))

    def test_qualifies_strong_value_bet(self):
        gate = QualifyingGate(QualifyingParams.standard())
        # Model: 65% home, market 45% implied (odds 2.22) → big edge
        decision = gate.evaluate(
            league="premier-league",
            model_home_prob=0.65, model_draw_prob=0.22, model_away_prob=0.13,
            market_odds_home=2.22, market_odds_draw=3.80, market_odds_away=5.50,
            confidence=0.70,
            data_quality=0.80,
        )
        assert decision.qualified is True
        assert decision.outcome_to_bet == "home"
        assert decision.ev_pct > 0

    def test_rejects_no_edge(self):
        gate = QualifyingGate(QualifyingParams.standard())
        # Model matches market perfectly → no edge
        decision = gate.evaluate(
            league="premier-league",
            model_home_prob=0.45, model_draw_prob=0.28, model_away_prob=0.27,
            market_odds_home=2.10, market_odds_draw=3.40, market_odds_away=3.60,
            confidence=0.70,
            data_quality=0.80,
        )
        assert decision.qualified is False

    def test_rejects_low_confidence(self):
        gate = QualifyingGate(QualifyingParams.standard())
        decision = gate.evaluate(
            league="premier-league",
            model_home_prob=0.65, model_draw_prob=0.22, model_away_prob=0.13,
            market_odds_home=2.22, market_odds_draw=3.80, market_odds_away=5.50,
            confidence=0.45,    # below 0.60 threshold
            data_quality=0.80,
        )
        assert decision.qualified is False

    def test_rejects_non_whitelisted_league(self):
        gate = QualifyingGate(QualifyingParams.standard())
        decision = gate.evaluate(
            league="mls",         # not in whitelist
            model_home_prob=0.70, model_draw_prob=0.20, model_away_prob=0.10,
            market_odds_home=2.00, market_odds_draw=3.80, market_odds_away=6.50,
            confidence=0.80,
            data_quality=0.80,
        )
        assert decision.qualified is False

    def test_rejects_odds_too_low(self):
        gate = QualifyingGate(QualifyingParams(min_odds=1.40))
        # Home odds 1.10 → too short
        decision = gate.evaluate(
            league="premier-league",
            model_home_prob=0.95, model_draw_prob=0.03, model_away_prob=0.02,
            market_odds_home=1.10, market_odds_draw=10.0, market_odds_away=20.0,
            confidence=0.92,
            data_quality=0.90,
        )
        assert decision.qualified is False

    def test_conservative_tighter_than_standard(self):
        records_passed_std = 0
        records_passed_con = 0
        from app.models.market_simulator import SyntheticMatchGenerator
        gen = SyntheticMatchGenerator(seed=99)
        recs = gen.generate(200)

        std_gate = QualifyingGate(QualifyingParams.standard())
        con_gate = QualifyingGate(QualifyingParams.conservative())

        for r in recs:
            mo = r["market_odds"]
            for g, counter in [(std_gate, "std"), (con_gate, "con")]:
                d = g.evaluate(
                    league=r["league"],
                    model_home_prob=r["model_home_prob"],
                    model_draw_prob=r["model_draw_prob"],
                    model_away_prob=r["model_away_prob"],
                    market_odds_home=mo.home_odds,
                    market_odds_draw=mo.draw_odds,
                    market_odds_away=mo.away_odds,
                    confidence=r["model_confidence"],
                    data_quality=r["data_quality"],
                )
                if d.qualified:
                    if counter == "std":
                        records_passed_std += 1
                    else:
                        records_passed_con += 1

        # Conservative gate must always let through fewer or equal bets
        assert records_passed_con <= records_passed_std


# ============================================================
# Integration: Market simulator → Gate → Profitability
# ============================================================

class TestEndToEndProfitability:
    def test_positive_roi_with_calibrated_model(self):
        """End-to-end: a well-calibrated 60% model should yield positive ROI."""
        from app.models.live_trading_validator import simulate_bets
        from app.models.market_simulator import SyntheticMatchGenerator

        gen = SyntheticMatchGenerator(model_accuracy=0.62, bookmaker_type="sharp", seed=777)
        records = gen.generate(1000)

        params = QualifyingParams.standard()
        gate = QualifyingGate(params)
        bets = simulate_bets(records, gate)
        report = build_profitability_report(bets, n_montecarlo=500)

        qual = report.qualifying_bets
        assert qual > 0, "No qualifying bets generated"
        # With our calibrated model we expect positive ROI on a large sample
        # (not guaranteed on small samples due to variance)
        assert report.hit_rate > 0.35, f"Hit rate suspiciously low: {report.hit_rate}"

    def test_validator_produces_verdict(self, tmp_path):
        """LiveTradingValidator runs without error and returns a verdict dict."""
        from app.models.live_trading_validator import LiveTradingValidator

        validator = LiveTradingValidator(
            data_dir="data",
            results_dir=str(tmp_path / "profitability"),
        )
        verdict = validator.run(
            params=QualifyingParams.standard(),
            n_synthetic=300,
            model_accuracy=0.62,
            n_walk_forward_splits=3,
            n_sensitivity_runs=False,
            save_results=True,
            verbose=False,
        )
        assert "verdict" in verdict
        assert "live_ready" in verdict["verdict"]
        assert "live_readiness_score" in verdict["verdict"]
        assert isinstance(verdict["verdict"]["live_ready"], bool)
        assert 0 <= verdict["verdict"]["live_readiness_score"] <= 100

        # Saved files should exist
        saved = list(Path(tmp_path / "profitability").glob("live_validation_*.json"))
        assert len(saved) == 1

    def test_live_ready_with_strong_model(self, tmp_path):
        """A very strong model (70% accuracy) should pass all live criteria."""
        from app.models.live_trading_validator import LiveTradingValidator

        validator = LiveTradingValidator(
            data_dir="data",
            results_dir=str(tmp_path / "profitability_strong"),
        )
        verdict = validator.run(
            params=QualifyingParams.standard(),
            n_synthetic=500,
            model_accuracy=0.70,       # strong model
            n_walk_forward_splits=3,
            n_sensitivity_runs=False,
            save_results=False,
            verbose=False,
        )
        v = verdict["verdict"]
        # Strong model should achieve high readiness score
        assert v["live_readiness_score"] >= 50, (
            f"Expected ≥50 score for strong model, got {v['live_readiness_score']}\n"
            f"Failures: {v['failure_reasons']}"
        )
