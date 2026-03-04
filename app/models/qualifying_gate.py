"""
Qualifying Gate (PROF-003)
===========================
Defines and enforces the strict set of conditions that a prediction must
meet before it is considered eligible for live-trading staking.

Every prediction passes through the gate before a bet is placed.
Rejected predictions are tracked with a reason code for audit purposes.

Qualifying Criteria (all must pass)
------------------------------------
1.  EDGE ≥ min_edge_pct
        Our model probability must exceed the market-implied probability by
        at least `min_edge_pct` percentage points.  This ensures positive
        expected value after bookmaker margin.

2.  CONFIDENCE ≥ min_confidence
        The prediction engine must assign at least `min_confidence` to the
        pick (0-1 scale from the prediction pipeline).

3.  DATA QUALITY ≥ min_data_quality
        The data-quality score attached to the prediction must meet the floor.
        Low scores indicate missing injury/form/lineup data.

4.  ODDS IN RANGE [min_odds, max_odds]
        Bets below min_odds have insufficient return for risk.
        Bets above max_odds have high variance and are typically data-sparse.

5.  LEAGUE IN WHITELIST
        Only leagues with sufficient historical accuracy data qualify.

6.  EV ≥ min_ev_pct
        The raw expected-value fraction must exceed a floor even if edge is
        met (guard against very-short-odds bets with tiny absolute EV).

7.  STAKE ≤ max_stake_pct
        Kelly-sized stake must not exceed max_stake_pct of the bankroll.

All thresholds are configurable to support different risk profiles.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Default qualifying parameters
# ---------------------------------------------------------------------------


@dataclass
class QualifyingParams:
    """
    All tunable thresholds that govern which bets qualify for live trading.

    Three pre-built profiles are available:
        QualifyingParams.conservative()  – tight gate, fewest but safest bets
        QualifyingParams.standard()      – balanced default
        QualifyingParams.aggressive()    – more bets, lower filter
    """

    # --- Edge / value ---
    min_edge_pct: float = 5.0        # minimum edge over market-implied prob (pp)
    min_ev_pct: float = 4.0          # minimum expected-value % per bet

    # --- Model outputs ---
    min_confidence: float = 0.60     # minimum prediction confidence (0-1)
    min_data_quality: float = 0.65   # minimum data-quality score (0-1)

    # --- Odds limits ---
    min_odds: float = 1.40           # don't bet on overwhelming favourites
    max_odds: float = 6.00           # don't bet on long shots (high variance)

    # --- Staking ---
    max_stake_pct: float = 0.05      # max 5% of bankroll per bet
    kelly_fraction: float = 0.25     # quarter-Kelly (conservative)

    # --- League whitelist ---
    allowed_leagues: list = field(default_factory=lambda: [
        "premier-league",
        "bundesliga",
        "la-liga",
        "serie-a",
        "ligue-1",
    ])

    # --- Market selection ---
    # Which bet side(s) qualify: 'home', 'draw', 'away', or 'any'
    allowed_outcomes: list = field(default_factory=lambda: ["home", "draw", "away"])

    # --- Portfolio / session limits ---
    max_bets_per_day: int = 10
    max_daily_exposure_pct: float = 0.20   # max 20% bankroll at risk per day

    @classmethod
    def conservative(cls) -> "QualifyingParams":
        """Very tight gate for risk-averse live trading."""
        return cls(
            min_edge_pct=8.0,
            min_ev_pct=7.0,
            min_confidence=0.68,
            min_data_quality=0.70,
            min_odds=1.60,
            max_odds=4.50,
            max_stake_pct=0.03,
            kelly_fraction=0.20,
        )

    @classmethod
    def standard(cls) -> "QualifyingParams":
        """Balanced default for production use."""
        return cls()          # uses __init__ defaults

    @classmethod
    def aggressive(cls) -> "QualifyingParams":
        """Lower filter — more bets, higher variance."""
        return cls(
            min_edge_pct=3.0,
            min_ev_pct=2.5,
            min_confidence=0.52,
            min_data_quality=0.55,
            min_odds=1.30,
            max_odds=8.00,
            max_stake_pct=0.07,
            kelly_fraction=0.33,
        )


# ---------------------------------------------------------------------------
# Rejection reason codes
# ---------------------------------------------------------------------------

REJECT_EDGE            = "EDGE_BELOW_MIN"
REJECT_EV              = "EV_BELOW_MIN"
REJECT_CONFIDENCE      = "CONFIDENCE_BELOW_MIN"
REJECT_DATA_QUALITY    = "DATA_QUALITY_BELOW_MIN"
REJECT_ODDS_TOO_LOW    = "ODDS_BELOW_MIN"
REJECT_ODDS_TOO_HIGH   = "ODDS_ABOVE_MAX"
REJECT_LEAGUE          = "LEAGUE_NOT_WHITELISTED"
REJECT_OUTCOME         = "OUTCOME_NOT_ALLOWED"
REJECT_NEGATIVE_EV     = "NEGATIVE_EXPECTED_VALUE"


# ---------------------------------------------------------------------------
# Gate logic
# ---------------------------------------------------------------------------


@dataclass
class GateDecision:
    """Result of passing a prediction through the qualifying gate."""

    qualified: bool
    outcome_to_bet: Optional[str]         # 'home' | 'draw' | 'away'
    decimal_odds: Optional[float]
    model_prob: Optional[float]
    market_prob: Optional[float]
    edge_pct: Optional[float]
    ev_pct: Optional[float]
    kelly_stake_pct: float
    rejection_reasons: list[str]          # empty if qualified


class QualifyingGate:
    """
    Evaluates a prediction against configurable qualifying parameters.

    Usage
    -----
        gate = QualifyingGate(QualifyingParams.standard())
        decision = gate.evaluate(
            league="premier-league",
            model_home_prob=0.55, model_draw_prob=0.25, model_away_prob=0.20,
            market_odds_home=2.10, market_odds_draw=3.40, market_odds_away=3.80,
            confidence=0.72,
            data_quality=0.80,
        )
        if decision.qualified:
            place_bet(decision.outcome_to_bet, decision.kelly_stake_pct)
    """

    def __init__(self, params: Optional[QualifyingParams] = None):
        self.params = params or QualifyingParams.standard()

    def evaluate(
        self,
        league: str,
        model_home_prob: float,     # 0-1
        model_draw_prob: float,     # 0-1
        model_away_prob: float,     # 0-1
        market_odds_home: float,    # decimal odds
        market_odds_draw: float,
        market_odds_away: float,
        confidence: float,          # 0-1
        data_quality: float,        # 0-1
    ) -> GateDecision:
        """
        Decide whether to bet on any of the three outcomes and, if so, which.

        The gate evaluates all three outcomes and returns a decision for the
        single best qualifying opportunity (highest EV that meets all thresholds).
        Returns qualified=False if no outcome passes all checks.
        """
        # Normalise model probs
        total_p = model_home_prob + model_draw_prob + model_away_prob
        if total_p <= 0:
            return GateDecision(False, None, None, None, None, None, None, 0.0,
                                ["Invalid probabilities"])
        h = model_home_prob / total_p
        d = model_draw_prob / total_p
        a = model_away_prob / total_p

        candidates = [
            ("home", h, market_odds_home),
            ("draw", d, market_odds_draw),
            ("away", a, market_odds_away),
        ]

        best_decision: Optional[GateDecision] = None
        best_ev = -999.0

        for outcome, model_p, odds in candidates:
            rejection_reasons = []

            # Check outcome allowed
            if outcome not in self.params.allowed_outcomes:
                continue

            # Check league whitelist
            if league not in self.params.allowed_leagues:
                rejection_reasons.append(f"{REJECT_LEAGUE}: {league}")

            # Check confidence
            if confidence < self.params.min_confidence:
                rejection_reasons.append(
                    f"{REJECT_CONFIDENCE}: {confidence:.3f} < {self.params.min_confidence}"
                )

            # Check data quality
            if data_quality < self.params.min_data_quality:
                rejection_reasons.append(
                    f"{REJECT_DATA_QUALITY}: {data_quality:.3f} < {self.params.min_data_quality}"
                )

            # Odds bounds
            if odds < self.params.min_odds:
                rejection_reasons.append(
                    f"{REJECT_ODDS_TOO_LOW}: {odds} < {self.params.min_odds}"
                )
            if odds > self.params.max_odds:
                rejection_reasons.append(
                    f"{REJECT_ODDS_TOO_HIGH}: {odds} > {self.params.max_odds}"
                )

            # EV
            from app.models.profitability import calculate_ev, calculate_edge, quarter_kelly
            ev = calculate_ev(model_p, odds)
            edge = calculate_edge(model_p, odds)
            edge_pct = edge * 100.0
            ev_pct = ev * 100.0

            if ev < 0:
                rejection_reasons.append(f"{REJECT_NEGATIVE_EV}: EV={ev_pct:.2f}%")
            elif ev_pct < self.params.min_ev_pct:
                rejection_reasons.append(
                    f"{REJECT_EV}: EV={ev_pct:.2f}% < {self.params.min_ev_pct}%"
                )

            if edge_pct < self.params.min_edge_pct:
                rejection_reasons.append(
                    f"{REJECT_EDGE}: edge={edge_pct:.2f}pp < {self.params.min_edge_pct}pp"
                )

            # Kelly stake
            kelly_full_pct = max(0.0, quarter_kelly(model_p, odds) / self.params.kelly_fraction
                                  * self.params.kelly_fraction * 100.0)
            kelly_pct = min(kelly_full_pct, self.params.max_stake_pct * 100.0)

            qualified = len(rejection_reasons) == 0

            if qualified and ev > best_ev:
                best_ev = ev
                best_decision = GateDecision(
                    qualified=True,
                    outcome_to_bet=outcome,
                    decimal_odds=odds,
                    model_prob=model_p,
                    market_prob=1.0 / odds,
                    edge_pct=round(edge_pct, 2),
                    ev_pct=round(ev_pct, 2),
                    kelly_stake_pct=round(kelly_pct, 3),
                    rejection_reasons=[],
                )

        if best_decision and best_decision.qualified:
            return best_decision

        # Collect all reasons from the most-promising outcome
        best_candidate = max(candidates, key=lambda c: calculate_ev(c[1], c[2]))
        all_reasons = self._collect_all_reasons(
            league=league,
            outcome=best_candidate[0],
            model_p=best_candidate[1],
            odds=best_candidate[2],
            confidence=confidence,
            data_quality=data_quality,
        )
        return GateDecision(
            qualified=False,
            outcome_to_bet=None,
            decimal_odds=None,
            model_prob=None,
            market_prob=None,
            edge_pct=None,
            ev_pct=None,
            kelly_stake_pct=0.0,
            rejection_reasons=all_reasons,
        )

    def _collect_all_reasons(
        self, league, outcome, model_p, odds, confidence, data_quality
    ) -> list[str]:
        """Collect all rejection reasons for the given (best) candidate."""
        from app.models.profitability import calculate_ev, calculate_edge
        reasons = []
        if league not in self.params.allowed_leagues:
            reasons.append(f"{REJECT_LEAGUE}: {league}")
        if confidence < self.params.min_confidence:
            reasons.append(f"{REJECT_CONFIDENCE}: {confidence:.3f}")
        if data_quality < self.params.min_data_quality:
            reasons.append(f"{REJECT_DATA_QUALITY}: {data_quality:.3f}")
        if odds < self.params.min_odds:
            reasons.append(f"{REJECT_ODDS_TOO_LOW}: {odds}")
        if odds > self.params.max_odds:
            reasons.append(f"{REJECT_ODDS_TOO_HIGH}: {odds}")
        ev = calculate_ev(model_p, odds)
        edge = calculate_edge(model_p, odds)
        if ev < 0:
            reasons.append(f"{REJECT_NEGATIVE_EV}: EV={ev*100:.2f}%")
        elif ev * 100 < self.params.min_ev_pct:
            reasons.append(f"{REJECT_EV}: EV={ev*100:.2f}%")
        if edge * 100 < self.params.min_edge_pct:
            reasons.append(f"{REJECT_EDGE}: edge={edge*100:.2f}pp")
        return reasons or ["UNKNOWN"]
