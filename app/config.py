"""
Configuration management for the Sports Prediction System
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

import yaml


@dataclass
class DatabaseConfig:
    """Database configuration settings"""

    type: str = "sqlite"
    path: str = "data/sports_predictions.db"
    host: str | None = None
    port: int | None = None
    username: str | None = None
    password: str | None = None
    database: str | None = None


@dataclass
class APIConfig:
    """API configuration for data sources"""

    primary_api: str
    secondary_api: str
    backup_csv: str
    features: list[str] = field(default_factory=list)


@dataclass
class ModelConfig:
    """Model configuration settings"""

    enabled: bool = True
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass
class Config:
    """Main configuration class"""

    environment: str = "dev"
    random_seed: int = 42
    timezone_storage: str = "UTC"
    timezone_display: str = "Europe/Madrid"
    language_default: str = "en"
    language_supported: list[str] = field(default_factory=lambda: ["en", "es"])

    # Nested configurations
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    data_sources: dict[str, Any] = field(default_factory=dict)
    models: dict[str, ModelConfig] = field(default_factory=dict)
    features: dict[str, Any] = field(default_factory=dict)
    monitoring: dict[str, Any] = field(default_factory=dict)
    reporting: dict[str, Any] = field(default_factory=dict)
    logging: dict[str, Any] = field(default_factory=dict)
    data_engineering: dict[str, Any] = field(default_factory=dict)


def load_config(config_path: str = "config/settings.yaml") -> dict[str, Any]:
    """
    Load configuration from YAML file with environment variable substitution.

    Args:
        config_path: Path to the configuration file

    Returns:
        Dictionary containing the configuration

    Raises:
        FileNotFoundError: If configuration file doesn't exist
        yaml.YAMLError: If YAML parsing fails
    """
    config_file = Path(config_path)

    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    try:
        with open(config_file, encoding="utf-8") as f:
            config_data = yaml.safe_load(f)
        # Ensure the loaded YAML is a dict for typing purposes
        config_data = cast(dict[str, Any], config_data or {})

        # Substitute environment variables
        config_data = cast(dict[str, Any], _substitute_env_vars(config_data))

        # Load environment-specific overrides
        env = config_data.get("environment", "dev")
        env_config_path = config_file.parent / f"settings.{env}.yaml"

        if env_config_path.exists():
            with open(env_config_path, encoding="utf-8") as f:
                env_config = yaml.safe_load(f)
            env_config = cast(dict[str, Any], env_config or {})
            config_data = _merge_configs(config_data, env_config)

        return config_data

    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Error parsing configuration file: {e}") from e


def _substitute_env_vars(data: Any) -> Any:
    """
    Recursively substitute environment variables in configuration data.

    Variables should be in format: ${ENV_VAR_NAME:default_value}
    """
    if isinstance(data, dict):
        return {key: _substitute_env_vars(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [_substitute_env_vars(item) for item in data]
    elif isinstance(data, str):
        # Simple environment variable substitution
        if data.startswith("${") and data.endswith("}"):
            var_spec = data[2:-1]
            if ":" in var_spec:
                var_name, default_value = var_spec.split(":", 1)
                return os.getenv(var_name, default_value)
            else:
                return os.getenv(var_spec, data)
        return data
    else:
        return data


def _merge_configs(
    base_config: dict[str, Any], override_config: dict[str, Any]
) -> dict[str, Any]:
    """
    Merge two configuration dictionaries, with override_config taking precedence.
    """
    merged = base_config.copy()

    for key, value in override_config.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _merge_configs(merged[key], value)
        else:
            merged[key] = value

    return merged


def get_env_config() -> dict[str, str]:
    """
    Get environment-specific configuration from environment variables.

    Returns:
        Dictionary of environment variables relevant to the application
    """
    env_vars = {}

    # Database configuration
    if "DATABASE_URL" in os.environ:
        env_vars["database_url"] = os.environ["DATABASE_URL"]

    # API keys
    api_keys = [
        "FOOTBALL_DATA_API_KEY",
        "API_FOOTBALL_KEY",
        "SPORTSDATA_API_KEY",
        "SPORTSRADAR_API_KEY",
        "OPENMETEO_API_KEY",
        "ODDS_API_KEY",
    ]

    for key in api_keys:
        if key in os.environ:
            env_vars[key.lower()] = os.environ[key]

    # Other configuration
    other_vars = [
        "ENVIRONMENT",
        "LOG_LEVEL",
        "SLACK_WEBHOOK_URL",
        "EMAIL_SMTP_HOST",
        "EMAIL_SMTP_PORT",
        "EMAIL_USERNAME",
        "EMAIL_PASSWORD",
    ]

    for key in other_vars:
        if key in os.environ:
            env_vars[key.lower()] = os.environ[key]

    return env_vars


def validate_config(config: dict[str, Any]) -> bool:
    """
    Validate configuration settings.

    Args:
        config: Configuration dictionary

    Returns:
        True if configuration is valid

    Raises:
        ValueError: If configuration is invalid
    """
    required_sections = ["data_sources", "models", "features"]

    for section in required_sections:
        if section not in config:
            raise ValueError(f"Missing required configuration section: {section}")

    # Validate data sources
    if "football" not in config["data_sources"]:
        raise ValueError("Football data source configuration is required")

    # Validate model configuration
    if not config.get("models"):
        raise ValueError("At least one model must be configured")

    # Validate random seed
    if not isinstance(config.get("random_seed", 42), int):
        raise ValueError("random_seed must be an integer")

    return True


def create_default_config() -> dict[str, Any]:
    """
    Create a default configuration dictionary.

    Returns:
        Default configuration dictionary
    """
    return {
        "environment": "dev",
        "random_seed": 42,
        "timezone_storage": "UTC",
        "timezone_display": "Europe/Madrid",
        "language_default": "en",
        "language_supported": ["en", "es"],
        "database": {"type": "sqlite", "path": "data/sports_predictions.db"},
        "data_sources": {
            "football": {
                "primary_api": "https://www.football-data.org/",
                "secondary_api": "https://www.api-football.com/",
                "backup_csv": "https://www.kaggle.com/datasets/hugomathien/soccer",
                "features": [
                    "match_results",
                    "team_stats",
                    "player_stats",
                    "injuries",
                    "fixtures",
                ],
            }
        },
        "models": {"elo": {"enabled": True}, "ensemble": {"enabled": True}},
        "features": {
            # Default feature toggles and small feature config used by tests
            "enabled_features": ["home_away_form", "recent_lineups", "market_odds"],
            "feature_window_days": 90,
        },
        "logging": {"level": "INFO", "format": "json", "location": "logs/"},
    }


# Ensure configuration directory exists
def ensure_config_directory() -> None:
    """Ensure the configuration directory exists"""
    config_dir = Path("config")
    config_dir.mkdir(exist_ok=True)

    # Create schemas directories
    (config_dir / "schemas" / "raw").mkdir(parents=True, exist_ok=True)
    (config_dir / "schemas" / "processed").mkdir(parents=True, exist_ok=True)
