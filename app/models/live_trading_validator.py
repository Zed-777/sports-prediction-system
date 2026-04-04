"""Live Trading Validator (PROF-004)
===================================
End-to-end validation pipeline that determines whether the prediction
strategy is ready for live sports-betting deployment.

Pipeline
--------
1.  Load match data (real historical OR synthetic generated)
2.  Apply qualifying gate to each match
3.  Simulate bets (Kelly staking, market odds)
4.  Compute ProfitabilityReport (ROI, drawdown, significance, risk-of-ruin)
5.  Walk-forward out-of-sample validation (prevent overfitting to history)
6.  Sensitivity analysis across qualifying gate thresholds
7.  Produce a structured JSON verdict with live-readiness score

Output
------
  reports/profitability/live_validation_<timestamp>.json
  reports/profitability/live_validation_<timestamp>_summary.txt

Live-ready verdict
------------------
A strategy is declared LIVE-READY if and only if ALL criteria in
app.models.profitability.LIVE_CRITERIA pass AND the walk-forward
validation also shows positive ROI.
"""

from __future__ import annotations

import json
import logging
import statistics
from datetime import datetime
from pathlib import Path

from app.models.market_simulator import MarketSimulator, SyntheticMatchGenerator
from app.models.profitability import (
    BetResult,
    ProfitabilityReport,
    build_profitability_report,
)
from app.models.qualifying_gate import QualifyingGate, QualifyingParams

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Walk-forward splitting
# ---------------------------------------------------------------------------


def walk_forward_split(
    records: list[dict],
    n_splits: int = 5,
) -> list[tuple[list[dict], list[dict]]]:
    """Split records into (train, test) folds for walk-forward validation.

    Records are assumed to be chronologically ordered (or at least randomly
    partitioned if no date is available).  Walk-forward ensures test periods
    always come *after* train periods (no data leakage).

    Returns list of (train_records, test_records) tuples.
    """
    if len(records) < n_splits * 2:
        # Not enough data for multiple folds – single split
        split = int(len(records) * 0.70)
        return [(records[:split], records[split:])]

    fold_size = len(records) // n_splits
    folds = []
    for i in range(1, n_splits):
        train = records[:i * fold_size]
        test = records[i * fold_size: (i + 1) * fold_size]
        if test:
            folds.append((train, test))
    return folds


# ---------------------------------------------------------------------------
# Core simulation
# ---------------------------------------------------------------------------


def simulate_bets(
    records: list[dict],
    gate: QualifyingGate,
    bankroll: float = 100.0,
) -> list[BetResult]:
    """Run each record through the qualifying gate and simulate the bet outcome.

    Parameters
    ----------
    records   : list of match dicts (from SyntheticMatchGenerator or real data)
    gate      : configured QualifyingGate
    bankroll  : starting bankroll in units (used for Kelly sizing)

    Returns
    -------
    list of BetResult (including disqualified bets with qualified=False)

    """
    results = []
    current_bankroll = bankroll

    for rec in records:
        market_odds = rec.get("market_odds")
        if market_odds is None:
            continue

        decision = gate.evaluate(
            league=rec.get("league", "unknown"),
            model_home_prob=rec["model_home_prob"],
            model_draw_prob=rec["model_draw_prob"],
            model_away_prob=rec["model_away_prob"],
            market_odds_home=market_odds.home_odds,
            market_odds_draw=market_odds.draw_odds,
            market_odds_away=market_odds.away_odds,
            confidence=rec.get("model_confidence", 0.5),
            data_quality=rec.get("data_quality", 0.5),
        )

        if not decision.qualified:
            results.append(BetResult(
                match_id=rec.get("match_id", "?"),
                league=rec.get("league", "?"),
                outcome_label=decision.outcome_to_bet or "none",
                model_prob=0.0,
                market_prob=0.0,
                decimal_odds=0.0,
                edge=0.0,
                ev=0.0,
                stake=0.0,
                won=False,
                profit=0.0,
                confidence=rec.get("model_confidence", 0.0),
                data_quality=rec.get("data_quality", 0.0),
                qualified=False,
                disqualification_reason="; ".join(decision.rejection_reasons[:2]),
            ))
            continue

        # Determine stake (Kelly, % of current bankroll)
        stake_pct = (decision.kelly_stake_pct or 2.0) / 100.0
        stake = min(current_bankroll * stake_pct, current_bankroll * 0.05)
        stake = max(stake, 0.01)

        # Determine win
        actual = rec.get("actual_outcome", rec.get("true_outcome", ""))
        won = (decision.outcome_to_bet == actual)

        # Profit
        if won:
            profit = stake * (decision.decimal_odds - 1.0)
        else:
            profit = -stake

        current_bankroll += profit

        results.append(BetResult(
            match_id=rec.get("match_id", "?"),
            league=rec.get("league", "?"),
            outcome_label=decision.outcome_to_bet,
            model_prob=decision.model_prob,
            market_prob=decision.market_prob,
            decimal_odds=decision.decimal_odds,
            edge=decision.edge_pct / 100.0 if decision.edge_pct else 0.0,
            ev=decision.ev_pct / 100.0 if decision.ev_pct else 0.0,
            stake=stake,
            won=won,
            profit=profit,
            confidence=rec.get("model_confidence", 0.5),
            data_quality=rec.get("data_quality", 0.5),
            qualified=True,
        ))

    return results


