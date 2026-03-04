"""
Market Odds Simulator (PROF-002)
=================================
Generates realistic bookmaker decimal odds from true-probability estimates,
applying a configurable book overround (margin).

This is used for backtesting when real historical odds are unavailable:
  • Build "fair odds" from the model's true-outcome probabilities
  • Apply a realistic bookmaker margin (typically 5-7% on 1X2 markets)
  • Optionally add calibration noise to simulate market uncertainty
  • Support "closing line" estimation (tighter market at kick-off)

Typical margins
---------------
Soft bookmakers    : 7-10%
Sharp bookmakers   : 3-5%
Betting exchanges  : 0-2% (commission on winnings)

All odds are DECIMAL (European) format.
"""

from __future__ import annotations

import random
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class SimulatedOdds:
    """Bookmaker odds for a 1X2 market."""

    home_odds: float        # decimal odds for home win
    draw_odds: float        # decimal odds for draw
    away_odds: float        # decimal odds for away win

    # Derived
    implied_home_prob: float = 0.0
    implied_draw_prob: float = 0.0
    implied_away_prob: float = 0.0
    overround: float = 0.0           # sum of implied probs - 1 (the book margin)
    margin_pct: float = 0.0          # overround expressed as %

    def __post_init__(self):
        self.implied_home_prob = 1.0 / self.home_odds
        self.implied_draw_prob = 1.0 / self.draw_odds
        self.implied_away_prob = 1.0 / self.away_odds
        total = self.implied_home_prob + self.implied_draw_prob + self.implied_away_prob
        self.overround = total - 1.0
        self.margin_pct = self.overround * 100.0

    def for_outcome(self, outcome: str) -> tuple[float, float]:
        """Return (decimal_odds, implied_prob) for 'home'|'draw'|'away'."""
        if outcome == "home":
            return self.home_odds, self.implied_home_prob
        if outcome == "draw":
            return self.draw_odds, self.implied_draw_prob
        return self.away_odds, self.implied_away_prob


# ---------------------------------------------------------------------------
# League-level typical margins (can be tuned per bookmaker type)
# ---------------------------------------------------------------------------

BOOKMAKER_MARGINS: dict[str, float] = {
    "soft":     0.075,   # typical high-street / soft bookmaker
    "sharp":    0.045,   # sharp/regulated bookmaker (Pinnacle-style)
    "exchange": 0.020,   # betting exchange (commission baked in)
    "default":  0.060,   # sensible conservative default
}

# League-specific overround adjustments (some leagues have less liquidity)
LEAGUE_MARGIN_ADJUSTMENTS: dict[str, float] = {
    "premier-league": 0.00,     # deep market, tight lines
    "bundesliga":     0.00,
    "la-liga":        0.00,
    "serie-a":        +0.005,
    "ligue-1":        +0.005,
    "default":        +0.010,
}


# ---------------------------------------------------------------------------
# Main simulator
# ---------------------------------------------------------------------------


