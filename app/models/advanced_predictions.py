"""Advanced Prediction Models
=========================

Implements remaining high-value prediction improvements:
- MI-003: Two-stage prediction (outcome first, then score)
- NF-004: Both Teams To Score (BTTS) prediction
- NF-005: Over/Under goals at multiple lines

These are dedicated models for specific betting markets.
"""

import logging
import math
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# ============================================================================
# MI-003: Two-Stage Prediction Model
# ============================================================================


@dataclass
class OutcomePrediction:
    """First stage: outcome prediction."""

    home_win_prob: float
    draw_prob: float
    away_win_prob: float
    predicted_outcome: str  # '1', 'X', '2'
    confidence: float


@dataclass
class ScorePrediction:
    """Second stage: score prediction given outcome."""

    expected_home_goals: float
    expected_away_goals: float
    most_likely_score: tuple[int, int]
    score_probability: float
    alternative_scores: list[tuple[tuple[int, int], float]]


class TwoStagePredictionModel:
    """Two-stage prediction model separating outcome and score prediction.

    Predicting "home win" is easier than predicting "2-1".
    This model:
    1. First predicts the outcome (1/X/2)
    2. Then predicts the most likely score GIVEN that outcome

    This separation reduces conflation errors and provides
    more accurate probability distributions.
    """

    def __init__(self):
        """Initialize two-stage model."""
        # Score distributions by outcome (based on historical data)
        # These are conditional probabilities P(score | outcome)
        self.home_win_scores = {
            (1, 0): 0.28,
            (2, 0): 0.18,
            (2, 1): 0.22,
            (3, 0): 0.08,
            (3, 1): 0.10,
            (3, 2): 0.06,
            (4, 0): 0.02,
            (4, 1): 0.03,
            (4, 2): 0.02,
            (4, 3): 0.01,
        }
        self.draw_scores = {
            (0, 0): 0.30,
            (1, 1): 0.38,
            (2, 2): 0.22,
            (3, 3): 0.08,
            (4, 4): 0.02,
        }
        self.away_win_scores = {
            (0, 1): 0.30,
            (0, 2): 0.20,
            (1, 2): 0.22,
            (0, 3): 0.08,
            (1, 3): 0.10,
            (2, 3): 0.05,
            (0, 4): 0.02,
            (1, 4): 0.02,
            (2, 4): 0.01,
        }

    def predict_outcome(
        self,
        home_strength: float,
        away_strength: float,
        home_advantage: float = 0.15,
        league_draw_tendency: float = 0.26,
    ) -> OutcomePrediction:
        """Stage 1: Predict match outcome.

        Args:
            home_strength: Home team strength (0-1)
            away_strength: Away team strength (0-1)
            home_advantage: Home advantage factor
            league_draw_tendency: League-specific draw rate

        Returns:
            OutcomePrediction with probabilities

        """
        # Adjust strengths for home advantage
        adj_home = home_strength * (1 + home_advantage)
        adj_away = away_strength * (1 - home_advantage * 0.5)

        # Calculate raw win probabilities
        total = adj_home + adj_away
        raw_home_prob = adj_home / total if total > 0 else 0.5
        raw_away_prob = adj_away / total if total > 0 else 0.5

        # Adjust for draws (draws happen ~26% in most leagues)
        # Use a blend of competitive factor and league tendency
        competitiveness = 1 - abs(raw_home_prob - raw_away_prob)
        draw_prob = league_draw_tendency * (0.5 + 0.5 * competitiveness)
        draw_prob = min(max(draw_prob, 0.15), 0.40)  # Cap between 15-40%

        # Distribute remaining probability
        remaining = 1 - draw_prob
        home_prob = raw_home_prob * remaining
        away_prob = raw_away_prob * remaining

        # Normalize
        total = home_prob + draw_prob + away_prob
        home_prob = home_prob / total * 100
        draw_prob = draw_prob / total * 100
        away_prob = away_prob / total * 100

        # Determine predicted outcome
        probs = {"1": home_prob, "X": draw_prob, "2": away_prob}
        predicted = max(probs, key=probs.get)

        # Confidence based on margin
        max_prob = max(home_prob, draw_prob, away_prob)
        confidence = min(max_prob + 10, 85)

        return OutcomePrediction(
            home_win_prob=round(home_prob, 1),
            draw_prob=round(draw_prob, 1),
            away_win_prob=round(away_prob, 1),
            predicted_outcome=predicted,
            confidence=round(confidence, 1),
        )

    def predict_score(
        self,
        outcome: OutcomePrediction,
        expected_home_goals: float = 1.5,
        expected_away_goals: float = 1.2,
    ) -> ScorePrediction:
        """Stage 2: Predict score given the predicted outcome.

        Args:
            outcome: Stage 1 outcome prediction
            expected_home_goals: Expected home goals (from Poisson/xG)
            expected_away_goals: Expected away goals (from Poisson/xG)

        Returns:
            ScorePrediction with most likely scores

        """
        predicted = outcome.predicted_outcome

        # Select score distribution based on outcome
        if predicted == "1":
            score_dist = self.home_win_scores
        elif predicted == "X":
            score_dist = self.draw_scores
        else:
            score_dist = self.away_win_scores

        # Weight scores by Poisson probability
        weighted_scores = {}
        for (h, a), base_prob in score_dist.items():
            # Poisson probability for this exact score
            poisson_home = self._poisson_prob(h, expected_home_goals)
            poisson_away = self._poisson_prob(a, expected_away_goals)
            poisson_combined = poisson_home * poisson_away

            # Blend historical with Poisson
            final_prob = 0.6 * base_prob + 0.4 * poisson_combined * 10
            weighted_scores[(h, a)] = final_prob

        # Normalize
        total = sum(weighted_scores.values())
        if total > 0:
            weighted_scores = {k: v / total for k, v in weighted_scores.items()}

        # Sort by probability
        sorted_scores = sorted(
            weighted_scores.items(), key=lambda x: x[1], reverse=True,
        )

        most_likely = sorted_scores[0]
        alternatives = [
            (score, round(prob * 100, 1)) for score, prob in sorted_scores[1:4]
        ]

        return ScorePrediction(
            expected_home_goals=round(expected_home_goals, 2),
            expected_away_goals=round(expected_away_goals, 2),
            most_likely_score=most_likely[0],
            score_probability=round(most_likely[1] * 100, 1),
            alternative_scores=alternatives,
        )

    def _poisson_prob(self, k: int, lambda_: float) -> float:
        """Calculate Poisson probability P(X=k) for given lambda."""
        if lambda_ <= 0:
            return 1.0 if k == 0 else 0.0
        return (lambda_**k) * math.exp(-lambda_) / math.factorial(k)

    def full_prediction(
        self,
        home_strength: float,
        away_strength: float,
        expected_home_goals: float,
        expected_away_goals: float,
        **kwargs,
    ) -> dict:
        """Complete two-stage prediction.

        Returns combined outcome and score prediction.
        """
        outcome = self.predict_outcome(home_strength, away_strength, **kwargs)
        score = self.predict_score(outcome, expected_home_goals, expected_away_goals)

        return {
            "outcome": {
                "home_prob": outcome.home_win_prob,
                "draw_prob": outcome.draw_prob,
                "away_prob": outcome.away_win_prob,
                "predicted": outcome.predicted_outcome,
                "confidence": outcome.confidence,
            },
            "score": {
                "expected_home": score.expected_home_goals,
                "expected_away": score.expected_away_goals,
                "most_likely": f"{score.most_likely_score[0]}-{score.most_likely_score[1]}",
                "probability": score.score_probability,
                "alternatives": [
                    f"{s[0]}-{s[1]} ({p}%)" for (s, p) in score.alternative_scores
                ],
            },
            "two_stage_enhanced": True,
        }