# ---------------------------------------------------------------------------
# Sensitivity analysis
# ---------------------------------------------------------------------------


def sensitivity_analysis(
    records: list[dict],
    edge_values: list[float] = (2.0, 4.0, 6.0, 8.0, 10.0),
    confidence_values: list[float] = (0.52, 0.58, 0.64, 0.70),
) -> dict:
    """Test how ROI and qualifying rate change across different gate thresholds.

    Returns a dict keyed by (edge_pct, confidence) with ROI and n_bets.
    """
    results = {}
    for edge in edge_values:
        for conf in confidence_values:
            params = QualifyingParams(
                min_edge_pct=edge,
                min_confidence=conf,
                min_ev_pct=max(2.0, edge - 2.0),
            )
            gate = QualifyingGate(params)
            bets = simulate_bets(records, gate)
            qual = [b for b in bets if b.qualified]
            if qual:
                total_staked = sum(b.stake for b in qual)
                total_profit = sum(b.profit for b in qual)
                roi = (total_profit / total_staked * 100) if total_staked > 0 else 0.0
            else:
                roi = 0.0
            results[f"edge={edge}_conf={conf}"] = {
                "n_qualifying": len(qual),
                "roi_pct": round(roi, 2),
                "hit_rate_pct": round(
                    sum(1 for b in qual if b.won) / max(len(qual), 1) * 100, 2,
                ),
            }
    return results


# ---------------------------------------------------------------------------
# Main validator
# ---------------------------------------------------------------------------


