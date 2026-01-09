"""
Prediction Tracking System - Phase 2 Data Foundation (CC-002)
Tracks predictions and actual results to measure and improve accuracy.

This is CRITICAL infrastructure - without tracking, we can't:
- Know which predictions were right/wrong
- Calculate actual accuracy
- Identify systematic biases
- Validate improvements
"""

import json
import os
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional


@dataclass
class PredictionRecord:
    """Single prediction with outcome tracking"""

    # Match identification
    prediction_id: str  # Unique ID
    match_id: int
    home_team_id: int
    away_team_id: int
    home_team_name: str
    away_team_name: str
    league: str
    match_date: str  # ISO format

    # Prediction values
    predicted_home_prob: float
    predicted_draw_prob: float
    predicted_away_prob: float
    predicted_home_goals: float
    predicted_away_goals: float
    confidence: float

    # Metadata
    prediction_timestamp: str
    model_version: str = "v4.2"
    enhancements_applied: List[str] = field(default_factory=list)

    # Actual results (filled in after match)
    actual_home_goals: Optional[int] = None
    actual_away_goals: Optional[int] = None
    actual_outcome: Optional[str] = None  # 'home', 'draw', 'away'
    result_timestamp: Optional[str] = None

    # Accuracy metrics (calculated after result)
    predicted_outcome: Optional[str] = None  # What we predicted
    prediction_correct: Optional[bool] = None
    probability_for_outcome: Optional[float] = (
        None  # Prob we assigned to actual outcome
    )
    brier_score: Optional[float] = None  # Probabilistic accuracy

    def calculate_metrics(self):
        """Calculate accuracy metrics after result is known"""
        if self.actual_outcome is None:
            return

        # Determine what we predicted
        probs = {
            "home": self.predicted_home_prob,
            "draw": self.predicted_draw_prob,
            "away": self.predicted_away_prob,
        }
        self.predicted_outcome = max(probs, key=probs.get)

        # Was prediction correct?
        self.prediction_correct = self.predicted_outcome == self.actual_outcome

        # What probability did we assign to the actual outcome?
        self.probability_for_outcome = probs.get(self.actual_outcome, 0)

        # Brier score (lower = better, 0 = perfect)
        # Sum of squared differences between predicted and actual (0/1)
        actual_vec = {"home": 0, "draw": 0, "away": 0}
        actual_vec[self.actual_outcome] = 1

        self.brier_score = sum(
            ((probs[k] / 100) - actual_vec[k]) ** 2 for k in ["home", "draw", "away"]
        )


