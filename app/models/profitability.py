"""Profitability Engine (PROF-001)
================================
Core expected-value, ROI, Kelly criterion, drawdown, and statistical-significance
calculations for validating whether the prediction strategy is profitable enough
for live sports-betting deployment.

Key metrics produced
--------------------
- Expected Value (EV) per bet in decimal odds
- Yield / ROI % over a sample of bets
- Kelly-fraction stake sizing (quarter-Kelly by default)
- Maximum drawdown and consecutive-loss streak
- Sharpe-equivalent (profit / std deviation of returns)
- Binomial significance test (one-tail p-value for ROI > 0)
- Risk-of-ruin estimate via Monte Carlo

Terminology
-----------
decimal_odds  : e.g. 2.50 means bet 1, win 2.50 back (profit = 1.50)
model_prob    : our estimated probability of the outcome (0-1)
market_prob   : bookmaker-implied probability = 1 / decimal_odds
edge          : model_prob - market_prob  (positive = value bet)
EV            : edge expressed as fraction of stake, e.g. 0.08 = +8%
"""

from __future__ import annotations

import math
import random
import statistics
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class BetResult:
    """Outcome of a single simulated or real bet."""

    match_id: str
    league: str
    outcome_label: str          # 'home' | 'draw' | 'away'
    model_prob: float           # 0-1
    market_prob: float          # 0-1  (= 1 / decimal_odds)
    decimal_odds: float         # e.g. 2.50
    edge: float                 # model_prob - market_prob
    ev: float                   # expected-value fraction of stake
    stake: float                # actual stake in units
    won: bool                   # did the bet win?
    profit: float               # profit in units (negative = loss)
    confidence: float           # model confidence 0-1
    data_quality: float         # data quality score 0-1
    qualified: bool             # passed qualifying gate?
    disqualification_reason: str | None = None


@dataclass
class ProfitabilityReport:
    """Aggregated profitability statistics over a backtest period."""

    # Sample stats
    total_bets: int = 0
    qualifying_bets: int = 0
    winning_bets: int = 0

    # Financial metrics
    total_staked: float = 0.0
    total_profit: float = 0.0
    roi_pct: float = 0.0          # total_profit / total_staked * 100
    yield_pct: float = 0.0        # profit per unit staked (same as roi)

    # Accuracy
    hit_rate: float = 0.0         # winning_bets / qualifying_bets

    # Risk metrics
    max_drawdown_pct: float = 0.0
    max_consecutive_losses: int = 0
    sharpe_equivalent: float = 0.0

    # Statistical significance
    z_score: float = 0.0
    p_value: float = 1.0          # one-tail
    statistically_significant: bool = False
    confidence_interval_low: float = 0.0   # 95% CI on ROI
    confidence_interval_high: float = 0.0

    # Risk of ruin
    risk_of_ruin_pct: float = 0.0       # estimated % chance of 50% bankroll loss

    # Per-league breakdown
    league_breakdown: dict = field(default_factory=dict)

    # Live-readiness verdict
    live_ready: bool = False
    live_readiness_score: float = 0.0   # 0-100
    failure_reasons: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "sample": {
                "total_bets": self.total_bets,
                "qualifying_bets": self.qualifying_bets,
                "winning_bets": self.winning_bets,
                "hit_rate_pct": round(self.hit_rate * 100, 2),
            },
            "financial": {
                "total_staked_units": round(self.total_staked, 2),
                "total_profit_units": round(self.total_profit, 2),
                "roi_pct": round(self.roi_pct, 2),
                "yield_pct": round(self.yield_pct, 2),
            },
            "risk": {
                "max_drawdown_pct": round(self.max_drawdown_pct, 2),
                "max_consecutive_losses": self.max_consecutive_losses,
                "sharpe_equivalent": round(self.sharpe_equivalent, 3),
                "risk_of_ruin_pct": round(self.risk_of_ruin_pct, 2),
            },
            "statistics": {
                "z_score": round(self.z_score, 3),
                "p_value": round(self.p_value, 4),
                "statistically_significant": self.statistically_significant,
                "ci_95_low_pct": round(self.confidence_interval_low, 2),
                "ci_95_high_pct": round(self.confidence_interval_high, 2),
            },
            "league_breakdown": self.league_breakdown,
            "verdict": {
                "live_ready": self.live_ready,
                "live_readiness_score": round(self.live_readiness_score, 1),
                "failure_reasons": self.failure_reasons,
            },
        }


