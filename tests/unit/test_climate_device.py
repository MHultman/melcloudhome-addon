"""Unit tests for ClimateDevice model."""

import pytest
from app.models.climate_device import ClimateDevice


def test_climate_device_from_pymelcloud_device(mock_pymelcloud_device, mock_ata_device_state):
    """Test creating ClimateDevice from pymelcloudhome Device."""
    device = ClimateDevice.from_pymelcloud_device(mock_pymelcloud_device, mock_ata_device_state)
    
    assert device.device_id == "test-device-123"
    assert device.device_name == "Test Climate Device"
    assert device.device_type == "ataunit"
    assert device.online == True
    assert device.state == mock_ata_device_state


def test_climate_device_ata_power_state(mock_pymelcloud_device, mock_ata_device_state):
    """Test ATA device power state extraction."""
    device = ClimateDevice.from_pymelcloud_device(mock_pymelcloud_device, mock_ata_device_state)
    
    assert device.get_power() == True
    
    # Test with power off
    mock_ata_device_state["power"] = False
    device = ClimateDevice.from_pymelcloud_device(mock_pymelcloud_device, mock_ata_device_state)
    assert device.get_power() == False


def test_climate_device_ata_temperatures(mock_pymelcloud_device, mock_ata_device_state):
    """Test ATA device temperature extraction."""
    device = ClimateDevice.from_pymelcloud_device(mock_pymelcloud_device, mock_ata_device_state)
    
    assert device.get_temperature() == 21.5
    assert device.get_target_temperature() == 22.0


def test_climate_device_atw_power_state(mock_atw_device_state):
    """Test ATW device power state extraction from settings array."""
    class MockATWDevice:
        id = "test-atw-123"
        given_display_name = "Test ATW"
        device_type = "atwunit"
    
    device = ClimateDevice.from_pymelcloud_device(MockATWDevice(), mock_atw_device_state)
    
    assert device.get_power() == True


def test_climate_device_atw_temperatures(mock_atw_device_state):
    """Test ATW device temperature extraction from settings array."""
    class MockATWDevice:
        id = "test-atw-123"
        given_display_name = "Test ATW"
        device_type = "atwunit"
    
    device = ClimateDevice.from_pymelcloud_device(MockATWDevice(), mock_atw_device_state)
    
    assert device.get_temperature() == 21.0  # RoomTemperatureZone1
    assert device.get_target_temperature() == 21.0  # SetTemperatureZone1
    assert device.get_tank_temperature() == 51.5  # TankWaterTemperature
    assert device.get_tank_target_temperature() == 53.0  # SetTankWaterTemperature


def test_climate_device_atw_zone2_detection(mock_atw_device_state):
    """Test ATW zone 2 detection."""
    class MockATWDevice:
        id = "test-atw-123"
        given_display_name = "Test ATW"
        device_type = "atwunit"
    
    device = ClimateDevice.from_pymelcloud_device(MockATWDevice(), mock_atw_device_state)
    
    # Default has HasZone2 = "0"
    assert device.has_zone_2() == False
    
    # Change to HasZone2 = "1"
    for setting in mock_atw_device_state["settings"]:
        if setting["name"] == "HasZone2":
            setting["value"] = "1"
            break
    
    device = ClimateDevice.from_pymelcloud_device(MockATWDevice(), mock_atw_device_state)
    assert device.has_zone_2() == True


def test_climate_device_error_detection_ata(mock_pymelcloud_device, mock_ata_device_state):
    """Test error detection for ATA devices."""
    mock_ata_device_state["isInError"] = True
    device = ClimateDevice.from_pymelcloud_device(mock_pymelcloud_device, mock_ata_device_state)
    
    assert device.is_in_error() == True


def test_climate_device_error_detection_atw(mock_atw_device_state):
    """Test error detection for ATW devices."""
    class MockATWDevice:
        id = "test-atw-123"
        given_display_name = "Test ATW"
        device_type = "atwunit"
    
    # Change IsInError to "True" in settings
    for setting in mock_atw_device_state["settings"]:
        if setting["name"] == "IsInError":
            setting["value"] = "True"
            break
    
    device = ClimateDevice.from_pymelcloud_device(MockATWDevice(), mock_atw_device_state)
    assert device.is_in_error() == True


def test_climate_device_to_mqtt_state_ata(mock_pymelcloud_device, mock_ata_device_state):
    """Test MQTT state conversion for ATA devices."""
    device = ClimateDevice.from_pymelcloud_device(mock_pymelcloud_device, mock_ata_device_state)
    
    state = device.to_mqtt_state()
    
    assert state["power"] == "ON"
    assert state["available"] == True
    assert state["mode"] == "heat"
    assert state["current_temperature"] == 21.5
    assert state["temperature"] == 22.0


def test_climate_device_to_mqtt_state_atw(mock_atw_device_state):
    """Test MQTT state conversion for ATW devices with all zone info."""
    class MockATWDevice:
        id = "test-atw-123"
        given_display_name = "Test ATW"
        device_type = "atwunit"
    
    device = ClimateDevice.from_pymelcloud_device(MockATWDevice(), mock_atw_device_state)
    
    state = device.to_mqtt_state()
    
    assert state["power"] == "ON"
    assert state["available"] == True
    assert state["mode"] == "heat"  # Mapped from "Heating" to HA mode
    assert state["operation_mode"] == "Heating"  # Original MELCloud mode
    assert state["current_temperature"] == 21.0
    assert state["temperature"] == 21.0
    assert state["tank_temperature"] == 51.5
    assert state["tank_target_temperature"] == 53.0
    assert state["operation_mode_zone1"] == "HeatRoomTemperature"
    assert state["forced_hot_water"] == False
    assert state["prohibit_hot_water"] == False
    assert state["in_standby"] == False


def test_climate_device_offline_status(mock_pymelcloud_device):
    """Test device offline status when state is None."""
    device = ClimateDevice.from_pymelcloud_device(mock_pymelcloud_device, None)
    
    assert device.online == False
    assert device.state == {}