class PredictionTracker:
    """
    Tracks all predictions and results in SQLite database.

    Features:
    - Store predictions at time of generation
    - Auto-fetch results after matches complete
    - Calculate accuracy metrics
    - Query historical performance
    """

    def __init__(self, db_path: str = "data/predictions.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_database()

    def _init_database(self):
        """Initialize SQLite database with prediction schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS predictions (
                prediction_id TEXT PRIMARY KEY,
                match_id INTEGER,
                home_team_id INTEGER,
                away_team_id INTEGER,
                home_team_name TEXT,
                away_team_name TEXT,
                league TEXT,
                match_date TEXT,
                
                predicted_home_prob REAL,
                predicted_draw_prob REAL,
                predicted_away_prob REAL,
                predicted_home_goals REAL,
                predicted_away_goals REAL,
                confidence REAL,
                
                prediction_timestamp TEXT,
                model_version TEXT,
                enhancements_applied TEXT,
                
                actual_home_goals INTEGER,
                actual_away_goals INTEGER,
                actual_outcome TEXT,
                result_timestamp TEXT,
                
                predicted_outcome TEXT,
                prediction_correct INTEGER,
                probability_for_outcome REAL,
                brier_score REAL
            )
        """
        )

        # Index for efficient queries
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_match_date ON predictions(match_date)"
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_league ON predictions(league)")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_result ON predictions(actual_outcome)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_correct ON predictions(prediction_correct)"
        )

        conn.commit()
        conn.close()

    def store_prediction(self, record: PredictionRecord) -> str:
        """Store a new prediction"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO predictions (
                prediction_id, match_id, home_team_id, away_team_id,
                home_team_name, away_team_name, league, match_date,
                predicted_home_prob, predicted_draw_prob, predicted_away_prob,
                predicted_home_goals, predicted_away_goals, confidence,
                prediction_timestamp, model_version, enhancements_applied,
                actual_home_goals, actual_away_goals, actual_outcome, result_timestamp,
                predicted_outcome, prediction_correct, probability_for_outcome, brier_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                record.prediction_id,
                record.match_id,
                record.home_team_id,
                record.away_team_id,
                record.home_team_name,
                record.away_team_name,
                record.league,
                record.match_date,
                record.predicted_home_prob,
                record.predicted_draw_prob,
                record.predicted_away_prob,
                record.predicted_home_goals,
                record.predicted_away_goals,
                record.confidence,
                record.prediction_timestamp,
                record.model_version,
                json.dumps(record.enhancements_applied),
                record.actual_home_goals,
                record.actual_away_goals,
                record.actual_outcome,
                record.result_timestamp,
                record.predicted_outcome,
                (
                    1
                    if record.prediction_correct
                    else (0 if record.prediction_correct is not None else None)
                ),
                record.probability_for_outcome,
                record.brier_score,
            ),
        )

        conn.commit()
        conn.close()

        return record.prediction_id

    def record_result(
        self, match_id: int, home_goals: int, away_goals: int
    ) -> Optional[PredictionRecord]:
        """Record actual match result and calculate accuracy"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Find prediction for this match
        cursor.execute("SELECT * FROM predictions WHERE match_id = ?", (match_id,))
        row = cursor.fetchone()

        if row is None:
            conn.close()
            return None

        # Determine outcome
        if home_goals > away_goals:
            outcome = "home"
        elif away_goals > home_goals:
            outcome = "away"
        else:
            outcome = "draw"

        # Create record from row
        record = self._row_to_record(row)
        record.actual_home_goals = home_goals
        record.actual_away_goals = away_goals
        record.actual_outcome = outcome
        record.result_timestamp = datetime.now().isoformat()
        record.calculate_metrics()

        # Update database
        cursor.execute(
            """
            UPDATE predictions SET
                actual_home_goals = ?,
                actual_away_goals = ?,
                actual_outcome = ?,
                result_timestamp = ?,
                predicted_outcome = ?,
                prediction_correct = ?,
                probability_for_outcome = ?,
                brier_score = ?
            WHERE match_id = ?
        """,
            (
                record.actual_home_goals,
                record.actual_away_goals,
                record.actual_outcome,
                record.result_timestamp,
                record.predicted_outcome,
                1 if record.prediction_correct else 0,
                record.probability_for_outcome,
                record.brier_score,
                match_id,
            ),
        )

        conn.commit()
        conn.close()

        return record

    def _row_to_record(self, row: tuple) -> PredictionRecord:
        """Convert database row to PredictionRecord"""
        columns = [
            "prediction_id",
            "match_id",
            "home_team_id",
            "away_team_id",
            "home_team_name",
            "away_team_name",
            "league",
            "match_date",
            "predicted_home_prob",
            "predicted_draw_prob",
            "predicted_away_prob",
            "predicted_home_goals",
            "predicted_away_goals",
            "confidence",
            "prediction_timestamp",
            "model_version",
            "enhancements_applied",
            "actual_home_goals",
            "actual_away_goals",
            "actual_outcome",
            "result_timestamp",
            "predicted_outcome",
            "prediction_correct",
            "probability_for_outcome",
            "brier_score",
        ]
        data = dict(zip(columns, row))

        # Parse enhancements JSON
        if data["enhancements_applied"]:
            try:
                data["enhancements_applied"] = json.loads(data["enhancements_applied"])
            except Exception:
                data["enhancements_applied"] = []
        else:
            data["enhancements_applied"] = []

        # Convert prediction_correct back to bool
        if data["prediction_correct"] is not None:
            data["prediction_correct"] = bool(data["prediction_correct"])

        return PredictionRecord(**data)

    def get_accuracy_stats(
        self,
        league: Optional[str] = None,
        days_back: int = 90,
        min_confidence: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Get accuracy statistics for predictions.

        Returns:
            Overall accuracy, Brier score, calibration metrics, breakdowns
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cutoff = (datetime.now() - timedelta(days=days_back)).isoformat()

        query = """
            SELECT * FROM predictions 
            WHERE actual_outcome IS NOT NULL
            AND prediction_timestamp > ?
            AND confidence >= ?
        """
        params: List[Any] = [cutoff, min_confidence]

        if league:
            query += " AND league = ?"
            params.append(league)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return {
                "total_predictions": 0,
                "accuracy": None,
                "brier_score": None,
                "calibration": None,
            }

        records = [self._row_to_record(row) for row in rows]

        # Overall accuracy
        correct = sum(1 for r in records if r.prediction_correct)
        total = len(records)
        accuracy = correct / total

        # Average Brier score
        brier_scores = [r.brier_score for r in records if r.brier_score is not None]
        avg_brier = sum(brier_scores) / len(brier_scores) if brier_scores else None

        # Calibration: group by predicted probability and check actual rate
        calibration = self._calculate_calibration(records)

        # Breakdown by confidence level
        high_conf = [r for r in records if r.confidence >= 0.70]
        med_conf = [r for r in records if 0.55 <= r.confidence < 0.70]
        low_conf = [r for r in records if r.confidence < 0.55]

        return {
            "total_predictions": total,
            "correct_predictions": correct,
            "accuracy": accuracy,
            "accuracy_pct": f"{accuracy:.1%}",
            "brier_score": avg_brier,
            "calibration": calibration,
            "by_confidence": {
                "high": {
                    "count": len(high_conf),
                    "accuracy": (
                        sum(1 for r in high_conf if r.prediction_correct)
                        / len(high_conf)
                        if high_conf
                        else None
                    ),
                },
                "medium": {
                    "count": len(med_conf),
                    "accuracy": (
                        sum(1 for r in med_conf if r.prediction_correct) / len(med_conf)
                        if med_conf
                        else None
                    ),
                },
                "low": {
                    "count": len(low_conf),
                    "accuracy": (
                        sum(1 for r in low_conf if r.prediction_correct) / len(low_conf)
                        if low_conf
                        else None
                    ),
                },
            },
        }

    def _calculate_calibration(self, records: List[PredictionRecord]) -> Dict[str, Any]:
        """
        Calculate calibration metrics.

        Good calibration means: when we say 70%, we're right 70% of the time.
        """
        # Bin predictions by probability assigned to predicted outcome
        bins = {
            "0-20%": {"count": 0, "correct": 0},
            "20-40%": {"count": 0, "correct": 0},
            "40-60%": {"count": 0, "correct": 0},
            "60-80%": {"count": 0, "correct": 0},
            "80-100%": {"count": 0, "correct": 0},
        }

        for record in records:
            if record.predicted_outcome is None:
                continue

            # Get probability we assigned to our predicted outcome
            probs = {
                "home": record.predicted_home_prob,
                "draw": record.predicted_draw_prob,
                "away": record.predicted_away_prob,
            }
            pred_prob = probs.get(record.predicted_outcome, 0)

            # Assign to bin
            if pred_prob < 20:
                bin_key = "0-20%"
            elif pred_prob < 40:
                bin_key = "20-40%"
            elif pred_prob < 60:
                bin_key = "40-60%"
            elif pred_prob < 80:
                bin_key = "60-80%"
            else:
                bin_key = "80-100%"

            bins[bin_key]["count"] += 1
            if record.prediction_correct:
                bins[bin_key]["correct"] += 1

        # Calculate actual accuracy per bin
        calibration_data = {}
        for bin_key, data in bins.items():
            if data["count"] > 0:
                actual_rate = data["correct"] / data["count"]
                calibration_data[bin_key] = {
                    "predictions": data["count"],
                    "correct": data["correct"],
                    "actual_rate": actual_rate,
                    "actual_pct": f"{actual_rate:.1%}",
                }
            else:
                calibration_data[bin_key] = {
                    "predictions": 0,
                    "correct": 0,
                    "actual_rate": None,
                    "actual_pct": "N/A",
                }

        return calibration_data

    def get_pending_results(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get predictions that need results fetched"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get predictions where match has passed but no result
        now = datetime.now().isoformat()
        cursor.execute(
            """
            SELECT match_id, home_team_name, away_team_name, league, match_date
            FROM predictions
            WHERE actual_outcome IS NULL
            AND match_date < ?
            ORDER BY match_date DESC
            LIMIT ?
        """,
            (now, limit),
        )

        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "match_id": row[0],
                "home_team": row[1],
                "away_team": row[2],
                "league": row[3],
                "match_date": row[4],
            }
            for row in rows
        ]

    def get_league_comparison(self) -> Dict[str, Dict[str, Any]]:
        """Compare accuracy across leagues"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT league,
                   COUNT(*) as total,
                   SUM(CASE WHEN prediction_correct = 1 THEN 1 ELSE 0 END) as correct,
                   AVG(brier_score) as avg_brier
            FROM predictions
            WHERE actual_outcome IS NOT NULL
            GROUP BY league
        """
        )

        rows = cursor.fetchall()
        conn.close()

        result = {}
        for row in rows:
            league, total, correct, avg_brier = row
            result[league] = {
                "total_predictions": total,
                "correct": correct,
                "accuracy": correct / total if total > 0 else None,
                "brier_score": avg_brier,
            }

        return result


