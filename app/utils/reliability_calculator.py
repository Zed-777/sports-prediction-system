"""Reliability and calibration utilities for prediction outputs."""

from __future__ import annotations

from typing import Any


def _clamp(value: float, lower: float, upper: float) -> float:
    """Clamp *value* to the inclusive range [lower, upper]."""
    return max(lower, min(value, upper))


class ReliabilityCalculator:
    """Compute reliability metrics and probability calibrations."""

    _LEVELS: list[tuple[float, str, str, str]] = [
        (
            88.0,
            "Very High",
            "Highly reliable prediction – ideal for confident usage.",
            "🟢",
        ),
        (78.0, "High", "Reliable outlook with minor variance expected.", "🟢"),
        (
            68.0,
            "Moderate",
            "Balanced reliability – treat as guidance with monitoring.",
            "🟡",
        ),
        (58.0, "Limited", "Limited reliability – supplement with manual review.", "🟠"),
        (0.0, "Low", "Low reliability – informational use only.", "🔴"),
    ]

    def calculate(
        self, prediction: dict[str, Any], enhanced_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Return reliability metrics by blending confidence, data quality, and coverage."""

        confidence = float(prediction.get("confidence", 0.6))
        data_quality = float(enhanced_data.get("data_quality_score", 70.0)) / 100.0
        probabilities = self._extract_probabilities(prediction)
        clarity_component = self._calculate_probability_clarity(probabilities)
        h2h_component = self._calculate_h2h_component(prediction)
        freshness_component = self._calculate_freshness_component(
            enhanced_data, prediction
        )

        score = (
            confidence * 0.4
            + data_quality * 0.25
            + clarity_component * 0.15
            + h2h_component * 0.1
            + freshness_component * 0.1
        ) * 100.0

        level, recommendation, emoji = self._resolve_level(score)
        confidence_intervals = self._build_confidence_intervals(probabilities, score)

        factors = {
            "model_confidence": round(confidence * 100.0, 1),
            "data_quality": round(data_quality * 100.0, 1),
            "probability_clarity": round(clarity_component * 100.0, 1),
            "h2h_depth": round(h2h_component * 100.0, 1),
            "data_freshness": round(freshness_component * 100.0, 1),
        }

        notes: list[str] = []
        if clarity_component < 0.35:
            notes.append(
                "Probability distribution fairly flat; monitor for volatility."
            )
        if h2h_component < 0.25:
            notes.append("Head-to-head sample is limited – emphasis on recent form.")
        if factors["data_quality"] < 70:
            notes.append("Data quality below optimal threshold; confidence capped.")

        return {
            "score": round(score, 1),
            "level": level,
            "indicator": f"{emoji} {level}",
            "recommendation": recommendation,
            "confidence_intervals": confidence_intervals,
            "spread_points": round(self._probability_spread(probabilities) * 100.0, 1),
            "factors": factors,
            "primary_driver": self._primary_driver(factors),
            "notes": notes,
        }

    def apply_calibration(
        self,
        prediction: dict[str, Any],
        reliability_metrics: dict[str, Any],
    ) -> dict[str, Any]:
        """Blend probabilities toward neutral anchor when reliability is limited."""

        probabilities = self._extract_probabilities(prediction)
        if not probabilities:
            return {
                "applied": False,
                "probabilities": {},
                "notes": ["No probability data available for calibration."],
            }

        reliability_score = float(reliability_metrics.get("score", 65.0))
        shrink_factor = _clamp((80.0 - reliability_score) / 140.0, 0.0, 0.45)
        neutral_anchor = 1.0 / 3.0

        # Preserve the exact pre-calibration fractions for transparency
        pre_calibration = [float(p) for p in probabilities]

        calibrated: list[float] = []
        if shrink_factor > 0.0:
            for prob in probabilities:
                calibrated.append(
                    (1.0 - shrink_factor) * prob + shrink_factor * neutral_anchor
                )
        else:
            calibrated = probabilities[:]

        total = sum(calibrated)
        if total <= 0:
            calibrated = [neutral_anchor, neutral_anchor, neutral_anchor]
            total = sum(calibrated)
        calibrated = [value / total for value in calibrated]
        calibrated_percents = [round(value * 100.0, 2) for value in calibrated]
        original_percents = [round(value * 100.0, 2) for value in probabilities]

        pre_calibration_floats = [round(v, 6) for v in pre_calibration]

        notes: list[str] = []
        if shrink_factor > 0.0:
            notes.append(
                f"Applied {shrink_factor * 100.0:.1f}% shrink toward neutral due to reliability score {reliability_score:.1f}."
            )

        return {
            "applied": shrink_factor > 0.0,
            "shrink_factor": round(shrink_factor, 3),
            "probabilities": {
                "home_win_prob": calibrated_percents[0],
                "draw_prob": calibrated_percents[1],
                "away_win_prob": calibrated_percents[2],
            },
            "original_probabilities": {
                "home_win_prob": original_percents[0],
                "draw_prob": original_percents[1],
                "away_win_prob": original_percents[2],
            },
            "pre_calibration_probabilities": {
                "home_win_prob": pre_calibration_floats[0],
                "draw_prob": pre_calibration_floats[1],
                "away_win_prob": pre_calibration_floats[2],
            },
            "neutral_anchor": round(neutral_anchor * 100.0, 1),
            "notes": notes,
        }

    def fallback_metrics(self) -> dict[str, Any]:
        """Return conservative metrics for fallback scenarios."""

        return {
            "score": 48.0,
            "level": "Low",
            "indicator": "🔴 Low",
            "recommendation": "Fallback prediction – informational use only.",
            "confidence_intervals": {},
            "spread_points": 0.0,
            "factors": {},
            "primary_driver": "insufficient_data",
            "notes": ["Reliability defaults applied due to missing data."],
        }

    @staticmethod
    def _extract_probabilities(prediction: dict[str, Any]) -> list[float]:
        """Return probabilities as unit fractions (0-1)."""

        keys = [
            ("home_win_prob", "home_win_probability"),
            ("draw_prob", "draw_probability"),
            ("away_win_prob", "away_win_probability"),
        ]

        fractions: list[float] = []
        for primary, secondary in keys:
            value = prediction.get(primary)
            if value is None:
                value = prediction.get(secondary)
            if value is None:
                return []
            fractions.append(float(value) / 100.0 if value > 1.0 else float(value))
        return fractions

    @staticmethod
    def _calculate_probability_clarity(probabilities: list[float]) -> float:
        if len(probabilities) != 3:
            return 0.35
        ordered = sorted(probabilities, reverse=True)
        spread = ordered[0] - ordered[1]
        return _clamp(spread / 0.25, 0.0, 1.0)

    @staticmethod
    def _probability_spread(probabilities: list[float]) -> float:
        if len(probabilities) != 3:
            return 0.0
        return max(probabilities) - min(probabilities)

    @staticmethod
    def _calculate_h2h_component(prediction: dict[str, Any]) -> float:
        h2h = prediction.get("head_to_head_analysis", {}) or {}
        meetings = float(h2h.get("total_meetings", 0.0))
        return _clamp(meetings / 10.0, 0.0, 1.0)

    @staticmethod
    def _calculate_freshness_component(
        enhanced_data: dict[str, Any], prediction: dict[str, Any]
    ) -> float:
        processing_time = enhanced_data.get("processing_time") or prediction.get(
            "processing_time"
        )
        if processing_time is None:
            return 0.7
        try:
            processing_time = float(processing_time)
        except (TypeError, ValueError):
            return 0.7
        if processing_time < 0.6:
            return 1.0
        if processing_time < 1.2:
            return 0.85
        if processing_time < 2.0:
            return 0.7
        return 0.55

    def _resolve_level(self, score: float) -> tuple[str, str, str]:
        for threshold, level, description, emoji in self._LEVELS:
            if score >= threshold:
                return level, description, emoji
        return "Low", self._LEVELS[-1][2], self._LEVELS[-1][3]

    @staticmethod
    def _build_confidence_intervals(
        probabilities: list[float], score: float
    ) -> dict[str, tuple[float, float] | float]:
        if len(probabilities) != 3:
            return {}
        margin = _clamp((100.0 - score) / 100.0 * 0.12, 0.025, 0.14)
        labels = ["home", "draw", "away"]
        intervals: dict[str, tuple[float, float] | float] = {}
        for label, prob in zip(labels, probabilities, strict=True):
            lower = _clamp(prob - margin, 0.0, 1.0)
            upper = _clamp(prob + margin, 0.0, 1.0)
            intervals[label] = (round(lower * 100.0, 1), round(upper * 100.0, 1))
        intervals["margin_percent"] = round(margin * 100.0, 2)
        return intervals

    @staticmethod
    def _primary_driver(factors: dict[str, float]) -> str | None:
        if not factors:
            return None
        best_key, _ = max(factors.items(), key=lambda item: item[1])
        return best_key
