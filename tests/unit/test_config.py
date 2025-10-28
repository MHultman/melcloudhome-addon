"""Unit tests for configuration module."""

import pytest
import os
from pydantic import ValidationError

from app.config import load_configuration


def test_valid_configuration_loads_successfully(set_env_config):
    """Test that valid configuration loads without errors."""
    config = load_configuration()
    
    assert config.melcloud_email == "test@example.com"
    assert config.melcloud_password == "test_password_123"
    assert config.mqtt_host == "test-mqtt-broker"
    assert config.mqtt_port == 1883
    assert config.poll_interval == 60
    assert config.log_level == "INFO"


def test_invalid_email_raises_validation_error():
    """Test that invalid email format raises ValidationError."""
    os.environ["MELCLOUD_EMAIL"] = "not-an-email"
    os.environ["MELCLOUD_PASSWORD"] = "password123"
    
    with pytest.raises((ValidationError, ValueError)):
        load_configuration()


def test_missing_required_field_raises_error():
    """Test that missing required fields are detected."""
    # Clear required environment variable
    if "MELCLOUD_EMAIL" in os.environ:
        del os.environ["MELCLOUD_EMAIL"]
    
    with pytest.raises((ValidationError, ValueError)):
        load_configuration()


def test_default_values_applied_correctly():
    """Test that default values are applied for optional fields."""
    # Set only required fields
    os.environ["MELCLOUD_EMAIL"] = "test@example.com"
    os.environ["MELCLOUD_PASSWORD"] = "password123"
    
    config = load_configuration()
    
    # Check defaults
    assert config.mqtt_host == "core-mosquitto"
    assert config.mqtt_port == 1883
    assert config.mqtt_base_topic == "homeassistant"
    assert config.poll_interval == 60
    assert config.log_level == "INFO"


def test_invalid_log_level_raises_error():
    """Test that invalid log level raises ValidationError."""
    os.environ["MELCLOUD_EMAIL"] = "test@example.com"
    os.environ["MELCLOUD_PASSWORD"] = "password123"
    os.environ["LOG_LEVEL"] = "INVALID_LEVEL"
    
    with pytest.raises((ValidationError, ValueError)):
        load_configuration()


def test_log_level_case_insensitive(set_env_config):
    """Test that log level is case-insensitive."""
    os.environ["LOG_LEVEL"] = "debug"
    
    config = load_configuration()
    assert config.log_level == "DEBUG"


def test_poll_interval_validation(set_env_config):
    """Test poll interval is validated within range."""
    # Test below minimum
    os.environ["POLL_INTERVAL"] = "5"
    with pytest.raises((ValidationError, ValueError)):
        load_configuration()
    
    # Test above maximum
    os.environ["POLL_INTERVAL"] = "700"
    with pytest.raises((ValidationError, ValueError)):
        load_configuration()
    
    # Test valid range
    os.environ["POLL_INTERVAL"] = "30"
    config = load_configuration()
    assert config.poll_interval == 30


def test_mqtt_base_topic_trailing_slash_removed(set_env_config):
    """Test that trailing slash is removed from MQTT base topic."""
    os.environ["MQTT_BASE_TOPIC"] = "homeassistant/"
    
    config = load_configuration()
    assert config.mqtt_base_topic == "homeassistant"


def test_get_safe_summary_masks_credentials(set_env_config):
    """Test that credentials are masked in summary."""
    config = load_configuration()
    summary = config.get_safe_summary()
    
    assert summary["melcloud_password"] == "***REDACTED***"
    assert summary["mqtt_password"] == "***REDACTED***"
    assert summary["melcloud_email"] == "test@example.com"  # Email not masked
