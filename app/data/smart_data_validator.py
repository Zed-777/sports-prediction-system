#!/usr/bin/env python3
"""
Smart Data Validation & Quality Scoring v2.0
Intelligent validation system for maximum data reliability and confidence
"""

import logging
import statistics
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any, List


@dataclass
class ValidationResult:
    """Result of data validation"""
    is_valid: bool
    quality_score: float  # 0-100
    confidence_impact: float  # 0-1
    issues: list[str]
    warnings: list[str]
    enhancements: list[str]
    metadata: dict[str, Any]

@dataclass
class DataQualityMetrics:
    """Comprehensive data quality metrics"""
    completeness: float  # How complete is the data
    consistency: float   # How consistent across sources
    accuracy: float      # How accurate/realistic
    timeliness: float    # How recent/up-to-date
    reliability: float   # How reliable the source
    relevance: float     # How relevant to prediction

class SmartDataValidator:
    """
    Intelligent data validation system for sports prediction

    Validation Layers:
    1. Schema Validation - Data structure and types
    2. Business Logic Validation - Sports-specific rules
    3. Cross-Source Validation - Multi-source consistency
    4. Statistical Validation - Outlier detection
    5. Temporal Validation - Time-series consistency
    6. Contextual Validation - League/competition context
    """

    def __init__(self):
        # type: () -> None
        self.logger = logging.getLogger(__name__)
        self.validation_rules = self._load_validation_rules()
        self.historical_stats: dict[str, Any] = {}
        self.league_contexts = self._load_league_contexts()

    def _load_validation_rules(self) -> dict[str, Any]:
        """Load sports-specific validation rules"""
        return {
            'match_scores': {
                'min_score': 0,
                'max_score': 15,  # Realistic maximum for football
                'typical_range': (0, 5)
            },
            'team_performance': {
                'win_rate_range': (0.0, 1.0),
                'goal_average_range': (0.0, 5.0),
                'typical_goal_range': (0.5, 3.0)
            },
            'form_scores': {
                'range': (0.0, 100.0),
                'typical_range': (20.0, 80.0)
            },
            'confidence_bounds': {
                'min_confidence': 0.3,
                'max_confidence': 0.95,
                'typical_range': (0.4, 0.8)
            },
            'temporal_constraints': {
                'max_age_days': 365,  # Data older than 1 year is stale
                'min_matches': 3,     # Minimum matches for reliability
                'preferred_matches': 10
            }
        }

    def _load_league_contexts(self) -> dict[str, dict[str, Any]]:
        """Load league-specific context for validation"""
        return {
            'premier-league': {
                'typical_goals_per_match': 2.8,
                'home_advantage': 0.15,
                'competitive_balance': 0.7,
                'season_length': 38
            },
            'la-liga': {
                'typical_goals_per_match': 2.6,
                'home_advantage': 0.12,
                'competitive_balance': 0.6,
                'season_length': 38
            },
            'bundesliga': {
                'typical_goals_per_match': 3.1,
                'home_advantage': 0.14,
                'competitive_balance': 0.65,
                'season_length': 34
            },
            'serie-a': {
                'typical_goals_per_match': 2.5,
                'home_advantage': 0.10,
                'competitive_balance': 0.75,
                'season_length': 38
            },
            'ligue-1': {
                'typical_goals_per_match': 2.7,
                'home_advantage': 0.13,
                'competitive_balance': 0.5,
                'season_length': 38
            }
        }

    def comprehensive_validation(self, match_data: dict[str, Any],
                                data_sources: list[dict[str, Any]] | None = None) -> ValidationResult:
        """
        Perform comprehensive data validation across all layers

        Returns validation result with quality score and confidence impact
        """

        issues: List[str] = []
        warnings: List[str] = []
        enhancements: List[str] = []

        # Layer 1: Schema Validation
        schema_score = self._validate_schema(match_data, issues, warnings)

        # Layer 2: Business Logic Validation
        business_score = self._validate_business_logic(match_data, issues, warnings)

        # Layer 3: Cross-Source Validation (if multiple sources available)
        cross_source_score = self._validate_cross_source(match_data, data_sources, issues, warnings)

        # Layer 4: Statistical Validation
        statistical_score = self._validate_statistical(match_data, issues, warnings)

        # Layer 5: Temporal Validation
        temporal_score = self._validate_temporal(match_data, issues, warnings)

        # Layer 6: Contextual Validation
        contextual_score = self._validate_contextual(match_data, issues, warnings)

        # Calculate overall quality metrics
        quality_metrics = DataQualityMetrics(
            completeness=schema_score,
            consistency=cross_source_score,
            accuracy=business_score,
            timeliness=temporal_score,
            reliability=statistical_score,
            relevance=contextual_score
        )

        # Calculate overall quality score (weighted average)
        weights = {
            'completeness': 0.2,
            'consistency': 0.15,
            'accuracy': 0.25,
            'timeliness': 0.15,
            'reliability': 0.15,
            'relevance': 0.1
        }

        overall_score = sum(
            getattr(quality_metrics, metric) * weight
            for metric, weight in weights.items()
        )

        # Calculate confidence impact
        confidence_impact = self._calculate_confidence_impact(quality_metrics, issues, warnings)

        # Generate enhancement suggestions
        enhancements = self._generate_enhancements(quality_metrics, match_data)

        # Determine if data is valid
        is_valid = overall_score >= 50.0 and len([i for i in issues if 'CRITICAL' in i]) == 0

        return ValidationResult(
            is_valid=is_valid,
            quality_score=overall_score,
            confidence_impact=confidence_impact,
            issues=issues,
            warnings=warnings,
            enhancements=enhancements,
            metadata={
                'quality_metrics': quality_metrics,
                'validation_timestamp': datetime.now().isoformat(),
                'data_sources_count': len(data_sources) if data_sources else 1
            }
        )

    def _validate_schema(self, match_data: dict[str, Any], issues: list[str], warnings: list[str]) -> float:
        """Validate data schema and structure"""
        score = 100.0
        required_fields = ['home_team', 'away_team', 'date', 'league']

        # Check required fields
        missing_fields = [field for field in required_fields if not match_data.get(field)]
        if missing_fields:
            issues.append(f"CRITICAL: Missing required fields: {', '.join(missing_fields)}")
            score -= 30.0

        # Check data types
        if 'confidence' in match_data:
            try:
                confidence = float(match_data['confidence'])
                if not (0.0 <= confidence <= 1.0):
                    warnings.append("Confidence value outside normal range (0-1)")
                    score -= 5.0
            except (ValueError, TypeError):
                issues.append("Invalid confidence data type")
                score -= 10.0

        # Check performance analysis structure
        home_perf = match_data.get('home_performance_analysis', {})
        away_perf = match_data.get('away_performance_analysis', {})

        if not home_perf or not away_perf:
            warnings.append("Performance analysis data incomplete")
            score -= 15.0

        return max(score, 0.0)

    def _validate_business_logic(self, match_data: dict[str, Any], issues: list[str], warnings: list[str]) -> float:
        """Validate against sports-specific business rules"""
        score = 100.0

        # Validate goal statistics
        home_goals = match_data.get('expected_home_goals', 0)
        away_goals = match_data.get('expected_away_goals', 0)

        rules = self.validation_rules['match_scores']

        if home_goals < rules['min_score'] or home_goals > rules['max_score']:
            issues.append(f"Home goals ({home_goals}) outside realistic range")
            score -= 20.0
        elif not (rules['typical_range'][0] <= home_goals <= rules['typical_range'][1]):
            warnings.append(f"Home goals ({home_goals}) outside typical range")
            score -= 5.0

        if away_goals < rules['min_score'] or away_goals > rules['max_score']:
            issues.append(f"Away goals ({away_goals}) outside realistic range")
            score -= 20.0
        elif not (rules['typical_range'][0] <= away_goals <= rules['typical_range'][1]):
            warnings.append(f"Away goals ({away_goals}) outside typical range")
            score -= 5.0

        # Validate probabilities sum to ~100%
        home_prob = match_data.get('home_win_probability', 0)
        draw_prob = match_data.get('draw_probability', 0)
        away_prob = match_data.get('away_win_probability', 0)

        total_prob = home_prob + draw_prob + away_prob
        if abs(total_prob - 100.0) > 5.0:  # Allow 5% tolerance
            issues.append(f"Win probabilities don't sum to 100% (sum: {total_prob:.1f}%)")
            score -= 15.0
        elif abs(total_prob - 100.0) > 1.0:
            warnings.append(f"Minor probability inconsistency (sum: {total_prob:.1f}%)")
            score -= 2.0

        # Validate team performance metrics
        home_stats = match_data.get('home_performance_analysis', {}).get('home', {})
        away_stats = match_data.get('away_performance_analysis', {}).get('away', {})

        for team_name, stats in [('home', home_stats), ('away', away_stats)]:
            win_rate = stats.get('win_rate', 0)
            if not (0 <= win_rate <= 100):
                issues.append(f"{team_name} win rate ({win_rate}) outside valid range")
                score -= 10.0

            avg_goals = stats.get('avg_goals_for', 0)
            if avg_goals < 0 or avg_goals > 5:
                warnings.append(f"{team_name} average goals ({avg_goals}) seems unusual")
                score -= 3.0

        return max(score, 0.0)

    def _validate_cross_source(self, match_data: dict[str, Any],
                              data_sources: list[dict[str, Any]] | None,
                              issues: list[str], warnings: list[str]) -> float:
        """Validate consistency across multiple data sources"""

        if not data_sources or len(data_sources) < 2:
            return 80.0  # Default score when cross-validation not possible

        score = 100.0

        # Compare key metrics across sources
        consensus_metrics = self._calculate_consensus_metrics(data_sources)

        # Check for significant disagreements
        for metric, values in consensus_metrics.items():
            if len(values) < 2:
                continue

            std_dev = statistics.stdev(values)
            mean_val = statistics.mean(values)

            # Calculate coefficient of variation
            cv = std_dev / mean_val if mean_val != 0 else 0

            if cv > 0.3:  # High disagreement
                warnings.append(f"High disagreement between sources for {metric} (CV: {cv:.2f})")
                score -= 10.0
            elif cv > 0.15:  # Moderate disagreement
                warnings.append(f"Moderate disagreement between sources for {metric}")
                score -= 5.0

        return max(score, 0.0)

    def _validate_statistical(self, match_data: dict[str, Any], issues: list[str], warnings: list[str]) -> float:
        """Validate using statistical analysis and outlier detection"""
        score = 100.0

        # Z-score analysis for key metrics
        home_goals = match_data.get('expected_home_goals', 0)
        away_goals = match_data.get('expected_away_goals', 0)

        # Use league averages for comparison
        league = match_data.get('league', '').lower().replace(' ', '-')
        league_context = self.league_contexts.get(league, {})
        expected_avg = league_context.get('typical_goals_per_match', 2.7) / 2  # Per team

        # Calculate z-scores (simplified)
        home_z = abs(home_goals - expected_avg) / (expected_avg * 0.5)  # Assume std = 50% of mean
        away_z = abs(away_goals - expected_avg) / (expected_avg * 0.5)

        if home_z > 3.0:  # Very unusual
            warnings.append(f"Home goals expectation is statistical outlier (z={home_z:.1f})")
            score -= 10.0
        elif home_z > 2.0:
            warnings.append(f"Home goals expectation is unusual (z={home_z:.1f})")
            score -= 3.0

        if away_z > 3.0:
            warnings.append(f"Away goals expectation is statistical outlier (z={away_z:.1f})")
            score -= 10.0
        elif away_z > 2.0:
            warnings.append(f"Away goals expectation is unusual (z={away_z:.1f})")
            score -= 3.0

        # Validate form scores for reasonableness
        home_form = match_data.get('home_performance_analysis', {}).get('home', {}).get('weighted_form_score', 50)
        away_form = match_data.get('away_performance_analysis', {}).get('away', {}).get('weighted_form_score', 50)

        if abs(home_form - 50) > 40:  # Extreme form score
            warnings.append(f"Extreme home form score: {home_form}")
            score -= 5.0

        if abs(away_form - 50) > 40:
            warnings.append(f"Extreme away form score: {away_form}")
            score -= 5.0

        return max(score, 0.0)

    def _validate_temporal(self, match_data: dict[str, Any], issues: list[str], warnings: list[str]) -> float:
        """Validate temporal aspects and data freshness"""
        score = 100.0

        # Check data age
        try:
            match_date_str = match_data.get('date', '')
            match_date = datetime.strptime(match_date_str, '%Y-%m-%d')
            data_age = (datetime.now() - match_date).days

            if data_age > 30:  # Match data more than 30 days old
                warnings.append(f"Match data is {data_age} days old")
                score -= min(data_age - 30, 20)  # Penalize up to 20 points

        except ValueError:
            warnings.append("Invalid or missing match date")
            score -= 10.0

        # Check match history depth
        home_matches = match_data.get('home_performance_analysis', {}).get('home', {}).get('matches', 0)
        away_matches = match_data.get('away_performance_analysis', {}).get('away', {}).get('matches', 0)

        min_matches = self.validation_rules['temporal_constraints']['min_matches']
        preferred_matches = self.validation_rules['temporal_constraints']['preferred_matches']

        if home_matches < min_matches:
            warnings.append(f"Limited home team data: {home_matches} matches")
            score -= 15.0
        elif home_matches < preferred_matches:
            warnings.append(f"Suboptimal home team data: {home_matches} matches")
            score -= 5.0

        if away_matches < min_matches:
            warnings.append(f"Limited away team data: {away_matches} matches")
            score -= 15.0
        elif away_matches < preferred_matches:
            warnings.append(f"Suboptimal away team data: {away_matches} matches")
            score -= 5.0

        return max(score, 0.0)

    def _validate_contextual(self, match_data: dict[str, Any], issues: list[str], warnings: list[str]) -> float:
        """Validate contextual relevance and league-specific factors"""
        score = 100.0

        league = match_data.get('league', '').lower().replace(' ', '-')
        league_context = self.league_contexts.get(league)

        if not league_context:
            warnings.append(f"Unknown league context: {league}")
            score -= 10.0
            return max(score, 0.0)

        # Validate home advantage
        home_adv = match_data.get('home_performance_analysis', {}).get('home_advantage', 0)
        expected_home_adv = league_context['home_advantage']

        if abs(home_adv / 100 - expected_home_adv) > expected_home_adv:  # More than 100% deviation
            warnings.append(f"Home advantage ({home_adv:.1f}%) deviates from league norm ({expected_home_adv:.1%})")
            score -= 5.0

        # Validate goal expectations against league average
        total_expected_goals = match_data.get('expected_home_goals', 1) + match_data.get('expected_away_goals', 1)
        league_avg = league_context['typical_goals_per_match']

        if abs(total_expected_goals - league_avg) > league_avg * 0.5:  # More than 50% deviation
            warnings.append(f"Total expected goals ({total_expected_goals:.1f}) deviates significantly from league average ({league_avg:.1f})")
            score -= 8.0

        return max(score, 0.0)

    def _calculate_consensus_metrics(self, data_sources: list[dict[str, Any]]) -> dict[str, list[float]]:
        """Calculate consensus metrics across data sources"""
        consensus = defaultdict(list)

        for source in data_sources:
            if 'error' in source:
                continue

            # Extract comparable metrics
            if 'confidence_score' in source:
                consensus['confidence'].append(source['confidence_score'])

            # Add other comparable metrics as they become available
            # This would be expanded based on actual multi-source data structure

        return dict(consensus)

    def _calculate_confidence_impact(self, quality_metrics: DataQualityMetrics,
                                   issues: list[str], warnings: list[str]) -> float:
        """Calculate impact on prediction confidence based on data quality"""

        # Base confidence impact from quality metrics
        base_impact = (
            quality_metrics.completeness * 0.2 +
            quality_metrics.accuracy * 0.3 +
            quality_metrics.consistency * 0.2 +
            quality_metrics.reliability * 0.2 +
            quality_metrics.timeliness * 0.1
        ) / 100.0

        # Penalties for issues
        critical_issues = len([i for i in issues if 'CRITICAL' in i])
        other_issues = len(issues) - critical_issues
        warning_count = len(warnings)

        # Calculate penalties
        critical_penalty = critical_issues * 0.2  # 20% per critical issue
        issue_penalty = other_issues * 0.05      # 5% per other issue
        warning_penalty = warning_count * 0.02   # 2% per warning

        # Final confidence impact
        confidence_impact = max(0.3, base_impact - critical_penalty - issue_penalty - warning_penalty)

        return min(confidence_impact, 0.95)  # Cap at 95%

    def _generate_enhancements(self, quality_metrics: DataQualityMetrics,
                              match_data: dict[str, Any]) -> list[str]:
        """Generate suggestions for data enhancement"""
        enhancements = []

        if quality_metrics.completeness < 80:
            enhancements.append("Consider adding more comprehensive team performance data")

        if quality_metrics.timeliness < 70:
            enhancements.append("Update with more recent match data for better accuracy")

        if quality_metrics.consistency < 60:
            enhancements.append("Cross-validate with additional data sources")

        # Specific suggestions based on data gaps
        h2h_meetings = match_data.get('head_to_head_analysis', {}).get('total_meetings', 0)
        if h2h_meetings == 0:
            enhancements.append("Historical head-to-head data would significantly improve prediction accuracy")
        elif h2h_meetings < 5:
            enhancements.append("Additional head-to-head history would enhance confidence")

        home_matches = match_data.get('home_performance_analysis', {}).get('home', {}).get('matches', 0)
        away_matches = match_data.get('away_performance_analysis', {}).get('away', {}).get('matches', 0)

        if home_matches < 10:
            enhancements.append("More home team match history would improve reliability")

        if away_matches < 10:
            enhancements.append("More away team match history would improve reliability")

        # Enhanced data suggestions
        if 'injuries' not in match_data:
            enhancements.append("Player injury data would enhance prediction accuracy")

        if 'weather_conditions' not in match_data:
            enhancements.append("Weather conditions data would provide additional context")

        return enhancements

    def validate_and_enhance_confidence(self, match_data: dict[str, Any],
                                       current_confidence: float,
                                       data_sources: list[dict[str, Any]] | None = None) -> tuple[float, ValidationResult]:
        """
        Validate data and calculate enhanced confidence score

        Returns enhanced confidence and validation result
        """

        validation_result = self.comprehensive_validation(match_data, data_sources)

        # Calculate enhanced confidence
        base_confidence = current_confidence
        quality_multiplier = validation_result.confidence_impact

        # Apply quality-based enhancement
        enhanced_confidence = base_confidence * quality_multiplier

        # Bonus for high-quality data
        if validation_result.quality_score >= 90:
            enhanced_confidence *= 1.1  # 10% bonus for excellent data
        elif validation_result.quality_score >= 80:
            enhanced_confidence *= 1.05  # 5% bonus for good data

        # Cap the confidence
        enhanced_confidence = min(enhanced_confidence, 0.95)

        return enhanced_confidence, validation_result


