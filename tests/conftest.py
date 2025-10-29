"""Pytest configuration and shared fixtures."""

import pytest
import os
from typing import Dict, Any


@pytest.fixture
def mock_env_config() -> Dict[str, str]:
    """Mock environment variables for configuration testing."""
    return {
        "MELCLOUD_EMAIL": "test@example.com",
        "MELCLOUD_PASSWORD": "test_password_123",
        "MQTT_HOST": "test-mqtt-broker",
        "MQTT_PORT": "1883",
        "MQTT_USERNAME": "mqtt_user",
        "MQTT_PASSWORD": "mqtt_pass",
        "MQTT_BASE_TOPIC": "homeassistant",
        "POLL_INTERVAL": "60",
        "LOG_LEVEL": "INFO"
    }


@pytest.fixture
def set_env_config(mock_env_config):
    """Set environment variables for testing."""
    original_env = os.environ.copy()
    
    # Set test environment variables
    for key, value in mock_env_config.items():
        os.environ[key] = value
    
    yield mock_env_config
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def mock_ata_device_state() -> Dict[str, Any]:
    """Mock ATA device state from MELCloud API."""
    return {
        "power": True,
        "operationMode": "heat",
        "setTemperature": 22.0,
        "roomTemperature": 21.5,
        "fanSpeed": "auto",
        "vaneHorizontal": "auto",
        "vaneVertical": "auto",
        "isInError": False
    }


@pytest.fixture
def mock_atw_device_state() -> Dict[str, Any]:
    """Mock ATW device state from MELCloud API."""
    return {
        "id": "26f6ae21-8862-4ab2-a40a-3ea138c119fc",
        "givenDisplayName": "Värmepanna",
        "displayIcon": "Loft",
        "settings": [
            {"name": "Power", "value": "True"},
            {"name": "InStandbyMode", "value": "False"},
            {"name": "OperationMode", "value": "Heating"},
            {"name": "HasZone2", "value": "0"},
            {"name": "OperationModeZone1", "value": "HeatRoomTemperature"},
            {"name": "RoomTemperatureZone1", "value": "21"},
            {"name": "SetTemperatureZone1", "value": "21"},
            {"name": "ProhibitHotWater", "value": "False"},
            {"name": "TankWaterTemperature", "value": "51.5"},
            {"name": "SetTankWaterTemperature", "value": "53"},
            {"name": "HasCoolingMode", "value": "False"},
            {"name": "ForcedHotWaterMode", "value": "False"},
            {"name": "IsInError", "value": "False"},
            {"name": "ErrorCode", "value": ""}
        ],
        "macAddress": "282e89465b95",
        "timeZone": "Europe/Berlin",
        "rssi": -74,
        "ftcModel": 5,
        "schedule": None,
        "scheduleEnabled": False,
        "frostProtection": None,
        "overheatProtection": None,
        "holidayMode": None,
        "isConnected": True,
        "isInError": False,
        "capabilities": None
    }


@pytest.fixture
def mock_pymelcloud_device():
    """Mock pymelcloudhome Device object."""
    class MockDevice:
        def __init__(self):
            self.id = "test-device-123"
            self.given_display_name = "Test Climate Device"
            self.device_type = "ataunit"
    
    return MockDevice()