# ============================================================================
# NF-004: Both Teams To Score (BTTS) Prediction
# ============================================================================


class BTTSPredictor:
    """Dedicated Both Teams To Score (BTTS) predictor.

    BTTS is a popular betting market. While it can be inferred
    from expected goals, a dedicated model is more accurate.

    Key factors:
    - Team's clean sheet rate
    - Team's failure to score rate
    - League average BTTS rate
    - Defensive/attacking styles
    """

    # League-specific BTTS base rates
    LEAGUE_BTTS_RATES = {
        "premier-league": 0.52,
        "PL": 0.52,
        "bundesliga": 0.56,
        "BL1": 0.56,
        "la-liga": 0.48,
        "PD": 0.48,
        "serie-a": 0.50,
        "SA": 0.50,
        "ligue-1": 0.47,
        "FL1": 0.47,
        "championship": 0.54,
        "ELC": 0.54,
        "eredivisie": 0.58,
        "DED": 0.58,
    }

    def __init__(self):
        """Initialize BTTS predictor."""

    def predict_btts(
        self,
        expected_home_goals: float,
        expected_away_goals: float,
        home_clean_sheet_rate: float = 0.30,
        away_clean_sheet_rate: float = 0.25,
        home_failed_to_score_rate: float = 0.20,
        away_failed_to_score_rate: float = 0.25,
        league: str = "premier-league",
    ) -> dict:
        """Predict probability of both teams scoring.

        Args:
            expected_home_goals: Expected home goals
            expected_away_goals: Expected away goals
            home_clean_sheet_rate: Home team clean sheet %
            away_clean_sheet_rate: Away team clean sheet %
            home_failed_to_score_rate: Home team blank %
            away_failed_to_score_rate: Away team blank %
            league: League code for base rate

        Returns:
            Dictionary with BTTS probabilities

        """
        # Method 1: Poisson-based
        # P(home scores) = 1 - P(home = 0) = 1 - e^(-lambda_home)
        p_home_scores = 1 - math.exp(-expected_home_goals)
        p_away_scores = 1 - math.exp(-expected_away_goals)
        poisson_btts = p_home_scores * p_away_scores

        # Method 2: Historical rate based
        # P(BTTS) = P(home scores) * P(away scores)
        # P(home scores) = 1 - failed_to_score_rate
        # P(away scores) = 1 - home_clean_sheet_rate (from home's perspective)
        historical_home_scores = 1 - home_failed_to_score_rate
        historical_away_scores = 1 - away_failed_to_score_rate
        historical_btts = historical_home_scores * historical_away_scores

        # Method 3: League base rate adjustment
        league_rate = self.LEAGUE_BTTS_RATES.get(league, 0.50)

        # Blend methods (weighted average)
        btts_probability = (
            0.40 * poisson_btts + 0.35 * historical_btts + 0.25 * league_rate
        )

        # Calculate confidence based on agreement
        method_std = (
            (poisson_btts - btts_probability) ** 2
            + (historical_btts - btts_probability) ** 2
            + (league_rate - btts_probability) ** 2
        ) / 3
        confidence = 70 - (method_std * 100)
        confidence = max(min(confidence, 85), 40)

        btts_yes = round(btts_probability * 100, 1)
        btts_no = round((1 - btts_probability) * 100, 1)

        return {
            "btts_yes_probability": btts_yes,
            "btts_no_probability": btts_no,
            "prediction": "Yes" if btts_yes > 50 else "No",
            "confidence": round(confidence, 1),
            "method_breakdown": {
                "poisson": round(poisson_btts * 100, 1),
                "historical": round(historical_btts * 100, 1),
                "league_base": round(league_rate * 100, 1),
            },
            "factors": {
                "home_scoring_chance": round(p_home_scores * 100, 1),
                "away_scoring_chance": round(p_away_scores * 100, 1),
            },
        }