# ---------------------------------------------------------------------------
# Core calculations
# ---------------------------------------------------------------------------


def calculate_ev(model_prob: float, decimal_odds: float) -> float:
    """Expected value as fraction of stake.

    EV = model_prob * (decimal_odds - 1) - (1 - model_prob)
       = model_prob * decimal_odds - 1

    Returns: EV fraction, e.g. 0.08 means +8% EV per unit staked.
    """
    return model_prob * decimal_odds - 1.0


def calculate_edge(model_prob: float, decimal_odds: float) -> float:
    """Edge = model probability − market-implied probability.
    Positive means the model sees more value than the market prices in.
    """
    market_prob = 1.0 / decimal_odds
    return model_prob - market_prob


def kelly_fraction(model_prob: float, decimal_odds: float) -> float:
    """Full Kelly criterion: f* = (model_prob * decimal_odds - 1) / (decimal_odds - 1)

    Returns fraction of bankroll to stake (can be negative if EV ≤ 0).
    """
    b = decimal_odds - 1.0          # net odds
    if b <= 0:
        return 0.0
    return (model_prob * decimal_odds - 1.0) / b


def quarter_kelly(model_prob: float, decimal_odds: float) -> float:
    """Conservative quarter-Kelly stake, floor at 0, cap at 5% of bankroll."""
    fk = kelly_fraction(model_prob, decimal_odds)
    return max(0.0, min(fk * 0.25, 0.05))


# ---------------------------------------------------------------------------
# Aggregate analysis
# ---------------------------------------------------------------------------


def compute_drawdown(profit_series: list[float]) -> tuple[float, float]:
    """Compute maximum drawdown from a cumulative P&L series.

    Returns (max_drawdown_absolute, max_drawdown_pct_of_peak).
    peak never goes below 0 (baseline = 0).
    """
    if not profit_series:
        return 0.0, 0.0

    cumulative = []
    running = 0.0
    for p in profit_series:
        running += p
        cumulative.append(running)

    peak = 0.0
    max_dd = 0.0

    for c in cumulative:
        peak = max(peak, c)
        dd = peak - c
        max_dd = max(max_dd, dd)

    # Express as % of peak (or % of initial bankroll, use 100 units as baseline)
    baseline = max(peak, 100.0)
    return max_dd, (max_dd / baseline) * 100.0


def max_consecutive_losses(won_flags: list[bool]) -> int:
    """Return the longest losing streak in a sequence of bet outcomes."""
    max_streak = 0
    current = 0
    for w in won_flags:
        if not w:
            current += 1
            max_streak = max(max_streak, current)
        else:
            current = 0
    return max_streak


def sharpe_equivalent(profit_series: list[float]) -> float:
    """Sharpe-equivalent: mean(profit per bet) / std(profit per bet).
    Higher is better. Annualise by noting most leagues have ~300 games/season.
    """
    if len(profit_series) < 2:
        return 0.0
    mean = statistics.mean(profit_series)
    std = statistics.stdev(profit_series)
    if std == 0:
        return 0.0
    return mean / std


# ---------------------------------------------------------------------------
# Statistical significance
# ---------------------------------------------------------------------------


def binomial_significance_test(
    n_bets: int, n_wins: int, expected_hit_rate: float,
) -> tuple[float, float]:
    """One-tailed binomial test: H0: actual win rate ≤ expected_hit_rate

    Uses normal approximation (valid for n > 30).

    Returns (z_score, p_value).
    p_value < 0.05 → statistically significant positive edge.
    """
    if n_bets < 2:
        return 0.0, 1.0

    p0 = expected_hit_rate          # null hypothesis hit rate
    p_hat = n_wins / n_bets

    std_err = math.sqrt(p0 * (1.0 - p0) / n_bets)
    if std_err == 0:
        return 0.0, 1.0

    z = (p_hat - p0) / std_err
    # Approximate one-tail p-value using error function
    p_value = max(0.0, 0.5 * (1.0 - math.erf(z / math.sqrt(2))))
    return z, p_value