# Convenience function to create prediction record from prediction result
def create_prediction_record(
    match: Dict[str, Any] | None = None,
    prediction: Dict[str, Any] | None = None,
    league: str | None = None,
    **kwargs,
) -> PredictionRecord:
    """
    Create a PredictionRecord from match data and prediction result.

    Supports two calling conventions:
    1) create_prediction_record(match, prediction, league)
    2) create_prediction_record(match_id=..., home_team=..., away_team=..., home_prob=..., ...)

    Returns:
        PredictionRecord ready to be stored
    """
    # If kwargs provided, prefer them (for backwards compatibility with enhanced_predictor usage)
    if kwargs:
        match_id = kwargs.get("match_id", 0)
        home_team_name = kwargs.get(
            "home_team", kwargs.get("home_team_name", "Unknown")
        )
        away_team_name = kwargs.get(
            "away_team", kwargs.get("away_team_name", "Unknown")
        )
        predicted_home = kwargs.get("home_prob", kwargs.get("home_win_prob", 33))
        predicted_draw = kwargs.get("draw_prob", kwargs.get("draw_probability", 33))
        predicted_away = kwargs.get("away_prob", kwargs.get("away_win_prob", 34))
        predicted_home_goals = kwargs.get("expected_home_goals", 1.5)
        predicted_away_goals = kwargs.get("expected_away_goals", 1.0)
        confidence = kwargs.get("confidence", 0.5)
        match_date = kwargs.get("match_date", "")
        league = kwargs.get("league", league)
        prediction_id = f"{match_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        return PredictionRecord(
            prediction_id=prediction_id,
            match_id=match_id,
            home_team_id=0,
            away_team_id=0,
            home_team_name=home_team_name,
            away_team_name=away_team_name,
            league=league or "unknown",
            match_date=match_date,
            predicted_home_prob=predicted_home,
            predicted_draw_prob=predicted_draw,
            predicted_away_prob=predicted_away,
            predicted_home_goals=predicted_home_goals,
            predicted_away_goals=predicted_away_goals,
            confidence=confidence,
            prediction_timestamp=datetime.now().isoformat(),
            model_version=kwargs.get("prediction_engine", "v4.2"),
            enhancements_applied=kwargs.get("phase1_enhancements", []),
        )

    # Original signature handling
    match_id = (match or {}).get("id", 0)
    home_team = (match or {}).get("homeTeam", {})
    away_team = (match or {}).get("awayTeam", {})

    prediction_id = f"{match_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    prediction = prediction or {}

    return PredictionRecord(
        prediction_id=prediction_id,
        match_id=match_id,
        home_team_id=home_team.get("id", 0),
        away_team_id=away_team.get("id", 0),
        home_team_name=home_team.get("name", "Unknown"),
        away_team_name=away_team.get("name", "Unknown"),
        league=league or "unknown",
        match_date=(match or {}).get("utcDate", ""),
        predicted_home_prob=prediction.get(
            "home_win_prob", prediction.get("home_win_probability", 33)
        ),
        predicted_draw_prob=prediction.get(
            "draw_prob", prediction.get("draw_probability", 33)
        ),
        predicted_away_prob=prediction.get(
            "away_win_prob", prediction.get("away_win_probability", 34)
        ),
        predicted_home_goals=prediction.get("expected_home_goals", 1.5),
        predicted_away_goals=prediction.get("expected_away_goals", 1.0),
        confidence=prediction.get("confidence", 0.5),
        prediction_timestamp=datetime.now().isoformat(),
        model_version=prediction.get("prediction_engine", "v4.2"),
        enhancements_applied=prediction.get("phase1_enhancements", []),
    )