# ============================================================================
# NF-005: Over/Under Goals Prediction
# ============================================================================


class OverUnderPredictor:
    """Over/Under goals predictor for multiple lines.

    Uses Poisson distribution to calculate exact probabilities
    for O/U 0.5, 1.5, 2.5, 3.5, 4.5 goals.
    """

    COMMON_LINES = [0.5, 1.5, 2.5, 3.5, 4.5, 5.5]

    def __init__(self):
        """Initialize O/U predictor."""

    def predict_over_under(
        self, expected_home_goals: float, expected_away_goals: float, league: str = None,
    ) -> dict:
        """Predict over/under probabilities for multiple lines.

        Args:
            expected_home_goals: Expected home goals (lambda for Poisson)
            expected_away_goals: Expected away goals (lambda for Poisson)
            league: Optional league for adjustments

        Returns:
            Dictionary with O/U probabilities for each line

        """
        total_expected = expected_home_goals + expected_away_goals

        results = {"expected_total_goals": round(total_expected, 2), "lines": {}}

        for line in self.COMMON_LINES:
            over_prob = self._calculate_over_probability(total_expected, line)
            under_prob = 1 - over_prob

            # Calculate fair odds (for reference)
            fair_over_odds = 1 / over_prob if over_prob > 0 else float("inf")
            fair_under_odds = 1 / under_prob if under_prob > 0 else float("inf")

            results["lines"][f"{line}"] = {
                "over_probability": round(over_prob * 100, 1),
                "under_probability": round(under_prob * 100, 1),
                "prediction": "Over" if over_prob > 0.5 else "Under",
                "fair_over_odds": round(fair_over_odds, 2),
                "fair_under_odds": round(fair_under_odds, 2),
            }

        # Add main line recommendation
        main_line = self._find_main_line(total_expected)
        results["recommended_line"] = main_line
        results["main_prediction"] = results["lines"][main_line]["prediction"]

        return results

    def _calculate_over_probability(self, expected_total: float, line: float) -> float:
        """Calculate P(total goals > line) using Poisson.

        For half-goal lines (0.5, 1.5, etc.), this is equivalent to
        P(total goals >= ceiling(line)).
        """
        threshold = int(line) + 1  # e.g., O 2.5 means >= 3 goals

        # P(X >= k) = 1 - P(X < k) = 1 - sum(P(X=i) for i=0 to k-1)
        under_prob = 0.0
        for i in range(threshold):
            under_prob += self._poisson_prob(i, expected_total)

        return 1 - under_prob

    def _poisson_prob(self, k: int, lambda_: float) -> float:
        """Calculate Poisson probability."""
        if lambda_ <= 0:
            return 1.0 if k == 0 else 0.0
        return (lambda_**k) * math.exp(-lambda_) / math.factorial(k)

    def _find_main_line(self, expected_total: float) -> str:
        """Find the most balanced line (closest to 50/50)."""
        best_line = "2.5"
        best_balance = float("inf")

        for line in self.COMMON_LINES:
            over_prob = self._calculate_over_probability(expected_total, line)
            balance = abs(over_prob - 0.5)
            if balance < best_balance:
                best_balance = balance
                best_line = f"{line}"

        return best_line