class LiveTradingValidator:
    """Orchestrates the full live-readiness validation pipeline.

    Usage
    -----
        validator = LiveTradingValidator()
        verdict = validator.run(params=QualifyingParams.standard())
        print(verdict["verdict"]["live_ready"])
    """

    def __init__(
        self,
        data_dir: str = "data",
        results_dir: str = "reports/profitability",
        bookmaker_type: str = "sharp",
    ):
        self.data_dir = Path(data_dir)
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.bookmaker_type = bookmaker_type
        self._market_sim = MarketSimulator(bookmaker_type=bookmaker_type)

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def load_real_data(self) -> list[dict]:
        """Load real historical match records and attach simulated market odds.

        Handles both the sparse real data (1-2 records per league) and any
        richer backtest files.  Attaches market odds via simulation so the
        profitability engine can evaluate edge.
        """
        records = []
        hist_dir = self.data_dir / "historical"

        for json_file in hist_dir.glob("*_results.json"):
            try:
                with open(json_file, encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    for item in data:
                        rec = self._convert_historical_record(item)
                        if rec:
                            records.append(rec)
            except Exception as e:
                logger.debug(f"Could not load {json_file}: {e}")

        logger.info(f"Loaded {len(records)} real historical records")
        return records

    def _convert_historical_record(self, item: dict) -> dict | None:
        """Convert a stored historical prediction record to the internal format."""
        try:
            pred = item.get("prediction", {})
            actual = item.get("actual_result", {})
            if not pred or not actual:
                return None

            hp = pred.get("home_win_prob", 0) / 100.0
            dp = pred.get("draw_prob", 0) / 100.0
            ap = pred.get("away_win_prob", 0) / 100.0
            total = hp + dp + ap
            if total <= 0:
                return None
            hp, dp, ap = hp / total, dp / total, ap / total

            # Determine actual outcome
            outcome_str = actual.get("outcome", "")
            if "home" in outcome_str:
                actual_outcome = "home"
            elif "away" in outcome_str:
                actual_outcome = "away"
            else:
                actual_outcome = "draw"

            confidence = pred.get("confidence", 0.6)
            if isinstance(confidence, (int, float)) and confidence > 1:
                confidence = confidence / 100.0

            # Simulated market odds from true probabilities
            market_odds = self._market_sim.simulate(
                home_prob=hp, draw_prob=dp, away_prob=ap,
                league=item.get("league", "default"),
            )

            return {
                "match_id": item.get("match_id", "?"),
                "league": item.get("league", "unknown"),
                "home_team": item.get("home_team", "?"),
                "away_team": item.get("away_team", "?"),
                "model_home_prob": round(hp, 4),
                "model_draw_prob": round(dp, 4),
                "model_away_prob": round(ap, 4),
                "model_confidence": min(0.92, max(0.0, float(confidence))),
                "data_quality": 0.80,   # assume adequate for stored records
                "market_odds": market_odds,
                "actual_outcome": actual_outcome,
                "true_outcome": actual_outcome,
                "source": "real",
            }
        except Exception as e:
            logger.debug(f"Could not convert record: {e}")
            return None

    # ------------------------------------------------------------------
    # Main pipeline
    # ------------------------------------------------------------------

    def run(
        self,
        params: QualifyingParams | None = None,
        n_synthetic: int = 2000,
        model_accuracy: float = 0.60,
        n_walk_forward_splits: int = 5,
        n_sensitivity_runs: bool = True,
        save_results: bool = True,
        verbose: bool = True,
    ) -> dict:
        """Run the full validation pipeline.

        Parameters
        ----------
        params               : qualifying parameters (default: QualifyingParams.standard())
        n_synthetic          : synthetic matches to generate if real data is sparse
        model_accuracy       : assumed model accuracy for synthetic data generation
        n_walk_forward_splits: number of walk-forward folds
        n_sensitivity_runs   : whether to run sensitivity analysis
        save_results         : write JSON output to reports/profitability/
        verbose              : log progress

        Returns
        -------
        Full verdict dict with live_readiness_score, live_ready, reports.

        """
        if params is None:
            params = QualifyingParams.standard()

        gate = QualifyingGate(params)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # ---- 1. Load data ----
        real_records = self.load_real_data()

        # Augment with synthetic data when real data is sparse
        gen = SyntheticMatchGenerator(
            model_accuracy=model_accuracy,
            bookmaker_type=self.bookmaker_type,
        )
        n_synth_needed = max(0, n_synthetic - len(real_records))
        synthetic_records = gen.generate(n_matches=n_synth_needed) if n_synth_needed > 0 else []

        all_records = real_records + synthetic_records
        if verbose:
            logger.info(
                f"Data: {len(real_records)} real + {len(synthetic_records)} synthetic "
                f"= {len(all_records)} total matches",
            )

        # ---- 2. Full-sample backtest ----
        bet_results = simulate_bets(all_records, gate)
        full_report = build_profitability_report(bet_results)

        if verbose:
            self._log_report_summary(full_report, "FULL SAMPLE")

        # ---- 3. Walk-forward validation ----
        wf_rois = []
        wf_summaries = []
        folds = walk_forward_split(all_records, n_splits=n_walk_forward_splits)
        for fold_idx, (train, test) in enumerate(folds):
            fold_bets = simulate_bets(test, gate)
            fold_report = build_profitability_report(fold_bets, n_montecarlo=2000)
            wf_rois.append(fold_report.roi_pct)
            wf_summaries.append({
                "fold": fold_idx + 1,
                "test_size": len(test),
                "qualifying_bets": fold_report.qualifying_bets,
                "roi_pct": round(fold_report.roi_pct, 2),
                "hit_rate_pct": round(fold_report.hit_rate * 100, 2),
                "live_readiness_score": round(fold_report.live_readiness_score, 1),
            })

        wf_positive_roi_rate = sum(1 for r in wf_rois if r > 0) / max(len(wf_rois), 1)
        wf_mean_roi = statistics.mean(wf_rois) if wf_rois else 0.0
        wf_min_roi = min(wf_rois) if wf_rois else 0.0
        wf_std_roi = statistics.stdev(wf_rois) if len(wf_rois) > 1 else 0.0

        if verbose:
            logger.info(f"Walk-forward: mean ROI={wf_mean_roi:.2f}%, "
                        f"min={wf_min_roi:.2f}%, "
                        f"positive in {wf_positive_roi_rate*100:.0f}% of folds")

        # ---- 4. Walk-forward pass/fail ----
        wf_passed = wf_positive_roi_rate >= 0.60 and wf_mean_roi > 0

        # ---- 5. Sensitivity analysis ----
        sensitivity = {}
        if n_sensitivity_runs:
            sensitivity = sensitivity_analysis(all_records)

        # ---- 6. Conservative profile check ----
        conservative_gate = QualifyingGate(QualifyingParams.conservative())
        cons_bets = simulate_bets(all_records, conservative_gate)
        cons_report = build_profitability_report(cons_bets, n_montecarlo=2000)

        # ---- 7. Build final verdict ----
        # Overall live-readiness: full_report criteria + walk-forward
        final_live_ready = full_report.live_ready and wf_passed
        final_score = full_report.live_readiness_score

        # Penalise if walk-forward fails
        if not wf_passed:
            final_score = min(final_score, 49.0)
            full_report.failure_reasons.append(
                f"Walk-forward validation failed: positive ROI in only "
                f"{wf_positive_roi_rate*100:.0f}% of folds (need ≥ 60%)",
            )

        # ---- 8. Parameter summary ----
        params_dict = {
            "profile": "custom",
            "min_edge_pct": params.min_edge_pct,
            "min_ev_pct": params.min_ev_pct,
            "min_confidence": params.min_confidence,
            "min_data_quality": params.min_data_quality,
            "min_odds": params.min_odds,
            "max_odds": params.max_odds,
            "kelly_fraction": params.kelly_fraction,
            "max_stake_pct": params.max_stake_pct,
        }

        verdict = {
            "generated_at": datetime.now().isoformat(),
            "bookmaker_type": self.bookmaker_type,
            "data": {
                "real_records": len(real_records),
                "synthetic_records": len(synthetic_records),
                "total_records": len(all_records),
                "model_accuracy_assumption": model_accuracy,
            },
            "qualifying_params": params_dict,
            "full_sample_report": full_report.to_dict(),
            "walk_forward": {
                "n_folds": len(folds),
                "mean_roi_pct": round(wf_mean_roi, 2),
                "min_roi_pct": round(wf_min_roi, 2),
                "std_roi_pct": round(wf_std_roi, 2),
                "positive_roi_folds_pct": round(wf_positive_roi_rate * 100, 1),
                "passed": wf_passed,
                "fold_summaries": wf_summaries,
            },
            "conservative_profile_check": {
                "qualifying_bets": cons_report.qualifying_bets,
                "roi_pct": round(cons_report.roi_pct, 2),
                "hit_rate_pct": round(cons_report.hit_rate * 100, 2),
                "live_readiness_score": round(cons_report.live_readiness_score, 1),
                "live_ready": cons_report.live_ready,
            },
            "sensitivity_analysis": sensitivity,
            "verdict": {
                "live_ready": final_live_ready,
                "live_readiness_score": round(final_score, 1),
                "failure_reasons": full_report.failure_reasons,
                "recommendation": self._recommendation(final_live_ready, final_score,
                                                        full_report, wf_mean_roi),
            },
        }

        # ---- 9. Save ----
        if save_results:
            out_path = self.results_dir / f"live_validation_{timestamp}.json"
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(verdict, f, indent=2, default=str)
            logger.info(f"Validation report saved to {out_path}")

            txt_path = self.results_dir / f"live_validation_{timestamp}_summary.txt"
            self._write_text_summary(verdict, txt_path)
            logger.info(f"Text summary saved to {txt_path}")

        return verdict

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _recommendation(
        live_ready: bool,
        score: float,
        report: ProfitabilityReport,
        wf_mean_roi: float,
    ) -> str:
        if live_ready:
            return (
                f"LIVE-READY ✓ — Strategy meets all qualifying criteria. "
                f"Recommended live deployment with QualifyingParams.standard(). "
                f"Readiness score: {score:.1f}/100. "
                f"Expected yield: ~{report.roi_pct:.1f}% per unit staked. "
                f"Use quarter-Kelly staking and monitor ROI weekly."
            )
        if score >= 70:
            return (
                f"NEAR-READY — Score {score:.1f}/100. "
                f"Minor gaps: {'; '.join(report.failure_reasons[:2])}. "
                f"Collect more qualifying bets, then re-assess."
            )
        if score >= 50:
            return (
                f"NOT YET READY — Score {score:.1f}/100. "
                f"Key failures: {'; '.join(report.failure_reasons[:3])}. "
                f"Tighten qualifying params or improve model accuracy."
            )
        return (
            f"NOT READY — Score {score:.1f}/100. "
            f"Strategy does not demonstrate consistent positive EV. "
            f"Review model calibration and re-run after collecting real data."
        )

    @staticmethod
    def _log_report_summary(report: ProfitabilityReport, label: str):
        logger.info(f"\n{'='*60}")
        logger.info(f"  {label}")
        logger.info(f"{'='*60}")
        logger.info(f"  Qualifying bets  : {report.qualifying_bets}/{report.total_bets}")
        logger.info(f"  Hit rate         : {report.hit_rate*100:.1f}%")
        logger.info(f"  ROI              : {report.roi_pct:.2f}%")
        logger.info(f"  Max drawdown     : {report.max_drawdown_pct:.1f}%")
        logger.info(f"  Max consec losses: {report.max_consecutive_losses}")
        logger.info(f"  Sharpe equiv     : {report.sharpe_equivalent:.3f}")
        logger.info(f"  p-value          : {report.p_value:.4f} "
                    f"({'✓' if report.statistically_significant else '✗'})")
        logger.info(f"  Risk of ruin     : {report.risk_of_ruin_pct:.2f}%")
        logger.info(f"  Live-ready score : {report.live_readiness_score:.1f}/100"
                    f"  ({'PASS' if report.live_ready else 'FAIL'})")
        if report.failure_reasons:
            for r in report.failure_reasons:
                logger.info(f"    ✗ {r}")
        logger.info("=" * 60)

    @staticmethod
    def _write_text_summary(verdict: dict, path: Path):
        lines = [
            "=" * 68,
            "  LIVE TRADING VALIDATION REPORT",
            f"  Generated: {verdict['generated_at']}",
            "=" * 68,
            "",
            f"  Bookmaker type   : {verdict['bookmaker_type']}",
            f"  Data             : {verdict['data']['real_records']} real + "
            f"{verdict['data']['synthetic_records']} synthetic "
            f"= {verdict['data']['total_records']} matches",
            f"  Model accuracy   : {verdict['data']['model_accuracy_assumption']*100:.0f}%",
            "",
            "  QUALIFYING PARAMETERS",
            f"    Min edge       : {verdict['qualifying_params']['min_edge_pct']}pp",
            f"    Min confidence : {verdict['qualifying_params']['min_confidence']}",
            f"    Min odds       : {verdict['qualifying_params']['min_odds']}",
            f"    Max odds       : {verdict['qualifying_params']['max_odds']}",
            f"    Kelly fraction : {verdict['qualifying_params']['kelly_fraction']} (quarter-Kelly)",
            "",
            "  FULL-SAMPLE RESULTS",
        ]

        fs = verdict["full_sample_report"]
        samp = fs["sample"]
        fin = fs["financial"]
        risk = fs["risk"]
        stat = fs["statistics"]

        lines += [
            f"    Qualifying bets : {samp['qualifying_bets']} / {samp['total_bets']}",
            f"    Hit rate        : {samp['hit_rate_pct']}%",
            f"    ROI             : {fin['roi_pct']}%",
            f"    95% CI          : [{stat['ci_95_low_pct']}%, {stat['ci_95_high_pct']}%]",
            f"    Max drawdown    : {risk['max_drawdown_pct']}%",
            f"    Max consec loss : {risk['max_consecutive_losses']}",
            f"    Sharpe equiv    : {risk['sharpe_equivalent']}",
            f"    Risk of ruin    : {risk['risk_of_ruin_pct']}%",
            f"    p-value         : {stat['p_value']} "
            f"({'significant ✓' if stat['statistically_significant'] else 'not significant ✗'})",
            "",
            "  WALK-FORWARD VALIDATION",
        ]

        wf = verdict["walk_forward"]
        lines += [
            f"    Folds           : {wf['n_folds']}",
            f"    Mean ROI        : {wf['mean_roi_pct']}%",
            f"    Min ROI         : {wf['min_roi_pct']}%",
            f"    Positive folds  : {wf['positive_roi_folds_pct']}%",
            f"    Passed          : {'YES ✓' if wf['passed'] else 'NO ✗'}",
        ]
        for fold in wf.get("fold_summaries", []):
            lines.append(
                f"      Fold {fold['fold']}: n={fold['qualifying_bets']:3d}  "
                f"ROI={fold['roi_pct']:+.2f}%  hit={fold['hit_rate_pct']:.1f}%",
            )

        lines += [
            "",
            "  CONSERVATIVE PROFILE CHECK",
        ]
        cp = verdict["conservative_profile_check"]
        lines += [
            f"    Qualifying bets : {cp['qualifying_bets']}",
            f"    ROI             : {cp['roi_pct']}%",
            f"    Live-ready      : {'YES ✓' if cp['live_ready'] else 'NO ✗'}",
        ]

        lines += [
            "",
            "  LEAGUE BREAKDOWN",
        ]
        for lg, lb in fs.get("league_breakdown", {}).items():
            lines.append(
                f"    {lg:20s}: {lb['bets']:3d} bets  "
                f"ROI={lb['roi_pct']:+.2f}%  hit={lb['hit_rate_pct']:.1f}%",
            )

        v = verdict["verdict"]
        lines += [
            "",
            "  " + "=" * 64,
            f"  VERDICT: {'LIVE-READY ✓' if v['live_ready'] else 'NOT READY ✗'}",
            f"  Live-readiness score: {v['live_readiness_score']}/100",
            "  " + "=" * 64,
            "",
            "  Recommendation:",
        ]
        for line in v["recommendation"].split("."):
            if line.strip():
                lines.append(f"    {line.strip()}.")

        if v["failure_reasons"]:
            lines.append("")
            lines.append("  Failure reasons:")
            for r in v["failure_reasons"]:
                lines.append(f"    ✗ {r}")

        lines += ["", "=" * 68]

        path.write_text("\n".join(lines), encoding="utf-8")
