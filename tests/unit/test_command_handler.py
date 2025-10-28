"""Unit tests for CommandHandler."""

import pytest
from unittest.mock import AsyncMock

from app.command_handler import CommandHandler
from app.models import ClimateDevice
from app.melcloud_client import MelCloudClient, ApiError


@pytest.fixture
def mock_melcloud_client():
    """Create mock MELCloud client."""
    client = AsyncMock(spec=MelCloudClient)
    return client


@pytest.fixture
def command_handler(mock_melcloud_client):
    """Create CommandHandler instance with mocked client."""
    return CommandHandler(mock_melcloud_client)


@pytest.fixture
def sample_device():
    """Create sample ClimateDevice for testing."""
    return ClimateDevice(
        device_id="test-device-123",
        device_name="Living Room AC",
        device_type="ataunit",
        online=True,
        state={
            "power": True,
            "setTemperature": 22.0,
            "roomTemperature": 21.5,
            "operationMode": "cool",
        }
    )


class TestTemperatureParsing:
    """Test temperature command parsing."""
    
    def test_parse_plain_number(self, command_handler):
        """Should parse plain number string."""
        result = command_handler.parse_temperature_command("22.5")
        assert result == 22.5
    
    def test_parse_integer(self, command_handler):
        """Should parse integer string."""
        result = command_handler.parse_temperature_command("24")
        assert result == 24.0
    
    def test_parse_json_with_temperature_key(self, command_handler):
        """Should parse JSON with temperature key."""
        result = command_handler.parse_temperature_command('{"temperature": 23.5}')
        assert result == 23.5
    
    def test_parse_json_number(self, command_handler):
        """Should parse JSON number."""
        result = command_handler.parse_temperature_command('20.0')
        assert result == 20.0
    
    def test_invalid_temperature_returns_none(self, command_handler):
        """Should return None for invalid temperature."""
        result = command_handler.parse_temperature_command("invalid")
        assert result is None
    
    def test_empty_temperature_returns_none(self, command_handler):
        """Should return None for empty string."""
        result = command_handler.parse_temperature_command("")
        assert result is None


class TestModeParsing:
    """Test mode command parsing."""
    
    def test_parse_plain_mode(self, command_handler):
        """Should parse plain mode string."""
        result = command_handler.parse_mode_command("cool")
        assert result == "cool"
    
    def test_parse_mode_with_whitespace(self, command_handler):
        """Should trim whitespace."""
        result = command_handler.parse_mode_command("  heat  ")
        assert result == "heat"
    
    def test_parse_uppercase_mode(self, command_handler):
        """Should convert to lowercase."""
        result = command_handler.parse_mode_command("AUTO")
        assert result == "auto"
    
    def test_parse_json_with_mode_key(self, command_handler):
        """Should parse JSON with mode key."""
        result = command_handler.parse_mode_command('{"mode": "dry"}')
        assert result == "dry"
    
    def test_invalid_mode_returns_none(self, command_handler):
        """Should return None for invalid mode."""
        result = command_handler.parse_mode_command("invalid_mode")
        assert result is None
    
    def test_empty_mode_returns_none(self, command_handler):
        """Should return None for empty string."""
        result = command_handler.parse_mode_command("")
        assert result is None


class TestTemperatureCommand:
    """Test temperature command execution."""
    
    @pytest.mark.asyncio
    async def test_valid_temperature_command(
        self,
        command_handler,
        mock_melcloud_client,
        sample_device
    ):
        """Should execute valid temperature command."""
        # Arrange
        mock_melcloud_client.set_device_state = AsyncMock(return_value=True)
        mock_melcloud_client.get_device_state = AsyncMock(
            return_value={"setTemperature": 24.0}
        )
        
        # Act
        result = await command_handler.handle_temperature_command(
            sample_device, 24.0
        )
        
        # Assert
        assert result is True
        mock_melcloud_client.set_device_state.assert_called_once_with(
            "test-device-123",
            {"setTemperature": 24.0}
        )
        mock_melcloud_client.get_device_state.assert_called_once_with(
            "test-device-123"
        )
    
    @pytest.mark.asyncio
    async def test_temperature_below_minimum(
        self,
        command_handler,
        mock_melcloud_client,
        sample_device
    ):
        """Should reject temperature below minimum (16°C)."""
        result = await command_handler.handle_temperature_command(
            sample_device, 15.0
        )
        
        assert result is False
        mock_melcloud_client.set_device_state.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_temperature_above_maximum(
        self,
        command_handler,
        mock_melcloud_client,
        sample_device
    ):
        """Should reject temperature above maximum (31°C)."""
        result = await command_handler.handle_temperature_command(
            sample_device, 32.0
        )
        
        assert result is False
        mock_melcloud_client.set_device_state.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_temperature_at_minimum_boundary(
        self,
        command_handler,
        mock_melcloud_client,
        sample_device
    ):
        """Should accept temperature at minimum boundary (16°C)."""
        mock_melcloud_client.set_device_state = AsyncMock(return_value=True)
        mock_melcloud_client.get_device_state = AsyncMock(
            return_value={"setTemperature": 16.0}
        )
        
        result = await command_handler.handle_temperature_command(
            sample_device, 16.0
        )
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_temperature_at_maximum_boundary(
        self,
        command_handler,
        mock_melcloud_client,
        sample_device
    ):
        """Should accept temperature at maximum boundary (31°C)."""
        mock_melcloud_client.set_device_state = AsyncMock(return_value=True)
        mock_melcloud_client.get_device_state = AsyncMock(
            return_value={"setTemperature": 31.0}
        )
        
        result = await command_handler.handle_temperature_command(
            sample_device, 31.0
        )
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_api_error_during_temperature_command(
        self,
        command_handler,
        mock_melcloud_client,
        sample_device
    ):
        """Should handle API error gracefully."""
        mock_melcloud_client.set_device_state = AsyncMock(
            side_effect=ApiError("Connection timeout")
        )
        
        result = await command_handler.handle_temperature_command(
            sample_device, 22.0
        )
        
        assert result is False