# ============================================================================
# Exact Score Probability Calculator
# ============================================================================


class ExactScoreCalculator:
    """Calculate probabilities for exact scores using Poisson distribution.

    Provides:
    - Most likely scores
    - Score matrix with probabilities
    - Correct score betting insights
    """

    MAX_GOALS = 6  # Consider scores up to 6-6

    def __init__(self):
        """Initialize calculator."""

    def calculate_score_matrix(
        self, expected_home_goals: float, expected_away_goals: float,
    ) -> dict:
        """Generate full score probability matrix.

        Returns probabilities for all scorelines from 0-0 to MAX_GOALS-MAX_GOALS.
        """
        matrix = {}
        probabilities = []

        for home in range(self.MAX_GOALS + 1):
            for away in range(self.MAX_GOALS + 1):
                prob = self._poisson_prob(
                    home, expected_home_goals,
                ) * self._poisson_prob(away, expected_away_goals)
                matrix[f"{home}-{away}"] = round(prob * 100, 2)
                probabilities.append(((home, away), prob))

        # Sort by probability
        probabilities.sort(key=lambda x: x[1], reverse=True)

        # Top 10 most likely scores
        top_10 = [
            {"score": f"{h}-{a}", "probability": round(p * 100, 1)}
            for (h, a), p in probabilities[:10]
        ]

        return {
            "matrix": matrix,
            "top_10_scores": top_10,
            "most_likely": top_10[0] if top_10 else None,
            "expected_home": round(expected_home_goals, 2),
            "expected_away": round(expected_away_goals, 2),
        }

    def _poisson_prob(self, k: int, lambda_: float) -> float:
        """Calculate Poisson probability."""
        if lambda_ <= 0:
            return 1.0 if k == 0 else 0.0
        return (lambda_**k) * math.exp(-lambda_) / math.factorial(k)