class MarketSimulator:
    """
    Converts true-probability estimates into bookmaker decimal odds.

    Typical usage
    -------------
        sim = MarketSimulator(bookmaker_type="sharp")
        odds = sim.simulate(home_prob=0.55, draw_prob=0.25, away_prob=0.20,
                            league="premier-league")
        print(odds.home_odds)   # e.g. 1.73
    """

    def __init__(
        self,
        bookmaker_type: str = "default",
        noise_std: float = 0.01,
        seed: int = 42,
    ):
        """
        Parameters
        ----------
        bookmaker_type : "soft" | "sharp" | "exchange" | "default"
        noise_std      : standard deviation of Gaussian noise on implied probs
                         to simulate market uncertainty (0 = no noise).
        seed           : random seed for reproducible noise
        """
        self.base_margin = BOOKMAKER_MARGINS.get(bookmaker_type, BOOKMAKER_MARGINS["default"])
        self.noise_std = noise_std
        self._rng = random.Random(seed)
        self._bookmaker_type = bookmaker_type

    def simulate(
        self,
        home_prob: float,
        draw_prob: float,
        away_prob: float,
        league: str = "default",
        add_noise: bool = False,
    ) -> SimulatedOdds:
        """
        Build simulated bookmaker odds from true probabilities.

        The method:
        1. Normalise the three probs to sum to 1.
        2. Apply optional small noise (market uncertainty).
        3. Apply the book margin by proportionally compressing the probs upward
           so that the sum of (1/odds) equals (1 + margin).
        4. Convert to decimal odds: odds_i = 1 / (compressed_prob_i).

        Returns a SimulatedOdds instance.
        """
        # Normalise
        total = home_prob + draw_prob + away_prob
        if total <= 0:
            raise ValueError("Probabilities must sum to a positive value")

        hp = home_prob / total
        dp = draw_prob / total
        ap = away_prob / total

        # Optional noise
        if add_noise and self.noise_std > 0:
            hp += self._rng.gauss(0, self.noise_std)
            dp += self._rng.gauss(0, self.noise_std)
            ap += self._rng.gauss(0, self.noise_std)
            # Re-normalise after noise
            total2 = hp + dp + ap
            hp /= total2
            dp /= total2
            ap /= total2

        # Clamp to reasonable bounds
        hp = max(0.03, min(0.92, hp))
        dp = max(0.03, min(0.55, dp))
        ap = max(0.03, min(0.92, ap))

        # Re-normalise post-clamp
        total3 = hp + dp + ap
        hp /= total3
        dp /= total3
        ap /= total3

        # Apply margin
        league_adj = LEAGUE_MARGIN_ADJUSTMENTS.get(league, LEAGUE_MARGIN_ADJUSTMENTS["default"])
        margin = self.base_margin + league_adj
        scale = 1.0 + margin            # e.g. 1.060 for 6% margin

        # Compressed probabilities (sum = scale)
        c_hp = hp * scale
        c_dp = dp * scale
        c_ap = ap * scale

        # Decimal odds
        home_odds = round(1.0 / c_hp, 2)
        draw_odds = round(1.0 / c_dp, 2)
        away_odds = round(1.0 / c_ap, 2)

        return SimulatedOdds(
            home_odds=home_odds,
            draw_odds=draw_odds,
            away_odds=away_odds,
        )

    def simulate_closing_line(
        self,
        home_prob: float,
        draw_prob: float,
        away_prob: float,
        league: str = "default",
    ) -> SimulatedOdds:
        """
        Simulate closing-line odds (tighter margin, higher accuracy).

        Closing-line odds are the last odds before kick-off and represent
        the market's most efficient estimate of true probabilities.
        Beating the closing line consistently is a strong indicator of edge.
        """
        # Closing line uses sharp-style margin regardless of configured type
        original_margin = self.base_margin
        self.base_margin = BOOKMAKER_MARGINS["sharp"]
        odds = self.simulate(home_prob, draw_prob, away_prob, league)
        self.base_margin = original_margin
        return odds

    def closing_line_value(
        self,
        model_prob: float,
        closing_decimal_odds: float,
    ) -> float:
        """
        Closing Line Value (CLV):  model_prob / closing_implied_prob - 1

        Positive CLV means we beat the closing market price.
        Sustained positive CLV is the gold standard for demonstrating edge.

        Returns CLV as a fraction (e.g. 0.05 = +5% CLV).
        """
        closing_implied_prob = 1.0 / closing_decimal_odds
        return model_prob / closing_implied_prob - 1.0


# ---------------------------------------------------------------------------
# Synthetic match generator for backtesting without real historical data
# ---------------------------------------------------------------------------


