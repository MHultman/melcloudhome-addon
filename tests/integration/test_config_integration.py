"""
Integration test for configuration loading from Home Assistant Supervisor environment.

Tests T030: Configuration loads from mock Supervisor environment
"""

import pytest
from app.config import Configuration


def test_config_loads_from_supervisor_environment(monkeypatch):
    """Test that Configuration loads from environment variables like HA Supervisor provides."""
    # Simulate Home Assistant Supervisor environment variables
    supervisor_env = {
        "MELCLOUD_EMAIL": "test@example.com",
        "MELCLOUD_PASSWORD": "test_password_123",
        "MQTT_HOST": "core-mosquitto",
        "MQTT_PORT": "1883",
        "MQTT_USERNAME": "mqtt_user",
        "MQTT_PASSWORD": "mqtt_pass",
        "MQTT_BASE_TOPIC": "homeassistant",
        "POLL_INTERVAL": "45",
        "LOG_LEVEL": "DEBUG",
    }
    
    # Set environment variables
    for key, value in supervisor_env.items():
        monkeypatch.setenv(key, value)
    
    # Load configuration
    config = Configuration()
    
    # Verify all values loaded correctly
    assert config.melcloud_email == "test@example.com"
    assert config.melcloud_password == "test_password_123"
    assert config.mqtt_host == "core-mosquitto"
    assert config.mqtt_port == 1883
    assert config.mqtt_username == "mqtt_user"
    assert config.mqtt_password == "mqtt_pass"
    assert config.mqtt_base_topic == "homeassistant"
    assert config.poll_interval == 45
    assert config.log_level == "DEBUG"


def test_config_uses_defaults_when_optional_values_missing(monkeypatch):
    """Test that Configuration uses sensible defaults for optional values."""
    # Only set required values
    monkeypatch.setenv("MELCLOUD_EMAIL", "test@example.com")
    monkeypatch.setenv("MELCLOUD_PASSWORD", "test_password_123")
    monkeypatch.setenv("MQTT_HOST", "core-mosquitto")
    
    # Load configuration
    config = Configuration()
    
    # Verify required values loaded
    assert config.melcloud_email == "test@example.com"
    assert config.melcloud_password == "test_password_123"
    assert config.mqtt_host == "core-mosquitto"
    
    # Verify defaults applied
    assert config.mqtt_port == 1883
    assert config.mqtt_username is None
    assert config.mqtt_password is None
    assert config.mqtt_base_topic == "homeassistant"
    assert config.poll_interval == 60
    assert config.log_level == "INFO"


def test_config_validation_rejects_invalid_email(monkeypatch):
    """Test that Configuration validation rejects invalid email addresses."""
    monkeypatch.setenv("MELCLOUD_EMAIL", "not-an-email")
    monkeypatch.setenv("MELCLOUD_PASSWORD", "test_password_123")
    monkeypatch.setenv("MQTT_HOST", "core-mosquitto")
    
    # Should raise validation error
    with pytest.raises(Exception) as exc_info:
        Configuration()
    
    assert "email" in str(exc_info.value).lower() or "validation" in str(exc_info.value).lower()


def test_config_validation_rejects_invalid_port(monkeypatch):
    """Test that Configuration validation rejects invalid port numbers."""
    monkeypatch.setenv("MELCLOUD_EMAIL", "test@example.com")
    monkeypatch.setenv("MELCLOUD_PASSWORD", "test_password_123")
    monkeypatch.setenv("MQTT_HOST", "core-mosquitto")
    monkeypatch.setenv("MQTT_PORT", "99999")  # Invalid port
    
    # Should raise validation error
    with pytest.raises(Exception) as exc_info:
        Configuration()
    
    assert "port" in str(exc_info.value).lower() or "validation" in str(exc_info.value).lower()


def test_config_validation_rejects_invalid_poll_interval(monkeypatch):
    """Test that Configuration validation rejects poll intervals outside valid range."""
    monkeypatch.setenv("MELCLOUD_EMAIL", "test@example.com")
    monkeypatch.setenv("MELCLOUD_PASSWORD", "test_password_123")
    monkeypatch.setenv("MQTT_HOST", "core-mosquitto")
    monkeypatch.setenv("POLL_INTERVAL", "5")  # Too short (min is 10)
    
    # Should raise validation error
    with pytest.raises(Exception) as exc_info:
        Configuration()
    
    assert "poll" in str(exc_info.value).lower() or "validation" in str(exc_info.value).lower()


def test_config_validation_rejects_invalid_log_level(monkeypatch):
    """Test that Configuration validation rejects invalid log levels."""
    monkeypatch.setenv("MELCLOUD_EMAIL", "test@example.com")
    monkeypatch.setenv("MELCLOUD_PASSWORD", "test_password_123")
    monkeypatch.setenv("MQTT_HOST", "core-mosquitto")
    monkeypatch.setenv("LOG_LEVEL", "INVALID")
    
    # Should raise validation error
    with pytest.raises(Exception) as exc_info:
        Configuration()
    
    assert "log" in str(exc_info.value).lower() or "validation" in str(exc_info.value).lower()


def test_config_allows_boundary_values(monkeypatch):
    """Test that Configuration accepts boundary values for poll_interval."""
    # Test minimum poll interval (10 seconds)
    monkeypatch.setenv("MELCLOUD_EMAIL", "test@example.com")
    monkeypatch.setenv("MELCLOUD_PASSWORD", "test_password_123")
    monkeypatch.setenv("MQTT_HOST", "core-mosquitto")
    monkeypatch.setenv("POLL_INTERVAL", "10")
    
    config = Configuration()
    assert config.poll_interval == 10
    
    # Test maximum poll interval (600 seconds = 10 minutes)
    monkeypatch.setenv("POLL_INTERVAL", "600")
    config = Configuration()
    assert config.poll_interval == 600


def test_config_missing_required_values_raises_error(monkeypatch):
    """Test that Configuration raises error when required values are missing."""
    # Clear all environment variables
    for key in ["MELCLOUD_EMAIL", "MELCLOUD_PASSWORD", "MQTT_HOST"]:
        monkeypatch.delenv(key, raising=False)
    
    # Should raise validation error for missing required fields
    with pytest.raises(Exception):
        Configuration()