class TestModeCommand:
    """Test mode command execution."""
    
    @pytest.mark.asyncio
    async def test_valid_mode_command_heat(
        self,
        command_handler,
        mock_melcloud_client,
        sample_device
    ):
        """Should execute valid heat mode command."""
        mock_melcloud_client.set_device_state = AsyncMock(return_value=True)
        mock_melcloud_client.get_device_state = AsyncMock(
            return_value={"operationMode": "heat"}
        )
        
        result = await command_handler.handle_mode_command(sample_device, "heat")
        
        assert result is True
        mock_melcloud_client.set_device_state.assert_called_once_with(
            "test-device-123",
            {"power": True, "operationMode": "heat"}
        )
    
    @pytest.mark.asyncio
    async def test_valid_mode_command_off(
        self,
        command_handler,
        mock_melcloud_client,
        sample_device
    ):
        """Should execute valid off mode command."""
        mock_melcloud_client.set_device_state = AsyncMock(return_value=True)
        mock_melcloud_client.get_device_state = AsyncMock(
            return_value={"power": False}
        )
        
        result = await command_handler.handle_mode_command(sample_device, "off")
        
        assert result is True
        mock_melcloud_client.set_device_state.assert_called_once_with(
            "test-device-123",
            {"power": False}
        )
    
    @pytest.mark.asyncio
    async def test_invalid_mode_command(
        self,
        command_handler,
        mock_melcloud_client,
        sample_device
    ):
        """Should reject invalid mode."""
        result = await command_handler.handle_mode_command(
            sample_device, "invalid_mode"
        )
        
        assert result is False
        mock_melcloud_client.set_device_state.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_all_valid_modes(
        self,
        command_handler,
        mock_melcloud_client,
        sample_device
    ):
        """Should accept all valid modes."""
        valid_modes = ["off", "heat", "cool", "auto", "dry", "fan_only"]
        
        for mode in valid_modes:
            mock_melcloud_client.set_device_state = AsyncMock(return_value=True)
            mock_melcloud_client.get_device_state = AsyncMock(
                return_value={"operationMode": mode}
            )
            
            result = await command_handler.handle_mode_command(sample_device, mode)
            assert result is True, f"Mode {mode} should be accepted"
    
    @pytest.mark.asyncio
    async def test_api_error_during_mode_command(
        self,
        command_handler,
        mock_melcloud_client,
        sample_device
    ):
        """Should handle API error gracefully."""
        mock_melcloud_client.set_device_state = AsyncMock(
            side_effect=ApiError("Device unreachable")
        )
        
        result = await command_handler.handle_mode_command(sample_device, "cool")
        
        assert result is False


class TestModeMapping:
    """Test Home Assistant to MELCloud mode mapping."""
    
    def test_mode_mapping_off(self, command_handler):
        """Should map 'off' to power=False."""
        mapping = command_handler._mode_mapping["off"]
        assert mapping == {"power": False}
    
    def test_mode_mapping_heat(self, command_handler):
        """Should map 'heat' to power=True + operationMode=heat."""
        mapping = command_handler._mode_mapping["heat"]
        assert mapping == {"power": True, "operationMode": "heat"}
    
    def test_mode_mapping_cool(self, command_handler):
        """Should map 'cool' to power=True + operationMode=cool."""
        mapping = command_handler._mode_mapping["cool"]
        assert mapping == {"power": True, "operationMode": "cool"}
    
    def test_mode_mapping_auto(self, command_handler):
        """Should map 'auto' to power=True + operationMode=auto."""
        mapping = command_handler._mode_mapping["auto"]
        assert mapping == {"power": True, "operationMode": "auto"}
    
    def test_mode_mapping_dry(self, command_handler):
        """Should map 'dry' to power=True + operationMode=dry."""
        mapping = command_handler._mode_mapping["dry"]
        assert mapping == {"power": True, "operationMode": "dry"}
    
    def test_mode_mapping_fan_only(self, command_handler):
        """Should map 'fan_only' to power=True + operationMode=fan."""
        mapping = command_handler._mode_mapping["fan_only"]
        assert mapping == {"power": True, "operationMode": "fan"}
    
    def test_all_ha_modes_mapped(self, command_handler):
        """Should have mappings for all Home Assistant modes."""
        expected_modes = {"off", "heat", "cool", "auto", "dry", "fan_only"}
        actual_modes = set(command_handler._mode_mapping.keys())
        assert actual_modes == expected_modes