class SyntheticMatchGenerator:
    """
    Generates a synthetic dataset of matches with model predictions and
    realistic market odds for backtesting the profitability engine.

    The generator uses a configurable model accuracy to simulate realistic
    prediction results from a calibrated sports prediction model.
    """

    # Typical league-level outcome distributions
    LEAGUE_PROFILES: dict[str, dict] = {
        "premier-league": {"home_rate": 0.46, "draw_rate": 0.24, "away_rate": 0.30},
        "bundesliga":     {"home_rate": 0.44, "draw_rate": 0.25, "away_rate": 0.31},
        "la-liga":        {"home_rate": 0.48, "draw_rate": 0.26, "away_rate": 0.26},
        "serie-a":        {"home_rate": 0.45, "draw_rate": 0.28, "away_rate": 0.27},
        "ligue-1":        {"home_rate": 0.47, "draw_rate": 0.27, "away_rate": 0.26},
        "default":        {"home_rate": 0.46, "draw_rate": 0.26, "away_rate": 0.28},
    }

    def __init__(
        self,
        model_accuracy: float = 0.60,
        bookmaker_type: str = "sharp",
        seed: int = 42,
    ):
        """
        Parameters
        ----------
        model_accuracy : overall 3-outcome accuracy to simulate (e.g. 0.60)
        bookmaker_type : type of bookmaker to simulate odds for
        seed           : random seed
        """
        self.model_accuracy = model_accuracy
        self.market_sim = MarketSimulator(bookmaker_type=bookmaker_type, seed=seed)
        self._rng = random.Random(seed)

    def generate(
        self,
        n_matches: int = 500,
        leagues: list[str] | None = None,
    ) -> list[dict]:
        """
        Generate n_matches synthetic match records.

        Each record contains:
            match_id, league, home_team, away_team,
            true_outcome ('home'|'draw'|'away'),
            model_home_prob, model_draw_prob, model_away_prob,
            model_confidence,
            data_quality,
            market_odds (SimulatedOdds),
            actual_outcome ('home'|'draw'|'away'),
        """
        if leagues is None:
            leagues = list(self.LEAGUE_PROFILES.keys())
            leagues = [lg for lg in leagues if lg != "default"]

        records = []
        outcomes = ["home", "draw", "away"]

        for i in range(n_matches):
            league = leagues[i % len(leagues)]
            profile = self.LEAGUE_PROFILES.get(league, self.LEAGUE_PROFILES["default"])

            base_probs = {
                "home": profile["home_rate"],
                "draw": profile["draw_rate"],
                "away": profile["away_rate"],
            }

            # ── True outcome (league realistic distribution) ──────────────
            r = self._rng.random()
            if r < base_probs["home"]:
                true_outcome = "home"
            elif r < base_probs["home"] + base_probs["draw"]:
                true_outcome = "draw"
            else:
                true_outcome = "away"

            # ── Market odds – derived from TRUE probs + independent noise ──
            # Bookmaker has their own model (historical stats + mild noise).
            # This is DECOUPLED from the prediction model below.
            mkt_h = max(0.05, base_probs["home"] + self._rng.gauss(0, 0.015))
            mkt_d = max(0.05, base_probs["draw"] + self._rng.gauss(0, 0.010))
            mkt_a = max(0.05, base_probs["away"] + self._rng.gauss(0, 0.015))
            mkt_tot = mkt_h + mkt_d + mkt_a
            market_odds = self.market_sim.simulate(
                home_prob=mkt_h / mkt_tot,
                draw_prob=mkt_d / mkt_tot,
                away_prob=mkt_a / mkt_tot,
                league=league,
            )

            # ── Prediction model ──────────────────────────────────────────
            # model_accuracy fraction: model predicts CORRECTLY (high prob on true)
            # (1 - model_accuracy) fraction: model predicts INCORRECTLY (high prob
            #   on one of the OTHER two outcomes, chosen randomly)
            model_is_correct = self._rng.random() < self.model_accuracy

            if model_is_correct:
                boosted_outcome = true_outcome
            else:
                wrong_choices = [o for o in outcomes if o != true_outcome]
                boosted_outcome = self._rng.choice(wrong_choices)

            # Build raw model probs: boost chosen outcome, add noise to all
            signal = 1.8  # fixed boost magnitude regardless of accuracy mode
            raw = {
                "home": base_probs["home"] * (signal if boosted_outcome == "home" else 1.0),
                "draw": base_probs["draw"] * (signal if boosted_outcome == "draw" else 1.0),
                "away": base_probs["away"] * (signal if boosted_outcome == "away" else 1.0),
            }
            raw["home"] += abs(self._rng.gauss(0, 0.035))
            raw["draw"] += abs(self._rng.gauss(0, 0.022))
            raw["away"] += abs(self._rng.gauss(0, 0.035))

            tot = raw["home"] + raw["draw"] + raw["away"]
            model_home_p = raw["home"] / tot
            model_draw_p = raw["draw"] / tot
            model_away_p = raw["away"] / tot

            # Confidence: function of the dominant probability
            dominant_prob = max(model_home_p, model_draw_p, model_away_p)
            confidence = min(0.92, max(0.45, 0.38 + dominant_prob * 0.82))

            # Data quality: random 0.55-1.0
            data_quality = 0.55 + self._rng.random() * 0.45

            records.append({
                "match_id": f"synth_{i:05d}",
                "league": league,
                "home_team": f"HomeFC_{i % 20}",
                "away_team": f"AwayFC_{i % 20 + 1}",
                "model_home_prob": round(model_home_p, 4),
                "model_draw_prob": round(model_draw_p, 4),
                "model_away_prob": round(model_away_p, 4),
                "model_confidence": round(confidence, 3),
                "data_quality": round(data_quality, 3),
                "market_odds": market_odds,
                "actual_outcome": true_outcome,
                "true_outcome": true_outcome,
                "model_was_correct": model_is_correct,
            })

        return records