def roi_confidence_interval(roi_pct: float, n_bets: int, std_profit: float,
                             stake: float = 1.0) -> tuple[float, float]:
    """95% confidence interval on ROI (% of stake) using normal approximation.

    Returns (lower_bound_pct, upper_bound_pct).
    """
    if n_bets < 2 or stake == 0:
        return roi_pct, roi_pct

    std_err_roi = (std_profit / stake) * 100.0 / math.sqrt(n_bets)
    margin = 1.96 * std_err_roi
    return roi_pct - margin, roi_pct + margin


# ---------------------------------------------------------------------------
# Monte Carlo risk-of-ruin
# ---------------------------------------------------------------------------


def estimate_risk_of_ruin(
    avg_stake_frac: float,
    avg_ev: float,
    hit_rate: float,
    avg_decimal_odds: float,
    n_simulations: int = 10_000,
    n_bets: int = 500,
    ruin_threshold: float = 0.50,
    seed: int = 42,
) -> float:
    """Monte Carlo estimate of Risk of Ruin (proportion of simulations where
    bankroll drops below `ruin_threshold` fraction of starting bankroll).

    Parameters
    ----------
    avg_stake_frac   : average stake as fraction of bankroll (e.g. 0.02)
    avg_ev           : average expected value per bet (e.g. 0.06 = +6%)
    hit_rate         : win probability per qualifying bet
    avg_decimal_odds : average decimal odds
    n_simulations    : number of Monte Carlo paths
    n_bets           : bets per simulation path
    ruin_threshold   : bankroll fraction below which we call it "ruin" (0.50 = 50% loss)
    seed             : random seed for reproducibility

    Returns
    -------
    risk_of_ruin_pct : percentage 0–100 of simulations that hit ruin.

    """
    rng = random.Random(seed)
    ruin_count = 0

    for _ in range(n_simulations):
        bankroll = 1.0
        for _ in range(n_bets):
            if bankroll <= 0:
                break
            stake = min(bankroll * avg_stake_frac, bankroll)
            won = rng.random() < hit_rate
            if won:
                bankroll += stake * (avg_decimal_odds - 1.0)
            else:
                bankroll -= stake

        if bankroll < ruin_threshold:
            ruin_count += 1

    return (ruin_count / n_simulations) * 100.0


# ---------------------------------------------------------------------------
# Live-readiness gate
# ---------------------------------------------------------------------------

# Thresholds that MUST pass for live deployment
LIVE_CRITERIA: dict[str, dict] = {
    "min_qualifying_bets":     {"threshold": 100,   "weight": 15, "label": "Sample ≥ 100 qualifying bets"},
    "min_roi_pct":             {"threshold": 5.0,   "weight": 20, "label": "Backtested ROI ≥ 5%"},
    "p_value":                 {"threshold": 0.05,  "weight": 20, "label": "Statistically significant (p < 0.05)"},
    "max_drawdown_pct":        {"threshold": 25.0,  "weight": 15, "label": "Max drawdown ≤ 25%"},
    "risk_of_ruin_pct":        {"threshold": 2.0,   "weight": 15, "label": "Risk of ruin ≤ 2%"},
    "max_consecutive_losses":  {"threshold": 20,    "weight": 5,  "label": "Max consecutive losses ≤ 20"},
    "sharpe_equivalent":       {"threshold": 0.05,  "weight": 10, "label": "Sharpe ≥ 0.05 per bet (≈ 1.1 annualised @ 500 bets/yr)"},
}


def score_live_readiness(report: ProfitabilityReport) -> tuple[float, bool, list[str]]:
    """Score the strategy's live-readiness on a 0-100 scale.

    Returns (score, live_ready, failure_reasons).
    A strategy is live-ready only if ALL hard criteria pass.
    """
    total_weight = sum(c["weight"] for c in LIVE_CRITERIA.values())
    earned_weight = 0.0
    failures = []

    checks = {
        "min_qualifying_bets":    (report.qualifying_bets,        ">="),
        "min_roi_pct":            (report.roi_pct,                ">="),
        "p_value":                (report.p_value,                "<="),
        "max_drawdown_pct":       (report.max_drawdown_pct,       "<="),
        "risk_of_ruin_pct":       (report.risk_of_ruin_pct,       "<="),
        "max_consecutive_losses": (report.max_consecutive_losses, "<="),
        "sharpe_equivalent":      (report.sharpe_equivalent,      ">="),
    }

    for key, (value, direction) in checks.items():
        criterion = LIVE_CRITERIA[key]
        threshold = criterion["threshold"]
        passed = (value >= threshold) if direction == ">=" else (value <= threshold)
        if passed:
            earned_weight += criterion["weight"]
        else:
            failures.append(
                f"{criterion['label']}: got {value:.3g}, need {direction} {threshold}",
            )

    score = (earned_weight / total_weight) * 100.0
    live_ready = len(failures) == 0
    return score, live_ready, failures


