"""Climate device entity wrapping pymelcloudhome Device with state."""

from typing import Optional, Dict, Any, Literal, List
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
        Extract setting value from ATW settings array.
        
        ATW devices return settings as: [{"name": "Power", "value": "True"}, ...]
        
        Args:
            setting_name: Setting name to extract
            
        Returns:
            Setting value as string, or None if not found
        """
        if self.device_type != "atwunit" or "settings" not in self.state:
            return None
        
        settings: List[Dict[str, str]] = self.state.get("settings", [])
        for setting in settings:
            if setting.get("name") == setting_name:
                return setting.get("value")
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
        value = self._get_atw_setting(setting_name)
        try:
            return float(value) if value else None
        except (ValueError, TypeError):
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
    
    def to_mqtt_state(self) -> dict:
        """
        Convert to MQTT state topic payload for Home Assistant.
        
        Returns:
            Dictionary suitable for MQTT state message
        """
        from loguru import logger
        
        # DEBUG: Log the raw state we're working with
        logger.debug(
            f"Converting state to MQTT for device {self.device_name} ({self.device_type})",
            extra={
                "device_id": self.device_id,
                "device_type": self.device_type,
                "state_keys": list(self.state.keys()) if isinstance(self.state, dict) else [],
                "has_settings": "settings" in self.state if isinstance(self.state, dict) else False,
                "settings_count": len(self.state.get("settings", [])) if isinstance(self.state, dict) else 0
            }
        )
        
        base_state = {
            "power": "ON" if self.get_power() else "OFF",
            "available": self.online,
        }
        
        # DEBUG: Log extracted power state
        logger.debug(
            f"Device {self.device_name} power state: {base_state['power']}, online: {self.online}",
            extra={
                "device_id": self.device_id,
                "power": base_state["power"],
                "online": self.online
            }
        )
        
        if self.device_type == "ataunit":
            # ATA: Standard climate control
            base_state.update({
                "mode": self.state.get("operationMode", "off").lower(),
                "current_temperature": self.get_temperature(),
                "temperature": self.get_target_temperature(),
            })
        
        elif self.device_type == "atwunit":
            # ATW: Hydronic heating with zones + hot water tank
            current_temp = self.get_temperature()
            target_temp = self.get_target_temperature()
            tank_temp = self.get_tank_temperature()
            tank_target = self.get_tank_target_temperature()
            operation_mode = self._get_atw_setting("OperationModeZone1")
            
            # DEBUG: Log key ATW values
            logger.debug(
                f"ATW device {self.device_name} temps: current={current_temp}, "
                f"target={target_temp}, tank={tank_temp}, tank_target={tank_target}, mode={operation_mode}",
                extra={
                    "device_id": self.device_id,
                    "current_temperature": current_temp,
                    "target_temperature": target_temp,
                    "tank_temperature": tank_temp,
                    "tank_target_temperature": tank_target,
                    "operation_mode": operation_mode
                }
            )
            
            base_state.update({
                "mode": self._get_atw_setting("OperationMode"),
                "current_temperature": current_temp,  # Zone 1 room temp
                "temperature": target_temp,  # Zone 1 target
                "tank_temperature": tank_temp,
                "tank_target_temperature": tank_target,
                "operation_mode_zone1": operation_mode,
                "set_temperature_zone1": target_temp,
                "set_heat_flow_temperature_zone1": self._get_atw_float("SetHeatFlowTemperatureZone1"),
                "set_cool_flow_temperature_zone1": self._get_atw_float("SetCoolFlowTemperatureZone1"),
                "forced_hot_water": self._get_atw_bool("ForcedHotWaterMode"),
                "prohibit_hot_water": self._get_atw_bool("ProhibitHotWater"),
                "in_standby": self._get_atw_bool("InStandbyMode"),
            })
            
            # Zone 2 if present
            if self.has_zone_2():
                logger.debug(f"Device {self.device_name} has Zone 2", extra={"device_id": self.device_id})
                base_state.update({
                    "zone2_temperature": self._get_atw_float("RoomTemperatureZone2"),
                    "zone2_target_temperature": self._get_atw_float("SetTemperatureZone2"),
                    "set_temperature_zone2": self._get_atw_float("SetTemperatureZone2"),
                    "operation_mode_zone2": self._get_atw_setting("OperationModeZone2"),
                    "set_heat_flow_temperature_zone2": self._get_atw_float("SetHeatFlowTemperatureZone2"),
                    "set_cool_flow_temperature_zone2": self._get_atw_float("SetCoolFlowTemperatureZone2"),
                })
            
            # Capabilities for control validation
            capabilities = self.state.get("capabilities", {})
            if isinstance(capabilities, dict):
                base_state["Capabilities"] = capabilities
                logger.debug(
                    f"Device {self.device_name} capabilities included in state",
                    extra={
                        "device_id": self.device_id,
                        "has_hot_water": capabilities.get("hasHotWater"),
                        "has_zone2": capabilities.get("hasZone2")
                    }
                )
        
        # Error state (all device types)
        base_state["error"] = self.is_in_error()
        if self.is_in_error():
            error_code = self.get_error_code()
            base_state["error_code"] = error_code if error_code else ""
        else:
            base_state["error_code"] = ""
        
        # DEBUG: Log final MQTT state
        logger.debug(
            f"Final MQTT state for {self.device_name}: power={base_state.get('power')}, "
            f"temp={base_state.get('temperature')}, current={base_state.get('current_temperature')}",
            extra={
                "device_id": self.device_id,
                "mqtt_state": base_state
            }
        )
        
        return base_state
