# Data Model

**Feature**: MELCloud Home Bridge  
**Date**: 2025-10-28  
**Purpose**: Define entities, state management, and data flows

**Note**: This data model is based on the [pymelcloudhome library](https://github.com/MHultman/pymelcloudhome) API structure.

## Entity Definitions

### 1. ClimateDevice

Represents a Mitsubishi MELCloud HVAC unit discovered from the pymelcloudhome API.

**Source**: `pymelcloudhome.Device` object from `list_devices()` method

**Core Attributes** (from pymelcloudhome Device):

- `id` (str): Unique device identifier (UUID format, e.g., "d3c4b5a6-f7e8-9012-cbad-876543210fed")
- `given_display_name` (str): User-assigned device name from MELCloud
- `device_type` (str): Device type - either "ataunit" (Air-to-Air) or "atwunit" (Air-to-Water)

**Extended Attributes** (from device state):

- `power` (bool): Device power state (on/off)
- `online` (bool): Device reachability from MELCloud
- Device-specific attributes depend on type (ATA vs ATW - see below)

**Device Type: ATA (Air-to-Air) - Climate Control**

Supports: Air conditioners, heat pumps

State attributes (from `get_device_state(device_id)`):

- `power` (bool): Power state
- `operationMode` (str): Operating mode - implementation specific to MELCloud API
- `setTemperature` (float): Target temperature setpoint
- `roomTemperature` (float): Current room temperature

**Device Type: ATW (Air-to-Water) - Hydronic Heating**

Supports: Water heating systems, underfloor heating

**Actual JSON Response Structure** (from `get_device_state(device_id)`):

```json
{
  "id": "26f6ae21-8862-4ab2-a40a-3ea138c119fc",
  "givenDisplayName": "Device Name",
  "displayIcon": "Loft",
  "settings": [
    { "name": "Power", "value": "True" },
    { "name": "InStandbyMode", "value": "False" },
    { "name": "OperationMode", "value": "Heating" },
    { "name": "HasZone2", "value": "0" },
    { "name": "OperationModeZone1", "value": "HeatRoomTemperature" },
    { "name": "RoomTemperatureZone1", "value": "21" },
    { "name": "SetTemperatureZone1", "value": "21" },
    { "name": "ProhibitHotWater", "value": "False" },
    { "name": "TankWaterTemperature", "value": "51.5" },
    { "name": "SetTankWaterTemperature", "value": "53" },
    { "name": "HasCoolingMode", "value": "False" },
    { "name": "ForcedHotWaterMode", "value": "False" },
    { "name": "IsInError", "value": "False" },
    { "name": "ErrorCode", "value": "" }
  ],
  "macAddress": "282e89465b95",
  "timeZone": "Europe/Berlin",
  "rssi": -74,
  "ftcModel": 5,
  "schedule": null,
  "scheduleEnabled": false,
  "frostProtection": null,
  "overheatProtection": null,
  "holidayMode": null,
  "isConnected": true,
  "isInError": false,
  "capabilities": null
}
```

**Settings Array Format**:
ATW devices return a `settings` array with name-value pairs (strings). The add-on must parse this format:

**Key Settings** (extracted from settings array):

- `Power` (str: "True"/"False"): Device power state
- `InStandbyMode` (str: "True"/"False"): Standby mode indicator
- `OperationMode` (str): "Heating", "Cooling", "HotWater" etc.
- `HasZone2` (str: "0"/"1"): Whether device has a second zone
- `OperationModeZone1` (str): Zone 1 mode - "HeatRoomTemperature", "HeatFlowTemperature", "HeatCurve"
- `RoomTemperatureZone1` (str: numeric): Current room temperature zone 1 (°C)
- `SetTemperatureZone1` (str: numeric): Target room temperature zone 1 (°C)
- `ProhibitHotWater` (str: "True"/"False"): Hot water prohibition state
- `TankWaterTemperature` (str: numeric): Current hot water tank temperature (°C)
- `SetTankWaterTemperature` (str: numeric): Target hot water tank temperature (°C)
- `HasCoolingMode` (str: "True"/"False"): Whether device supports cooling
- `ForcedHotWaterMode` (str: "True"/"False"): Force hot water mode
- `IsInError` (str: "True"/"False"): Error state indicator
- `ErrorCode` (str): Error code if IsInError is True

**Additional Top-Level Fields**:

- `isConnected` (bool): Device online/offline status
- `isInError` (bool): Error state (redundant with settings)
- `macAddress` (str): Device MAC address
- `rssi` (int): WiFi signal strength
- `ftcModel` (int): Device model identifier
- `scheduleEnabled` (bool): Whether scheduling is active

**Zone 2 Settings** (if HasZone2 = "1"):

- `OperationModeZone2` (str)
- `RoomTemperatureZone2` (str: numeric)
- `SetTemperatureZone2` (str: numeric)

**Validation Rules**:

- `device_id` must be unique across all devices
- `device_type` must be either "ataunit" or "atwunit"
- Temperature values depend on device capabilities (obtained from MELCloud)

**Python Representation**:

```python
from dataclasses import dataclass
from typing import Optional, Literal, Dict, Any

@dataclass
class ClimateDevice:
    """Wrapper for pymelcloudhome Device with state."""

    # From pymelcloudhome Device object
    device_id: str  # device.id
    device_name: str  # device.given_display_name
    device_type: Literal["ataunit", "atwunit"]  # device.device_type

    # From get_device_state()
    state: Dict[str, Any]  # Raw state dict from MELCloud
    online: bool  # Derived from API availability

    @classmethod
    def from_pymelcloud_device(cls, device, state: Optional[Dict] = None) -> "ClimateDevice":
        """Create from pymelcloudhome Device object."""
        return cls(
            device_id=device.id,
            device_name=device.given_display_name,
            device_type=device.device_type,
            state=state or {},
            online=state is not None
        )

    def _get_atw_setting(self, setting_name: str) -> Optional[str]:
        """Extract setting value from ATW settings array."""
        if self.device_type != "atwunit" or "settings" not in self.state:
            return None

        for setting in self.state.get("settings", []):
            if setting.get("name") == setting_name:
                return setting.get("value")
        return None

    def _get_atw_bool(self, setting_name: str) -> bool:
        """Get boolean from ATW settings array (handles "True"/"False" strings)."""
        value = self._get_atw_setting(setting_name)
        return value == "True" if value else False

    def _get_atw_float(self, setting_name: str) -> Optional[float]:
        """Get float from ATW settings array."""
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
        """Convert to MQTT state topic payload for Home Assistant."""
        base_state = {
            "power": "ON" if self.get_power() else "OFF",
            "available": self.online,
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
            base_state.update({
                "mode": self._get_atw_setting("OperationMode"),
                "current_temperature": self.get_temperature(),  # Zone 1 room temp
                "temperature": self.get_target_temperature(),  # Zone 1 target
                "tank_temperature": self.get_tank_temperature(),
                "tank_target_temperature": self.get_tank_target_temperature(),
                "operation_mode_zone1": self._get_atw_setting("OperationModeZone1"),
                "forced_hot_water": self._get_atw_bool("ForcedHotWaterMode"),
                "prohibit_hot_water": self._get_atw_bool("ProhibitHotWater"),
                "in_standby": self._get_atw_bool("InStandbyMode"),
            })

            # Zone 2 if present
            if self.has_zone_2():
                base_state.update({
                    "zone2_temperature": self._get_atw_float("RoomTemperatureZone2"),
                    "zone2_target_temperature": self._get_atw_float("SetTemperatureZone2"),
                    "operation_mode_zone2": self._get_atw_setting("OperationModeZone2"),
                })

        # Error state (all device types)
        if self.is_in_error():
            base_state["error"] = True
            error_code = self.get_error_code()
            if error_code:
                base_state["error_code"] = error_code

        return base_state
```

**Notes on ATW Settings Array Parsing**:

- ATW devices return a `settings` array with `{"name": "...", "value": "..."}` objects
- All values are strings (including booleans and numbers)
- Helper methods (`_get_atw_setting`, `_get_atw_bool`, `_get_atw_float`) handle type conversion
- Some settings are redundant: `IsInError` in settings array + `isInError` at top level

**Notes on pymelcloudhome Integration**:

- pymelcloudhome uses **internal caching** (default 5 minutes) to minimize API calls
- `list_devices()` returns cached device list unless cache expired
- `get_device_state()` returns cached state data (no new API call)
- To update state, call `list_devices()` again (refreshes cache if expired)
- Session management and renewal is **automatic** (handles 401 errors internally)

---

### 2. SessionToken

**IMPORTANT**: pymelcloudhome handles session management internally. The add-on does NOT need to manage session tokens directly.

**pymelcloudhome Session Handling**:

- Sessions are managed by the `MelCloudHomeClient` instance
- Automatic re-authentication on 401 errors
- Credentials stored in memory (passed to `login()` method)
- Session persistence is handled by keeping the client instance alive

**Add-on Credential Storage**:

Since pymelcloudhome manages sessions, the add-on only needs to persist **credentials** for re-initialization:

**Attributes**:

- `email` (str): MELCloud account email
- `password` (str): MELCloud account password (encrypted/secured)

**Python Representation**:

```python
from dataclasses import dataclass
import json
from pathlib import Path

@dataclass
class Credentials:
    """User credentials for pymelcloudhome login (not session tokens)."""
    email: str
    password: str

    def to_json(self) -> dict:
        """Serialize for /data/credentials.json (should be encrypted in production)."""
        return {
            "email": self.email,
            "password": self.password
        }

    @classmethod
    def from_json(cls, data: dict) -> "Credentials":
        """Deserialize from /data/credentials.json."""
        return cls(
            email=data["email"],
            password=data["password"]
        )

    def save(self, path: Path = Path("/data/credentials.json")):
        """Save credentials to disk."""
        # TODO: Add encryption for password in production
        path.write_text(json.dumps(self.to_json()))

    @classmethod
    def load(cls, path: Path = Path("/data/credentials.json")) -> Optional["Credentials"]:
        """Load credentials from disk."""
        if not path.exists():
            return None
        return cls.from_json(json.loads(path.read_text()))
```

**Session Management Strategy**:

1. Store only email/password (from HA config) in memory
2. Create `MelCloudHomeClient` instance on startup
3. Call `await client.login(email, password)`
4. Keep client instance alive throughout add-on lifetime
5. pymelcloudhome handles session renewal automatically on API errors
6. On add-on restart, recreate client and re-login

```

---

### 3. MQTTDiscoveryMessage

Configuration payload for Home Assistant MQTT Discovery.

**Attributes**:

- `name` (str): Entity display name
- `unique_id` (str): Unique identifier for entity (e.g., "melcloud_12345")
- `device` (DeviceInfo): Device metadata for HA device registry
- `modes` (list[str]): Available HVAC modes
- `current_temperature_topic` (str): Topic for current temp
- `temperature_command_topic` (str): Topic for setpoint commands
- `mode_state_topic` (str): Topic for mode state
- `mode_command_topic` (str): Topic for mode commands
- `availability_topic` (str): Topic for online/offline status
- `temperature_unit` (str): "C" or "F"
- `min_temp` (float): Minimum temperature
- `max_temp` (float): Maximum temperature
- `temp_step` (float): Temperature increment

**DeviceInfo Sub-Entity**:

- `identifiers` (list[str]): Device unique IDs
- `name` (str): Device name
- `manufacturer` (str): Always "Mitsubishi Electric"
- `model` (str): Device model
- `sw_version` (str): Firmware version

**Topic Patterns**:

```

Discovery: <base_topic>/climate/<device_id>/config
State: <base_topic>/climate/<device_id>/state
Temperature Command: <base_topic>/climate/<device_id>/set_temperature
Mode Command: <base_topic>/climate/<device_id>/set_mode
Availability: <base_topic>/climate/<device_id>/availability

````

**Python Representation**:

```python
from dataclasses import dataclass

@dataclass
class DeviceInfo:
    identifiers: list[str]
    name: str
    manufacturer: str
    model: str
    sw_version: str

@dataclass
class MQTTDiscoveryMessage:
    name: str
    unique_id: str
    device: DeviceInfo
    modes: list[str]
    current_temperature_topic: str
    temperature_command_topic: str
    mode_state_topic: str
    mode_command_topic: str
    availability_topic: str
    temperature_unit: str
    min_temp: float
    max_temp: float
    temp_step: float

    def to_json(self) -> dict:
        """Convert to MQTT payload."""
        return {
            "name": self.name,
            "unique_id": self.unique_id,
            "device": {
                "identifiers": self.device.identifiers,
                "name": self.device.name,
                "manufacturer": self.device.manufacturer,
                "model": self.device.model,
                "sw_version": self.device.sw_version
            },
            "modes": self.modes,
            "current_temperature_topic": self.current_temperature_topic,
            "temperature_command_topic": self.temperature_command_topic,
            "mode_state_topic": self.mode_state_topic,
            "mode_command_topic": self.mode_command_topic,
            "availability_topic": self.availability_topic,
            "temperature_unit": self.temperature_unit,
            "min_temp": self.min_temp,
            "max_temp": self.max_temp,
            "temp_step": self.temp_step
        }
````

---

### 4. Configuration

User-provided settings from Home Assistant config UI.

**Attributes**:

- `melcloud_email` (str, required): MELCloud account email
- `melcloud_password` (str, required): MELCloud account password
- `mqtt_host` (str, required): MQTT broker hostname/IP
- `mqtt_port` (int, required): MQTT broker port
- `mqtt_username` (str, optional): MQTT authentication username
- `mqtt_password` (str, optional): MQTT authentication password
- `mqtt_base_topic` (str, default="homeassistant"): MQTT Discovery base topic
- `poll_interval` (int, default=60): Polling interval in seconds
- `log_level` (str, default="INFO"): Logging level

**Validation Rules**:

- `melcloud_email` must be valid email format
- `melcloud_password` must be non-empty
- `mqtt_host` must be non-empty
- `mqtt_port` must be in range [1, 65535]
- `poll_interval` must be in range [10, 3600] (10 seconds to 1 hour)
- `log_level` must be one of: DEBUG, INFO, WARNING, ERROR

**Python Representation**:

```python
from dataclasses import dataclass
from typing import Optional
import re

@dataclass
class Configuration:
    melcloud_email: str
    melcloud_password: str
    mqtt_host: str
    mqtt_port: int
    mqtt_username: Optional[str] = None
    mqtt_password: Optional[str] = None
    mqtt_base_topic: str = "homeassistant"
    poll_interval: int = 60
    log_level: str = "INFO"

    def validate(self) -> tuple[bool, list[str]]:
        """Validate configuration, return (valid, error_messages)."""
        errors = []

        # Email validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, self.melcloud_email):
            errors.append(f"Invalid email format: {self.melcloud_email}")

        # Password
        if not self.melcloud_password:
            errors.append("MELCloud password is required")

        # MQTT host
        if not self.mqtt_host:
            errors.append("MQTT host is required")

        # MQTT port
        if not (1 <= self.mqtt_port <= 65535):
            errors.append(f"MQTT port must be 1-65535, got {self.mqtt_port}")

        # Poll interval
        if not (10 <= self.poll_interval <= 3600):
            errors.append(f"Poll interval must be 10-3600 seconds, got {self.poll_interval}")

        # Log level
        if self.log_level not in ["DEBUG", "INFO", "WARNING", "ERROR"]:
            errors.append(f"Log level must be DEBUG/INFO/WARNING/ERROR, got {self.log_level}")

        return (len(errors) == 0, errors)

    @classmethod
    def from_options(cls, options: dict) -> "Configuration":
        """Load from Home Assistant options dict."""
        return cls(
            melcloud_email=options["melcloud_email"],
            melcloud_password=options["melcloud_password"],
            mqtt_host=options["mqtt_host"],
            mqtt_port=options["mqtt_port"],
            mqtt_username=options.get("mqtt_username"),
            mqtt_password=options.get("mqtt_password"),
            mqtt_base_topic=options.get("mqtt_base_topic", "homeassistant"),
            poll_interval=options.get("poll_interval", 60),
            log_level=options.get("log_level", "INFO")
        )
```

---

## State Management

### Device State Flow with pymelcloudhome

```
Add-on Startup → Create MelCloudHomeClient → login(email, password)
                            ↓
                    list_devices() [cached 5 min]
                            ↓
                    List[Device] objects
                            ↓
              For each device: get_device_state(device_id) [cached]
                            ↓
                    Dict[device_state]
                            ↓
              Build ClimateDevice wrapper objects
                            ↓
              Publish MQTT Discovery + Initial State
                            ↓
┌───────────────── Polling Loop ─────────────────┐
│                                                 │
│  1. Call list_devices() [uses cache]           │
│  2. For each device: get_device_state()        │
│  3. Compare with previous state                │
│  4. If changed: publish MQTT state update      │
│  5. Sleep(poll_interval)                       │
│                                                 │
└─────────────────────────────────────────────────┘
         ↓ (MQTT Command received)
         ↓
   MQTT Command Handler
         ↓
   Validate command payload
         ↓
   Call set_device_state(device_id, device_type, state_data)
         ↓
   pymelcloudhome → MELCloud API
         ↓
   Next poll cycle picks up updated state
```

**State Synchronization Strategy**:

1. **Startup**: Call `list_devices()` to get all devices (cached for 5 min by pymelcloudhome)
2. **Polling Loop**: Every N seconds (default 60)
   - Call `list_devices()` - returns cached data OR fetches if cache expired
   - For each device: call `get_device_state(device_id)` - returns cached state
   - Compare state with previous poll
   - Publish only **changed** values to MQTT to reduce message volume
3. **Command Handling**:
   - Receive MQTT command from Home Assistant
   - Call `set_device_state(device_id, device_type, state_data)`
   - Do NOT wait for confirmation - next poll will sync updated state
4. **Cache Behavior**: pymelcloudhome refreshes cache every 5 minutes automatically

**Command Flow**:

1. User changes setting in Home Assistant (e.g., temperature setpoint)
2. HA publishes to MQTT command topic (e.g., `homeassistant/climate/melcloud_abc123/set_temperature`)
3. Add-on MQTT callback receives command
4. Add-on validates command (temperature in range, valid mode, etc.)
5. Add-on calls `await client.set_device_state(device_id, device_type, {"setTemperature": 22.0})`
6. pymelcloudhome sends command to MELCloud API
7. MELCloud API returns success/failure
8. Add-on logs result
9. Next polling cycle (within 60 seconds) fetches updated state and publishes to MQTT

### Authentication & Session Flow with pymelcloudhome

```
Add-on Startup
      ↓
Load credentials from config
      ↓
Create MelCloudHomeClient instance
      ↓
await client.login(email, password)
      ↓
┌─────────── pymelcloudhome handles internally ───────────┐
│                                                          │
│  Playwright launches browser                            │
│  Navigate to MELCloud login                             │
│  Fill credentials                                        │
│  Extract session cookies/tokens                         │
│  Store session in client instance                       │
│                                                          │
└──────────────────────────────────────────────────────────┘
      ↓
Login successful → Start polling loop
      ↓
┌────────── During polling/API calls ──────────┐
│                                               │
│  API call → 401 Unauthorized?                │
│       ↓                                       │
│   YES → pymelcloudhome automatically          │
│         re-authenticates using stored         │
│         credentials and retries request       │
│       ↓                                       │
│   NO → Return result                          │
│                                               │
└───────────────────────────────────────────────┘
```

**Key Points**:

- **No manual session token management needed**
- pymelcloudhome stores credentials in memory after `login()`
- Automatic re-authentication on 401 errors
- Add-on only needs to keep `MelCloudHomeClient` instance alive
- On add-on restart: create new client and call `login()` again

### Error State Handling

**Network Failure**:

```
API Call → Timeout/ConnectionError → pymelcloudhome raises ApiError
                                            ↓
                                      Add-on catches error
                                            ↓
                                      Log warning
                                            ↓
                                      Exponential backoff
                                            ↓
                                      Retry next poll cycle
                                            ↓
                                      Maintain last known state in MQTT
```

**Authentication Failure**:

```
login() call → LoginError → Add-on catches
                                  ↓
                            Log ERROR with details
                                  ↓
                            Publish all devices as "unavailable"
                                  ↓
                            Continue running (wait for config update)
                                  ↓
                            Health endpoint reports "unhealthy"
```

**Device Command Failure**:

```
set_device_state() → ApiError or DeviceNotFound
                            ↓
                      Log ERROR with device_id
                            ↓
                      Do NOT update local state
                            ↓
                      Next poll will show actual device state
                            ↓
                      HA will reflect correct state from poll
```

**pymelcloudhome Built-in Error Handling**:

- `LoginError`: Raised when browser automation login fails (bad credentials, page changed)
- `ApiError`: Raised for API failures (includes `.status` and `.message` attributes)
- `DeviceNotFound`: Raised when operating on non-existent device
- Automatic retry on 401 with re-authentication

### MQTT Disconnection Handling

```
MQTT Disconnect Event (paho-mqtt callback)
           ↓
     Log WARNING
           ↓
     paho-mqtt automatic reconnect enabled
           ↓
     Wait for reconnection
           ↓
     On Reconnect:
           ↓
     ├─ Resubscribe to all command topics
     ├─ Republish all discovery messages (retain=True)
     └─ Publish availability "online" for all devices
```

---

## Relationship Diagram

```
┌─────────────────┐
│  Configuration  │──────┐
│  (HA Config UI) │      │
└─────────────────┘      │
                         ↓
                    Credentials
                    (email/password)
                         ↓
                ┌─────────────────────┐
                │ MelCloudHomeClient  │ ← pymelcloudhome library
                │  (session managed)  │
                └─────────────────────┘
                         ↓
                    login() call
                         ↓
              ┌──────────────────────┐
              │   MELCloud API       │
              │ (Playwright browser) │
              └──────────────────────┘
                         ↓
                  list_devices()
                         ↓
                ┌──────────────┐
                │Device objects│ (1..N)
                └──────────────┘
                         ↓
              get_device_state(device_id)
                         ↓
              ┌────────────────────┐
              │  ClimateDevice     │ (wrapper with state)
              │  + MQTT formatting │
              └────────────────────┘
                         ↓
              ┌──────────────────────┐
              │ MQTTDiscoveryMessage │
              └──────────────────────┘
                         ↓
              ┌──────────────┐
              │ MQTT Broker  │
              └──────────────┘
                         ↓
              ┌──────────────┐
              │Home Assistant│
              └──────────────┘
```

**Relationships**:

- Configuration → 1:1 → Credentials (from HA config UI)
- Credentials → 1:1 → MelCloudHomeClient (singleton instance)
- MelCloudHomeClient → 1:N → Device objects (from list_devices())
- Device → 1:1 → Device State (from get_device_state())
- ClimateDevice → 1:1 → MQTTDiscoveryMessage (mapping)
- Application → 1:1 → MQTT Broker (connection)
- MQTT Broker → 1:1 → Home Assistant (integration)

**Key Difference from Original Design**:

- ❌ No SessionToken entity (handled by pymelcloudhome)
- ❌ No manual session persistence to `/data/session.json`
- ✅ MelCloudHomeClient manages sessions internally
- ✅ Only credentials (email/password) stored/passed to client
- ✅ Automatic re-authentication on 401 errors

---

## Data Persistence

### /data/credentials.json (Optional - for development/testing)

```json
{
  "email": "user@example.com",
  "password": "encrypted_or_plain_password"
}
```

**Note**: In production, credentials come from Home Assistant config UI and should NOT be persisted to disk. This file is only for development convenience.

**Persistence Strategy**:

- Read credentials from HA Supervisor config (environment variables or options)
- Pass directly to `MelCloudHomeClient.login()` on startup
- Do NOT persist credentials to disk in production
- Keep credentials in memory only

### /data/device_cache.json (Optional - for faster restart)

Optional optimization to cache last known device states for immediate MQTT publishing on restart:

```json
{
  "devices": [
    {
      "device_id": "d3c4b5a6-f7e8-9012-cbad-876543210fed",
      "device_name": "Living Room AC",
      "device_type": "ataunit",
      "last_state": {
        "power": true,
        "setTemperature": 22.0,
        "roomTemperature": 23.5
      },
      "last_updated": "2025-10-28T10:30:00Z"
    }
  ]
}
```

**Use Case**:

- On add-on restart, publish last known states immediately
- User sees device status in HA without waiting for first poll
- First poll cycle will update with fresh data from MELCloud

**Not Critical**: Can be omitted - first poll cycle will populate states within 60 seconds.

### In-Memory State

**MelCloudHomeClient Instance**:

- Singleton instance created on startup
- Stores session cookies/tokens internally
- Stores credentials for re-authentication
- Manages cache (5-minute TTL by default)

**Device Cache**:

- Dictionary: `{device_id: ClimateDevice}`
- Updated on each poll cycle
- Used for state comparison (detect changes)
- Published to MQTT only when changes detected

**Connection State**:

- `melcloud_authenticated: bool` - True after successful login()
- `mqtt_connected: bool` - paho-mqtt connection status
- `last_poll_time: datetime` - timestamp of last successful poll
- `error_backoff: ExponentialBackoff` - retry delay calculator

**No Session Token Storage**:

- pymelcloudhome manages sessions internally
- Add-on does not need to persist/load session tokens
- Simpler architecture with fewer failure modes

---

## pymelcloudhome API Reference

### Core Methods

**`await client.login(email: str, password: str)`**

- Authenticates using Playwright browser automation
- Stores credentials internally for re-authentication
- Raises `LoginError` on failure
- Should be called once on startup

**`await client.list_devices() -> List[Device]`**

- Returns list of all devices
- Uses internal cache (default 5 minutes)
- Automatically refreshes cache if expired
- Each Device has: `.id`, `.given_display_name`, `.device_type`

**`await client.get_device_state(device_id: str) -> Optional[Dict[str, Any]]`**

- Returns cached device state (no new API call)
- Returns `None` if device not found
- State dict structure depends on device_type (ataunit vs atwunit)

**`await client.set_device_state(device_id: str, device_type: str, state_data: dict) -> dict`**

- Sends command to MELCloud API
- Returns response dict
- Raises `ApiError` on failure
- Automatically handles 401 (re-authenticates and retries)

**`await client.close()`**

- Closes aiohttp session
- Should be called on add-on shutdown
- Automatically called when using `async with` context manager

### Exception Handling

```python
from pymelcloudhome import MelCloudHomeClient
from pymelcloudhome.errors import LoginError, ApiError, DeviceNotFound

try:
    async with MelCloudHomeClient() as client:
        await client.login(email, password)
        devices = await client.list_devices()
        state = await client.get_device_state(devices[0].id)
        await client.set_device_state(devices[0].id, "ataunit", {"power": True})

except LoginError:
    # Bad credentials or login page changed
    logger.error("Authentication failed - check credentials")

except ApiError as e:
    # API call failed (includes status code)
    logger.error(f"API error: {e.status} - {e.message}")

except DeviceNotFound:
    # Device ID not found
    logger.error("Device not found in account")
```

### Configuration Options

```python
# Default: 5-minute cache
client = MelCloudHomeClient()

# Custom cache duration (in minutes)
client = MelCloudHomeClient(cache_duration_minutes=10)
```

**Recommended for Add-on**: Use default 5-minute cache, poll every 60 seconds. This ensures fresh data while minimizing API calls (12 API calls/hour per device).

---

## Summary of Changes from Original Design

### ✅ Simplified Architecture

1. **Session Management**: Delegated to pymelcloudhome (no manual token handling)
2. **Authentication**: Single `login()` call on startup, automatic renewal
3. **Caching**: Built-in 5-minute cache reduces API calls automatically
4. **Error Handling**: pymelcloudhome provides structured exceptions (LoginError, ApiError, DeviceNotFound)

### ✅ Reduced Complexity

- ❌ No SessionToken entity needed
- ❌ No session_manager.py module needed
- ❌ No /data/session.json persistence needed
- ✅ Simpler melcloud_client.py wrapper around pymelcloudhome
- ✅ Fewer edge cases to handle (pymelcloudhome handles 401 automatically)

### ✅ Better Reliability

- Automatic re-authentication on 401 errors
- Playwright-based login handles JavaScript-heavy pages
- Built-in caching reduces rate limit risks
- Clear exception types for error handling

### 🔄 Implementation Updates Needed

1. Update `app/melcloud_client.py` to use pymelcloudhome methods
2. Remove `app/session_manager.py` (no longer needed)
3. Simplify polling loop (no manual token checks)
4. Update error handling to catch pymelcloudhome exceptions
5. Update requirements.txt with correct pymelcloudhome version
6. Update sequence diagrams in plan.md to reflect pymelcloudhome usage
