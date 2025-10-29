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
    
    # ATW-specific control handlers
    
    async def handle_power_command(
        self,
        device: ClimateDevice,
        power_state: str
    ) -> bool:
        """
        Handle power switch command for ATW devices.
        
        Args:
            device: Target ATW device
            power_state: "ON" or "OFF"
            
        Returns:
            True if command succeeded, False otherwise
        """
        if device.device_type != "atwunit":
            self._logger.warning(f"Power control not supported for {device.device_type}")
            return False
        
        power_bool = power_state.upper() == "ON"
        self._logger.info(f"Setting power to {power_bool} on {device.device_name}")
        
        try:
            await self.melcloud_client.set_device_state(
                device.device_id,
                {"power": power_bool}
            )
            await self._refresh_device_state(device)
            self._logger.info(f"Successfully set power to {power_bool} on {device.device_name}")
            return True
        except ApiError as e:
            self._logger.error(f"Failed to set power on {device.device_name}: {e}")
            return False
    
    async def handle_zone_temperature_command(
        self,
        device: ClimateDevice,
        zone: int,
        temperature: float
    ) -> bool:
        """
        Handle zone temperature setpoint command.
        
        Args:
            device: Target ATW device
            zone: Zone number (1 or 2)
            temperature: Desired temperature (Celsius)
            
        Returns:
            True if command succeeded, False otherwise
        """
        if device.device_type != "atwunit":
            self._logger.warning(f"Zone temperature control not supported for {device.device_type}")
            return False
        
        # Validate zone
        if zone == 2 and not device.has_zone_2():
            self._logger.warning(f"Device {device.device_name} does not have Zone 2")
            return False
        
        # Validate temperature range
        if not self._validate_temperature(temperature):
            self._logger.warning(
                f"Invalid temperature {temperature}°C for {device.device_name} "
                f"(must be 16-31°C)"
            )
            return False
        
        param_name = f"setTemperatureZone{zone}"
        self._logger.info(f"Setting Zone {zone} temperature to {temperature}°C on {device.device_name}")
        
        try:
            await self.melcloud_client.set_device_state(
                device.device_id,
                {param_name: temperature}
            )
            await self._refresh_device_state(device)
            self._logger.info(f"Successfully set Zone {zone} temperature on {device.device_name}")
            return True
        except ApiError as e:
            self._logger.error(f"Failed to set Zone {zone} temperature on {device.device_name}: {e}")
            return False
    
    async def handle_zone_operation_mode_command(
        self,
        device: ClimateDevice,
        zone: int,
        mode: str
    ) -> bool:
        """
        Handle zone operation mode command.
        
        Args:
            device: Target ATW device
            zone: Zone number (1 or 2)
            mode: Operation mode (HeatRoomTemperature, HeatFlowTemperature, HeatCurve)
            
        Returns:
            True if command succeeded, False otherwise
        """
        if device.device_type != "atwunit":
            self._logger.warning(f"Zone operation mode not supported for {device.device_type}")
            return False
        
        valid_modes = ["HeatRoomTemperature", "HeatFlowTemperature", "HeatCurve"]
        if mode not in valid_modes:
            self._logger.warning(f"Invalid operation mode '{mode}' (valid: {valid_modes})")
            return False
        
        # Validate zone
        if zone == 2 and not device.has_zone_2():
            self._logger.warning(f"Device {device.device_name} does not have Zone 2")
            return False
        
        param_name = f"operationModeZone{zone}"
        self._logger.info(f"Setting Zone {zone} operation mode to {mode} on {device.device_name}")
        
        try:
            await self.melcloud_client.set_device_state(
                device.device_id,
                {param_name: mode}
            )
            await self._refresh_device_state(device)
            self._logger.info(f"Successfully set Zone {zone} operation mode on {device.device_name}")
            return True
        except ApiError as e:
            self._logger.error(f"Failed to set Zone {zone} operation mode on {device.device_name}: {e}")
            return False
    
    async def handle_zone_flow_temperature_command(
        self,
        device: ClimateDevice,
        zone: int,
        flow_type: str,
        temperature: int
    ) -> bool:
        """
        Handle zone flow temperature command (heat or cool).
        
        Args:
            device: Target ATW device
            zone: Zone number (1 or 2)
            flow_type: "heat" or "cool"
            temperature: Desired flow temperature (Celsius)
            
        Returns:
            True if command succeeded, False otherwise
        """
        if device.device_type != "atwunit":
            self._logger.warning(f"Flow temperature control not supported for {device.device_type}")
            return False
        
        # Validate zone
        if zone == 2 and not device.has_zone_2():
            self._logger.warning(f"Device {device.device_name} does not have Zone 2")
            return False
        
        # Validate flow type
        if flow_type not in ["heat", "cool"]:
            self._logger.warning(f"Invalid flow type '{flow_type}' (must be 'heat' or 'cool')")
            return False
        
        # Validate temperature range
        if flow_type == "heat" and not (20 <= temperature <= 60):
            self._logger.warning(f"Invalid heat flow temperature {temperature}°C (must be 20-60°C)")
            return False
        elif flow_type == "cool" and not (5 <= temperature <= 25):
            self._logger.warning(f"Invalid cool flow temperature {temperature}°C (must be 5-25°C)")
            return False
        
        param_name = f"set{flow_type.capitalize()}FlowTemperatureZone{zone}"
        self._logger.info(f"Setting Zone {zone} {flow_type} flow temperature to {temperature}°C on {device.device_name}")
        
        try:
            await self.melcloud_client.set_device_state(
                device.device_id,
                {param_name: temperature}
            )
            await self._refresh_device_state(device)
            self._logger.info(f"Successfully set Zone {zone} {flow_type} flow temperature on {device.device_name}")
            return True
        except ApiError as e:
            self._logger.error(f"Failed to set Zone {zone} {flow_type} flow temperature on {device.device_name}: {e}")
            return False
    
    async def handle_tank_temperature_command(
        self,
        device: ClimateDevice,
        temperature: int
    ) -> bool:
        """
        Handle hot water tank temperature setpoint command.
        
        Args:
            device: Target ATW device
            temperature: Desired tank temperature (Celsius, typically 40-60)
            
        Returns:
            True if command succeeded, False otherwise
        """
        if device.device_type != "atwunit":
            self._logger.warning(f"Tank temperature control not supported for {device.device_type}")
            return False
        
        # Validate range (typically 40-60°C)
        if not (40 <= temperature <= 60):
            self._logger.warning(f"Invalid tank temperature {temperature}°C (must be 40-60°C)")
            return False
        
        self._logger.info(f"Setting tank temperature to {temperature}°C on {device.device_name}")
        
        try:
            await self.melcloud_client.set_device_state(
                device.device_id,
                {"setTankWaterTemperature": temperature}
            )
            await self._refresh_device_state(device)
            self._logger.info(f"Successfully set tank temperature on {device.device_name}")
            return True
        except ApiError as e:
            self._logger.error(f"Failed to set tank temperature on {device.device_name}: {e}")
            return False
    
    async def handle_forced_hot_water_command(
        self,
        device: ClimateDevice,
        state: str
    ) -> bool:
        """
        Handle forced hot water mode command.
        
        Args:
            device: Target ATW device
            state: "ON" or "OFF"
            
        Returns:
            True if command succeeded, False otherwise
        """
        if device.device_type != "atwunit":
            self._logger.warning(f"Forced hot water mode not supported for {device.device_type}")
            return False
        
        forced_mode = state.upper() == "ON"
        self._logger.info(f"Setting forced hot water mode to {forced_mode} on {device.device_name}")
        
        try:
            await self.melcloud_client.set_device_state(
                device.device_id,
                {"forcedHotWaterMode": forced_mode}
            )
            await self._refresh_device_state(device)
            self._logger.info(f"Successfully set forced hot water mode on {device.device_name}")
            return True
        except ApiError as e:
            self._logger.error(f"Failed to set forced hot water mode on {device.device_name}: {e}")
            return False