# ---------------------------------------------------------------------------
# Aggregate bet results into a report
# ---------------------------------------------------------------------------


def build_profitability_report(
    results: list[BetResult],
    market_expected_hit_rate: float = 0.40,      # typical market-implied hit rate
    n_montecarlo: int = 5_000,
) -> ProfitabilityReport:
    """Build a ProfitabilityReport from a list of BetResult objects.

    Only qualifying bets (result.qualified == True) are counted in financials.
    """
    report = ProfitabilityReport()
    report.total_bets = len(results)

    qual = [r for r in results if r.qualified]
    report.qualifying_bets = len(qual)

    if not qual:
        report.failure_reasons = ["No qualifying bets found — tighten or loosen the qualifying gate."]
        score, ready, failures = score_live_readiness(report)
        report.live_readiness_score = score
        report.live_ready = ready
        report.failure_reasons = failures
        return report

    # Financial
    profits = [r.profit for r in qual]
    report.winning_bets = sum(1 for r in qual if r.won)
    report.total_staked = sum(r.stake for r in qual)
    report.total_profit = sum(profits)
    report.hit_rate = report.winning_bets / report.qualifying_bets

    if report.total_staked > 0:
        report.roi_pct = (report.total_profit / report.total_staked) * 100.0
        report.yield_pct = report.roi_pct

    # Risk
    _, report.max_drawdown_pct = compute_drawdown(profits)
    report.max_consecutive_losses = max_consecutive_losses([r.won for r in qual])
    report.sharpe_equivalent = sharpe_equivalent(profits)

    # Statistical significance
    report.z_score, report.p_value = binomial_significance_test(
        report.qualifying_bets,
        report.winning_bets,
        market_expected_hit_rate,
    )
    report.statistically_significant = report.p_value < 0.05

    # 95% CI on ROI
    try:
        std_p = statistics.stdev(profits)
        avg_stake = report.total_staked / report.qualifying_bets
        low, high = roi_confidence_interval(report.roi_pct, report.qualifying_bets,
                                            std_p, avg_stake)
        report.confidence_interval_low = low
        report.confidence_interval_high = high
    except Exception:
        pass

    # Risk of ruin (Monte Carlo)
    # avg_stake_frac: Kelly staking is capped at 5% of current bankroll per bet.
    # Absolute stake amounts grow with the bankroll, so dividing by initial $100
    # inflates the fraction when the bankroll has grown.  We therefore clamp to
    # the hard cap enforced in simulate_bets (0.05 = 5%).
    avg_stake_frac = min(
        (report.total_staked / report.qualifying_bets) / 100.0,
        0.05,  # quarter-Kelly hard cap
    )
    avg_odds = sum(r.decimal_odds for r in qual) / len(qual)
    report.risk_of_ruin_pct = estimate_risk_of_ruin(
        avg_stake_frac=avg_stake_frac,
        avg_ev=sum(r.ev for r in qual) / len(qual),
        hit_rate=report.hit_rate,
        avg_decimal_odds=avg_odds,
        n_simulations=n_montecarlo,
    )

    # League breakdown
    league_results: dict[str, list[BetResult]] = {}
    for r in qual:
        league_results.setdefault(r.league, []).append(r)
    report.league_breakdown = {
        lg: {
            "bets": len(lr),
            "wins": sum(1 for r in lr if r.won),
            "roi_pct": round(
                sum(r.profit for r in lr) / max(sum(r.stake for r in lr), 1e-9) * 100, 2,
            ),
            "hit_rate_pct": round(sum(1 for r in lr if r.won) / len(lr) * 100, 2),
        }
        for lg, lr in league_results.items()
    }

    # Live readiness
    score, ready, failures = score_live_readiness(report)
    report.live_readiness_score = score
    report.live_ready = ready
    report.failure_reasons = failures

    return report
