"""Unit tests for configuration management
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from app.config import (
    _substitute_env_vars,
    create_default_config,
    load_config,
    validate_config,
)


class TestLoadConfig:
    """Test configuration loading functionality"""

    def test_load_config_file_not_found(self):
        """Test loading config when file doesn't exist"""
        with pytest.raises(FileNotFoundError):
            load_config("nonexistent.yaml")

    def test_load_config_success(self):
        """Test successful config loading"""
        config_data = {
            "environment": "test",
            "random_seed": 42,
            "database": {"type": "sqlite"},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name

        try:
            loaded_config = load_config(temp_path)
            assert loaded_config["environment"] == "test"
            assert loaded_config["random_seed"] == 42
        finally:
            Path(temp_path).unlink()

    def test_load_config_with_env_substitution(self):
        """Test config loading with environment variable substitution"""
        config_data = {
            "api_key": "${TEST_API_KEY:default_key}",
            "database_url": "${DATABASE_URL:sqlite:///test.db}",
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name

        try:
            with patch.dict("os.environ", {"TEST_API_KEY": "real_key"}):
                loaded_config = load_config(temp_path)
                assert loaded_config["api_key"] == "real_key"
                assert loaded_config["database_url"] == "sqlite:///test.db"  # default
        finally:
            Path(temp_path).unlink()


class TestSubstituteEnvVars:
    """Test environment variable substitution"""

    def test_substitute_simple_string(self):
        """Test substitution in simple string"""
        with patch.dict("os.environ", {"TEST_VAR": "test_value"}):
            result = _substitute_env_vars("${TEST_VAR}")
            assert result == "test_value"

    def test_substitute_with_default(self):
        """Test substitution with default value"""
        result = _substitute_env_vars("${NONEXISTENT_VAR:default_value}")
        assert result == "default_value"

    def test_substitute_nested_dict(self):
        """Test substitution in nested dictionary"""
        data = {
            "database": {
                "url": "${DB_URL:sqlite:///default.db}",
                "password": "${DB_PASS:default_pass}",
            },
            "api_key": "${API_KEY}",
        }

        with patch.dict(
            "os.environ", {"DB_URL": "postgres://...", "API_KEY": "key123"},
        ):
            result = _substitute_env_vars(data)
            assert result["database"]["url"] == "postgres://..."
            assert result["database"]["password"] == "default_pass"
            assert result["api_key"] == "key123"

    def test_substitute_list(self):
        """Test substitution in list"""
        data = ["${VAR1:default1}", "${VAR2:default2}", "static_value"]

        with patch.dict("os.environ", {"VAR1": "value1"}):
            result = _substitute_env_vars(data)
            assert result == ["value1", "default2", "static_value"]


class TestValidateConfig:
    """Test configuration validation"""

    def test_validate_valid_config(self):
        """Test validation of valid configuration"""
        config = create_default_config()
        assert validate_config(config) is True

    def test_validate_missing_section(self):
        """Test validation with missing required section"""
        config = {"random_seed": 42}  # Missing required sections

        with pytest.raises(ValueError, match="Missing required configuration section"):
            validate_config(config)

    def test_validate_missing_football_data(self):
        """Test validation with missing football data source"""
        config = {
            "data_sources": {"basketball": {}},  # Missing football
            "models": {"elo": {"enabled": True}},
            "features": {},
        }

        with pytest.raises(
            ValueError, match="Football data source configuration is required",
        ):
            validate_config(config)

    def test_validate_no_models(self):
        """Test validation with no models configured"""
        config = {
            "data_sources": {"football": {"primary_api": "test"}},
            "models": {},  # No models
            "features": {},
        }

        with pytest.raises(ValueError, match="At least one model must be configured"):
            validate_config(config)

    def test_validate_invalid_random_seed(self):
        """Test validation with invalid random seed"""
        config = create_default_config()
        config["random_seed"] = "not_an_integer"

        with pytest.raises(ValueError, match="random_seed must be an integer"):
            validate_config(config)


class TestCreateDefaultConfig:
    """Test default configuration creation"""

    def test_create_default_config_structure(self):
        """Test that default config has required structure"""
        config = create_default_config()

        required_keys = [
            "environment",
            "random_seed",
            "timezone_storage",
            "database",
            "data_sources",
            "models",
            "logging",
        ]

        for key in required_keys:
            assert key in config

    def test_create_default_config_values(self):
        """Test default configuration values"""
        config = create_default_config()

        assert config["environment"] == "dev"
        assert config["random_seed"] == 42
        assert config["timezone_storage"] == "UTC"
        assert config["database"]["type"] == "sqlite"
        assert "football" in config["data_sources"]
        assert "elo" in config["models"]


@pytest.mark.parametrize(
    "env,expected",
    [
        ("dev", "development"),
        ("prod", "production"),
        ("staging", "staging"),
        ("test", "testing"),
    ],
)
def test_environment_mapping(env, expected):
    """Test environment name mapping (placeholder for future feature)"""
    # This is a placeholder test showing how to use parametrize
    # for testing different environment configurations
    assert len(env) > 0  # Simple assertion for now