# ============================================================================
# Unified Advanced Predictions Interface
# ============================================================================


class AdvancedPredictionSuite:
    """Unified interface for all advanced prediction models.

    Combines:
    - Two-stage prediction
    - BTTS prediction
    - Over/Under prediction
    - Exact score calculation
    """

    def __init__(self):
        """Initialize all prediction models."""
        self.two_stage = TwoStagePredictionModel()
        self.btts = BTTSPredictor()
        self.over_under = OverUnderPredictor()
        self.exact_score = ExactScoreCalculator()

    def full_prediction(
        self,
        home_strength: float,
        away_strength: float,
        expected_home_goals: float,
        expected_away_goals: float,
        league: str = "premier-league",
        home_clean_sheet_rate: float = 0.30,
        away_clean_sheet_rate: float = 0.25,
        home_failed_to_score_rate: float = 0.20,
        away_failed_to_score_rate: float = 0.25,
    ) -> dict:
        """Generate comprehensive prediction with all advanced models.

        Returns:
            Dictionary with all prediction types

        """
        # Two-stage prediction
        two_stage_result = self.two_stage.full_prediction(
            home_strength=home_strength,
            away_strength=away_strength,
            expected_home_goals=expected_home_goals,
            expected_away_goals=expected_away_goals,
        )

        # BTTS prediction
        btts_result = self.btts.predict_btts(
            expected_home_goals=expected_home_goals,
            expected_away_goals=expected_away_goals,
            home_clean_sheet_rate=home_clean_sheet_rate,
            away_clean_sheet_rate=away_clean_sheet_rate,
            home_failed_to_score_rate=home_failed_to_score_rate,
            away_failed_to_score_rate=away_failed_to_score_rate,
            league=league,
        )

        # Over/Under prediction
        ou_result = self.over_under.predict_over_under(
            expected_home_goals=expected_home_goals,
            expected_away_goals=expected_away_goals,
            league=league,
        )

        # Exact score probabilities
        score_result = self.exact_score.calculate_score_matrix(
            expected_home_goals=expected_home_goals,
            expected_away_goals=expected_away_goals,
        )

        return {
            "outcome": two_stage_result["outcome"],
            "predicted_score": two_stage_result["score"],
            "btts": btts_result,
            "over_under": ou_result,
            "exact_scores": score_result["top_10_scores"],
            "advanced_predictions_enabled": True,
        }


# Quick test
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    suite = AdvancedPredictionSuite()

    result = suite.full_prediction(
        home_strength=0.65,
        away_strength=0.55,
        expected_home_goals=1.8,
        expected_away_goals=1.2,
        league="premier-league",
    )

    print("=== Advanced Prediction Suite Test ===")
    print()
    print("Outcome Prediction:")
    print(
        f"  {result['outcome']['home_prob']}% / {result['outcome']['draw_prob']}% / {result['outcome']['away_prob']}%",
    )
    print(
        f"  Predicted: {result['outcome']['predicted']} ({result['outcome']['confidence']}% confidence)",
    )
    print()
    print("Score Prediction:")
    print(
        f"  Most likely: {result['predicted_score']['most_likely']} ({result['predicted_score']['probability']}%)",
    )
    print(f"  Alternatives: {result['predicted_score']['alternatives']}")
    print()
    print("BTTS Prediction:")
    print(
        f"  Yes: {result['btts']['btts_yes_probability']}% / No: {result['btts']['btts_no_probability']}%",
    )
    print(f"  Prediction: {result['btts']['prediction']}")
    print()
    print("Over/Under 2.5:")
    ou_25 = result["over_under"]["lines"]["2.5"]
    print(
        f"  Over: {ou_25['over_probability']}% / Under: {ou_25['under_probability']}%",
    )
    print(f"  Prediction: {ou_25['prediction']}")
    print()
    print("Top 5 Exact Scores:")
    for i, score in enumerate(result["exact_scores"][:5], 1):
        print(f"  {i}. {score['score']}: {score['probability']}%")
