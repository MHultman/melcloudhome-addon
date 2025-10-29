"""Climate device entity wrapping pymelcloudhome Device with state."""

from typing import Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict


class ClimateDevice(BaseModel):
    """
    Wrapper for pymelcloudhome Device with state.
    
    Supports both ATA (Air-to-Air) and ATW (Air-to-Water) device types.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    device_id: str = Field(..., description="Device unique identifier (UUID)")
    device_name: str = Field(..., description="User-assigned device name")
    device_type: Literal["ataunit", "atwunit"] = Field(..., description="Device type")
    state: Dict[str, Any] = Field(default_factory=dict, description="Raw state from MELCloud API")
    online: bool = Field(default=False, description="Device reachability status")
    
    @classmethod
    def from_pymelcloud_device(cls, device: Any, state: Optional[Dict] = None) -> "ClimateDevice":
        """
        Create ClimateDevice from pymelcloudhome Device object.
        
        Args:
            device: pymelcloudhome Device object with .id, .given_display_name, .device_type
            state: Optional device state dict from get_device_state()
            
        Returns:
            ClimateDevice instance
        """
        return cls(
            device_id=device.id,
            device_name=device.given_display_name,
            device_type=device.device_type,
            state=state or {},
            online=state is not None
        )
    
    def _get_atw_setting(self, setting_name: str) -> Optional[str]:
        """
        Extract setting value from ATW state dictionary.
        
        ATW devices can return state in two formats:
        1. Flat dict: {"Power": "True", "OperationModeZone1": "Heat", ...}
        2. Settings array: {"settings": [{"name": "Power", "value": "True"}, ...]}
        
        Args:
            setting_name: Setting name to extract
            
        Returns:
            Setting value as string, or None if not found
        """
        from loguru import logger
        
        if self.device_type != "atwunit":
            logger.debug(f"Not an ATW device (type={self.device_type}), cannot get setting {setting_name}")
            return None
        
        if not isinstance(self.state, dict):
            return None
        
        # Try flat dictionary format first (production API format)
        if setting_name in self.state:
            value = self.state.get(setting_name)
            logger.debug(
                f"Found setting '{setting_name}' = '{value}'",
                extra={"device_id": self.device_id, "setting_name": setting_name, "value": value}
            )
            return str(value) if value is not None else None
        
        # Try settings array format (test fixture format)
        if "settings" in self.state and isinstance(self.state["settings"], list):
            for setting in self.state["settings"]:
                if isinstance(setting, dict) and setting.get("name") == setting_name:
                    value = setting.get("value")
                    logger.debug(
                        f"Found setting '{setting_name}' = '{value}' in settings array",
                        extra={"device_id": self.device_id, "setting_name": setting_name, "value": value}
                    )
                    return str(value) if value is not None else None
        
        logger.debug(
            f"Setting '{setting_name}' not found in state",
            extra={
                "device_id": self.device_id,
                "setting_name": setting_name,
                "available_keys": list(self.state.keys()) if isinstance(self.state, dict) else []
            }
        )
        return None
    
    def _get_atw_bool(self, setting_name: str) -> bool:
        """
        Get boolean from ATW settings array (handles "True"/"False" strings).
        
        Args:
            setting_name: Setting name
            
        Returns:
            Boolean value, False if not found
        """
        value = self._get_atw_setting(setting_name)
        return value == "True" if value else False
    
    def _get_atw_float(self, setting_name: str) -> Optional[float]:
        """
        Get float from ATW settings array.
        
        Args:
            setting_name: Setting name
            
        Returns:
            Float value, or None if not found or invalid
        """
        from loguru import logger
        
        value = self._get_atw_setting(setting_name)
        try:
            result = float(value) if value else None
            logger.debug(
                f"Converting '{setting_name}' to float: '{value}' -> {result}",
                extra={"device_id": self.device_id, "setting_name": setting_name, "string_value": value, "float_value": result}
            )
            return result
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to convert '{setting_name}' value '{value}' to float: {e}")
            return None
    
    def get_power(self) -> bool:
        """Get power state (works for both ATA and ATW)."""
        if self.device_type == "ataunit":
            return self.state.get("power", False)
        elif self.device_type == "atwunit":
            return self._get_atw_bool("Power")
        return False
    
    def get_temperature(self) -> Optional[float]:
        """Get current/room temperature (device-type specific)."""
        if self.device_type == "ataunit":
            return self.state.get("roomTemperature")
        elif self.device_type == "atwunit":
            return self._get_atw_float("RoomTemperatureZone1")
        return None
    
    def get_target_temperature(self) -> Optional[float]:
        """Get target temperature (device-type specific)."""
        if self.device_type == "ataunit":
            return self.state.get("setTemperature")
        elif self.device_type == "atwunit":
            return self._get_atw_float("SetTemperatureZone1")
        return None
    
    def get_tank_temperature(self) -> Optional[float]:
        """Get hot water tank temperature (ATW only)."""
        if self.device_type == "atwunit":
            return self._get_atw_float("TankWaterTemperature")
        return None
    
    def get_tank_target_temperature(self) -> Optional[float]:
        """Get hot water tank target temperature (ATW only)."""
        if self.device_type == "atwunit":
            return self._get_atw_float("SetTankWaterTemperature")
        return None
    
    def is_in_error(self) -> bool:
        """Check if device is in error state."""
        if self.device_type == "ataunit":
            return self.state.get("isInError", False)
        elif self.device_type == "atwunit":
            # Check both top-level and settings array
            return (
                self.state.get("isInError", False) or 
                self._get_atw_bool("IsInError")
            )
        return False
    
    def get_error_code(self) -> Optional[str]:
        """Get error code if device is in error."""
        if self.device_type == "atwunit":
            return self._get_atw_setting("ErrorCode")
        return None
    
    def has_zone_2(self) -> bool:
        """Check if ATW device has a second zone."""
        if self.device_type == "atwunit":
            return self._get_atw_setting("HasZone2") == "1"
        return False
    
    def has_cooling_mode(self) -> bool:
        """Check if ATW device supports cooling mode."""
        if self.device_type == "atwunit":
            return self._get_atw_bool("HasCoolingMode")
        return False
    
    def get_in_standby_mode(self) -> bool:
        """Check if ATW device is in standby mode."""
        if self.device_type == "atwunit":
            return self._get_atw_bool("InStandbyMode")
        return False
    
    def get_operation_mode(self) -> Optional[str]:
        """Get overall operation mode (ATW only)."""
        if self.device_type == "atwunit":
            return self._get_atw_setting("OperationMode")
        return None
    
    def get_operation_mode_zone1(self) -> Optional[str]:
        """Get Zone 1 operation mode (ATW only)."""
        if self.device_type == "atwunit":
            return self._get_atw_setting("OperationModeZone1")
        return None
    
    def get_operation_mode_zone2(self) -> Optional[str]:
        """Get Zone 2 operation mode (ATW only)."""
        if self.device_type == "atwunit" and self.has_zone_2():
            return self._get_atw_setting("OperationModeZone2")
        return None
    
    def get_room_temperature_zone1(self) -> Optional[float]:
        """Get Zone 1 room temperature (ATW only)."""
        if self.device_type == "atwunit":
            return self._get_atw_float("RoomTemperatureZone1")
        return None
    
    def get_room_temperature_zone2(self) -> Optional[float]:
        """Get Zone 2 room temperature (ATW only)."""
        if self.device_type == "atwunit" and self.has_zone_2():
            return self._get_atw_float("RoomTemperatureZone2")
        return None
    
    def get_set_temperature_zone1(self) -> Optional[float]:
        """Get Zone 1 set temperature (ATW only)."""
        if self.device_type == "atwunit":
            return self._get_atw_float("SetTemperatureZone1")
        return None
    
    def get_set_temperature_zone2(self) -> Optional[float]:
        """Get Zone 2 set temperature (ATW only)."""
        if self.device_type == "atwunit" and self.has_zone_2():
            return self._get_atw_float("SetTemperatureZone2")
        return None
    
    def get_prohibit_hot_water(self) -> bool:
        """Check if hot water is prohibited (ATW only)."""
        if self.device_type == "atwunit":
            return self._get_atw_bool("ProhibitHotWater")
        return False
    
    def get_forced_hot_water_mode(self) -> bool:
        """Check if forced hot water mode is active (ATW only)."""
        if self.device_type == "atwunit":
            return self._get_atw_bool("ForcedHotWaterMode")
        return False
    
    def _map_melcloud_mode_to_ha(self, melcloud_mode: str) -> str:
        """
        Map MELCloud operation mode to Home Assistant HVAC mode.
        
        MELCloud modes: Heating, Cooling, Auto, etc.
        Home Assistant modes: heat, cool, auto, off, etc.
        
        Args:
            melcloud_mode: Mode string from MELCloud API
            
        Returns:
            Home Assistant compatible mode string
        """
        mode_lower = melcloud_mode.lower() if melcloud_mode else "unknown"
        
        # Map MELCloud modes to HA modes
        mode_map = {
            "heating": "heat",
            "cooling": "cool",
            "auto": "auto",
            "off": "off",
            "stop": "off",
            "unknown": "heat",  # Default to heat if unknown
        }
        
        return mode_map.get(mode_lower, "heat")
    
    def to_mqtt_state(self) -> dict:
        """
        Convert to MQTT state topic payload for Home Assistant.
        
        Returns:
            Dictionary suitable for MQTT state message
        """
        # DEBUG: Log state conversion start
        from loguru import logger
        
        try:
            state_keys = list(self.state.keys()) if isinstance(self.state, dict) else []
            has_settings = "settings" in self.state if isinstance(self.state, dict) else False
            settings_count = len(self.state.get("settings", [])) if isinstance(self.state, dict) else 0
            
            logger.debug(
                f"Converting state to MQTT for device {self.device_name}: "
                f"type={self.device_type}, keys={str(state_keys)}, "
                f"has_settings={has_settings}, settings_count={settings_count}",
                extra={
                    "device_id": self.device_id,
                    "device_type": self.device_type,
                    "state_keys": state_keys,
                    "has_settings": has_settings,
                    "settings_count": settings_count
                }
            )
        except Exception as e:
            logger.warning(f"Error logging state conversion start: {e}")
        
        base_state = {
            "power": "ON" if self.get_power() else "OFF",
            "available": self.online,
            "mode": "unknown",  # Default mode, will be overridden per device type
        }
        
        if self.device_type == "ataunit":
            # ATA: Standard climate control
            base_state.update({
                "mode": self.state.get("operationMode", "off").lower(),
                "current_temperature": self.get_temperature(),
                "temperature": self.get_target_temperature(),
            })
        
        elif self.device_type == "atwunit":
            # ATW: Hydronic heating with zones + hot water tank
            # Map MELCloud OperationMode to Home Assistant mode
            operation_mode = self.get_operation_mode() or "unknown"
            ha_mode = self._map_melcloud_mode_to_ha(operation_mode)
            
            atw_values = {
                "mode": ha_mode,
                "current_temperature": self.get_room_temperature_zone1(),  # Zone 1 room temp
                "temperature": self.get_set_temperature_zone1(),  # Zone 1 target
                "tank_temperature": self.get_tank_temperature(),
                "tank_target_temperature": self.get_tank_target_temperature(),
                "operation_mode": operation_mode,
                "operation_mode_zone1": self.get_operation_mode_zone1(),
                "forced_hot_water": self.get_forced_hot_water_mode(),
                "prohibit_hot_water": self.get_prohibit_hot_water(),
                "in_standby": self.get_in_standby_mode(),
                "has_zone2": self.has_zone_2(),
                "has_cooling_mode": self.has_cooling_mode(),
            }
            
            # DEBUG: Log each ATW value being set
            atw_values_str = ", ".join(f"{k}={v}" for k, v in atw_values.items())
            logger.debug(
                f"ATW values for {self.device_name}: {atw_values_str}",
                extra={"device_id": self.device_id, "atw_values": atw_values}
            )
            
            base_state.update(atw_values)
            
            # Zone 2 if present
            if self.has_zone_2():
                base_state.update({
                    "zone2_temperature": self.get_room_temperature_zone2(),
                    "zone2_target_temperature": self.get_set_temperature_zone2(),
                    "operation_mode_zone2": self.get_operation_mode_zone2(),
                })
        
        # Error state (all device types)
        base_state["error"] = self.is_in_error()
        if self.is_in_error():
            error_code = self.get_error_code()
            base_state["error_code"] = error_code if error_code else ""
        else:
            base_state["error_code"] = ""
        
        # DEBUG: Log final MQTT state being returned
        logger.debug(
            f"Final MQTT state for {self.device_name}: power={base_state.get('power')}, "
            f"temp={base_state.get('current_temperature')}, "
            f"target={base_state.get('temperature')}, "
            f"mode={base_state.get('mode')}",
            extra={"device_id": self.device_id, "mqtt_state": base_state}
        )
        
        return base_state
