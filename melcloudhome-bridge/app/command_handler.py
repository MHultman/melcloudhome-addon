"""Command handler for processing MQTT commands and executing them on MELCloud devices."""

import json
from typing import Optional
from loguru import logger

from app.models import ClimateDevice
from app.melcloud_client import MelCloudClient, ApiError


class CommandHandler:
    """
    Handle MQTT commands from Home Assistant and execute them via MELCloud API.
    
    Responsibilities:
    - Parse temperature and mode commands from MQTT
    - Validate command parameters
    - Map Home Assistant modes to MELCloud API modes
    - Execute commands via MelCloudClient
    - Trigger immediate state refresh after command
    """
    
    def __init__(self, melcloud_client: MelCloudClient):
        """
        Initialize command handler.
        
        Args:
            melcloud_client: MELCloud client for command execution
        """
        self.melcloud_client = melcloud_client
        self._logger = logger.bind(component="command_handler")
        
        # Mode mapping: Home Assistant → MELCloud API
        # Based on pymelcloudhome expected values
        self._mode_mapping = {
            "off": {"power": False},
            "heat": {"power": True, "operationMode": "heat"},
            "cool": {"power": True, "operationMode": "cool"},
            "auto": {"power": True, "operationMode": "auto"},
            "dry": {"power": True, "operationMode": "dry"},
            "fan_only": {"power": True, "operationMode": "fan"},
        }
    
    async def handle_temperature_command(
        self,
        device: ClimateDevice,
        temperature: float
    ) -> bool:
        """
        Handle temperature setpoint command.
        
        Args:
            device: Target device
            temperature: Desired temperature (Celsius)
            
        Returns:
            True if command succeeded, False otherwise
        """
        # Validate temperature range
        if not self._validate_temperature(temperature):
            self._logger.warning(
                f"Invalid temperature {temperature}°C for {device.device_name} "
                f"(must be 16-31°C)"
            )
            return False
        
        self._logger.info(
            f"Setting temperature to {temperature}°C on {device.device_name}"
        )
        
        try:
            # Build state change payload
            state_changes = {
                "setTemperature": temperature
            }
            
            # Execute command
            await self.melcloud_client.set_device_state(
                device.device_id,
                state_changes
            )
            
            # Immediate state refresh
            await self._refresh_device_state(device)
            
            self._logger.info(
                f"Successfully set temperature to {temperature}°C on {device.device_name}"
            )
            return True
            
        except ApiError as e:
            self._logger.error(
                f"Failed to set temperature on {device.device_name}: {e}"
            )
            return False
    
    async def handle_mode_command(
        self,
        device: ClimateDevice,
        mode: str
    ) -> bool:
        """
        Handle HVAC mode command.
        
        Args:
            device: Target device
            mode: Desired mode (off, heat, cool, auto, dry, fan_only)
            
        Returns:
            True if command succeeded, False otherwise
        """
        # Validate mode
        if mode not in self._mode_mapping:
            self._logger.warning(
                f"Invalid mode '{mode}' for {device.device_name} "
                f"(valid: {list(self._mode_mapping.keys())})"
            )
            return False
        
        self._logger.info(
            f"Setting mode to '{mode}' on {device.device_name}"
        )
        
        try:
            # Get state changes for this mode
            state_changes = self._mode_mapping[mode].copy()
            
            # Execute command
            await self.melcloud_client.set_device_state(
                device.device_id,
                state_changes
            )
            
            # Immediate state refresh
            await self._refresh_device_state(device)
            
            self._logger.info(
                f"Successfully set mode to '{mode}' on {device.device_name}"
            )
            return True
            
        except ApiError as e:
            self._logger.error(
                f"Failed to set mode on {device.device_name}: {e}"
            )
            return False
    
    def _validate_temperature(self, temperature: float) -> bool:
        """
        Validate temperature is within acceptable range.
        
        Args:
            temperature: Temperature in Celsius
            
        Returns:
            True if valid, False otherwise
        """
        # Standard range for most Mitsubishi devices
        return 16.0 <= temperature <= 31.0
    
    async def _refresh_device_state(self, device: ClimateDevice) -> None:
        """
        Refresh device state immediately after command execution.
        
        Args:
            device: Device to refresh
        """
        try:
            new_state = await self.melcloud_client.get_device_state(
                device.device_id
            )
            if new_state:
                device.state = new_state
                device.online = True
                self._logger.debug(
                    f"Refreshed state for {device.device_name}"
                )
        except Exception as e:
            self._logger.warning(
                f"Failed to refresh state for {device.device_name}: {e}"
            )
    
    def parse_temperature_command(self, payload: str) -> Optional[float]:
        """
        Parse temperature command payload.
        
        Home Assistant sends temperature as plain string or JSON.
        
        Args:
            payload: MQTT payload string
            
        Returns:
            Temperature as float, or None if invalid
        """
        try:
            # Try parsing as plain number first
            return float(payload)
        except ValueError:
            # Try parsing as JSON
            try:
                data = json.loads(payload)
                if isinstance(data, dict) and "temperature" in data:
                    return float(data["temperature"])
                elif isinstance(data, (int, float)):
                    return float(data)
            except (json.JSONDecodeError, ValueError, TypeError):
                pass
        
        self._logger.warning(f"Failed to parse temperature command: {payload}")
        return None
    
    def parse_mode_command(self, payload: str) -> Optional[str]:
        """
        Parse mode command payload.
        
        Home Assistant sends mode as plain string or JSON.
        
        Args:
            payload: MQTT payload string
            
        Returns:
            Mode string, or None if invalid
        """
        try:
            # Try plain string first
            mode = payload.strip().lower()
            if mode in self._mode_mapping:
                return mode
            
            # Try parsing as JSON
            data = json.loads(payload)
            if isinstance(data, dict) and "mode" in data:
                mode = data["mode"].strip().lower()
                if mode in self._mode_mapping:
                    return mode
        except (json.JSONDecodeError, AttributeError):
            pass
        
        self._logger.warning(f"Failed to parse mode command: {payload}")
        return None
