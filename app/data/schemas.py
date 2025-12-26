"""
Data validation schemas
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of data validation"""

    is_valid: bool
    errors: list[str]
    warnings: list[str]


def validate_raw_data(data: Any, data_type: str) -> ValidationResult:
    """
    Validate raw data against expected schema

    Args:
        data: List of data records
        data_type: Type of data (matches, teams, players, etc.)

    Returns:
        ValidationResult with validation status and any errors
    """
    errors: List[str] = []
    warnings: List[str] = []

    if not isinstance(data, list):
        errors.append("Data must be a list")
        return ValidationResult(False, errors, warnings)

    if len(data) == 0:
        warnings.append("Data list is empty")
        return ValidationResult(True, errors, warnings)

    # Validate based on data type
    if data_type == "matches":
        errors.extend(_validate_matches(data))
    elif data_type == "teams":
        errors.extend(_validate_teams(data))
    elif data_type == "players":
        errors.extend(_validate_players(data))
    else:
        warnings.append(f"Unknown data type: {data_type}")

    is_valid = len(errors) == 0
    return ValidationResult(is_valid, errors, warnings)


def _validate_matches(data: Any) -> List[str]:
    """Validate match data"""
    errors = []
    required_fields = ["home_team", "away_team", "date"]

    for i, match in enumerate(data):
        if not isinstance(match, dict):
            errors.append(f"Match {i} is not a dictionary")
            continue

        for field in required_fields:
            if field not in match:
                errors.append(f"Match {i} missing required field: {field}")
            elif match[field] is None or match[field] == "":
                errors.append(f"Match {i} has empty {field}")

    return errors


def _validate_teams(data: Any) -> List[str]:
    """Validate team data"""
    errors = []
    required_fields = ["name"]

    for i, team in enumerate(data):
        if not isinstance(team, dict):
            errors.append(f"Team {i} is not a dictionary")
            continue

        for field in required_fields:
            if field not in team:
                errors.append(f"Team {i} missing required field: {field}")
            elif team[field] is None or team[field] == "":
                errors.append(f"Team {i} has empty {field}")

    return errors


def _validate_players(data: Any) -> List[str]:
    """Validate player data"""
    errors = []
    required_fields = ["name", "team"]

    for i, player in enumerate(data):
        if not isinstance(player, dict):
            errors.append(f"Player {i} is not a dictionary")
            continue

        for field in required_fields:
            if field not in player:
                errors.append(f"Player {i} missing required field: {field}")
            elif player[field] is None or player[field] == "":
                errors.append(f"Player {i} has empty {field}")

    return errors