# Example usage and testing
if __name__ == "__main__":
    validator = SmartDataValidator()

    # Example match data
    match_data = {
        'home_team': 'Arsenal',
        'away_team': 'Chelsea',
        'date': '2025-10-18',
        'league': 'Premier League',
        'confidence': 0.7,
        'expected_home_goals': 1.8,
        'expected_away_goals': 1.2,
        'home_win_probability': 45.0,
        'draw_probability': 25.0,
        'away_win_probability': 30.0,
        'home_performance_analysis': {
            'home': {'matches': 8, 'win_rate': 62.5, 'avg_goals_for': 2.1}
        },
        'away_performance_analysis': {
            'away': {'matches': 6, 'win_rate': 50.0, 'avg_goals_for': 1.5}
        },
        'head_to_head_analysis': {'total_meetings': 3}
    }

    # Validate and enhance
    enhanced_confidence, validation = validator.validate_and_enhance_confidence(match_data, 0.7)

    print("Original Confidence: 70.0%")
    print(f"Enhanced Confidence: {enhanced_confidence:.1%}")
    print(f"Quality Score: {validation.quality_score:.1f}/100")
    print(f"Validation Issues: {len(validation.issues)}")
    print(f"Validation Warnings: {len(validation.warnings)}")
    print(f"Enhancement Suggestions: {len(validation.enhancements)}")
