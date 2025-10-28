# Data Model

**Feature**: MELCloud Home Bridge  
**Date**: 2025-10-28  
**Purpose**: Define entities, state management, and data flows

## Entity Definitions

### 1. ClimateDevice

Represents a Mitsubishi MELCloud HVAC unit discovered from the API.

**Attributes**:

- `device_id` (str): Unique identifier from MELCloud API (e.g., "12345")
- `device_name` (str): User-friendly name from MELCloud (e.g., "Living Room AC")
- `model` (str): Device model number (e.g., "MSZ-FH25VE")
- `firmware_version` (str): Firmware version string
- `current_temperature` (float): Current room temperature in Celsius
- `target_temperature` (float): Target setpoint temperature in Celsius
- `hvac_mode` (str): Operating mode - one of: "off", "heat", "cool", "auto", "dry", "fan_only"
- `hvac_action` (str): Current action - one of: "off", "heating", "cooling", "drying", "fan"
- `online` (bool): Device reachability from MELCloud
- `min_temp` (float): Minimum allowed temperature (typically 16°C)
- `max_temp` (float): Maximum allowed temperature (typically 31°C)
- `temp_step` (float): Temperature adjustment increment (typically 0.5°C)

**State Transitions**:

```
off → [heat, cool, auto, dry, fan_only]
heat → [off, cool, auto, dry, fan_only]
cool → [off, heat, auto, dry, fan_only]
auto → [off, heat, cool, dry, fan_only]
dry → [off, heat, cool, auto, fan_only]
fan_only → [off, heat, cool, auto, dry]
```

**Validation Rules**:

- `target_temperature` must be within [min_temp, max_temp]
- `target_temperature` must be multiple of temp_step
- `hvac_mode` must be one of valid modes
- `device_id` must be unique across all devices

**Python Representation**:

```python
from dataclasses import dataclass
from typing import Literal

@dataclass
class ClimateDevice:
    device_id: str
    device_name: str
    model: str
    firmware_version: str
    current_temperature: float
    target_temperature: float
    hvac_mode: Literal["off", "heat", "cool", "auto", "dry", "fan_only"]
    hvac_action: Literal["off", "heating", "cooling", "drying", "fan"]
    online: bool
    min_temp: float = 16.0
    max_temp: float = 31.0
    temp_step: float = 0.5

    def validate_target_temperature(self, temp: float) -> bool:
        """Validate temperature is within bounds and correct increment."""
        if temp < self.min_temp or temp > self.max_temp:
            return False
        if (temp - self.min_temp) % self.temp_step != 0:
            return False
        return True

    def to_mqtt_state(self) -> dict:
        """Convert to MQTT state topic payload."""
        return {
            "mode": self.hvac_mode,
            "action": self.hvac_action,
            "current_temperature": self.current_temperature,
            "target_temperature": self.target_temperature
        }
```

---

### 2. SessionToken

Authentication credential for MELCloud API access.

**Attributes**:

- `access_token` (str): JWT or session token from MELCloud
- `refresh_token` (str, optional): Token for refreshing session
- `expires_at` (float): Unix timestamp when token expires
- `user_id` (str): MELCloud account identifier
- `context_key` (str, optional): API context key if required by MELCloud

**State Lifecycle**:

```
None → Authenticated → Expired → Re-authenticated
         ↓                ↓
    Valid (polling)    Invalid (401) → Re-auth
```

**Validation Rules**:

- `expires_at` must be future timestamp
- `access_token` must be non-empty string
- Tokens expire after 24 hours (typical MELCloud behavior)

**Python Representation**:

```python
from dataclasses import dataclass
import time

@dataclass
class SessionToken:
    access_token: str
    user_id: str
    expires_at: float
    refresh_token: str = ""
    context_key: str = ""

    def is_valid(self) -> bool:
        """Check if token is not expired."""
        return time.time() < self.expires_at

    def to_json(self) -> dict:
        """Serialize for /data/session.json."""
        return {
            "access_token": self.access_token,
            "user_id": self.user_id,
            "expires_at": self.expires_at,
            "refresh_token": self.refresh_token,
            "context_key": self.context_key
        }

    @classmethod
    def from_json(cls, data: dict) -> "SessionToken":
        """Deserialize from /data/session.json."""
        return cls(**data)
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
```

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
```

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

### Device State Flow

```
MELCloud API → ClimateDevice → MQTT State Topic → Home Assistant
     ↑                                                    ↓
     └────────── MQTT Command Topic ←──────────────────┘
```

**State Synchronization**:

1. Poll MELCloud API every N seconds (configurable)
2. Update ClimateDevice objects in memory
3. Publish state changes to MQTT state topics
4. Home Assistant updates UI based on state topics

**Command Flow**:

1. User changes setting in Home Assistant
2. HA publishes to MQTT command topic
3. Add-on receives command via MQTT subscription
4. Add-on calls MELCloud API to execute command
5. Next poll cycle syncs updated state back to HA

### Session State Flow

```
Startup → Load /data/session.json → Valid? → Use Token
              ↓                         ↓
         Not Found                  Invalid/Expired
              ↓                         ↓
         Authenticate ← ─── ─── ─── ─ ┘
              ↓
         Save Token → /data/session.json
```

**Token Refresh Strategy**:

- Check token validity before each API call
- If expired (401 response), re-authenticate immediately
- Save new token to disk after successful auth
- Max 3 re-auth attempts before requiring user config update

### Error State Handling

**Network Failure**:

```
API Call → Timeout/Error → Log Warning → Exponential Backoff → Retry
                               ↓
                         Maintain Last Known State
```

**Authentication Failure**:

```
API Call → 401 Response → Re-authenticate → Success → Continue
                              ↓               ↓
                         3 Attempts      Failure → Error Log
                                                     ↓
                                              Require Config Update
```

**MQTT Disconnection**:

```
Disconnect Event → Log Warning → Automatic Reconnect (paho-mqtt)
                       ↓
                 Publish "offline" to availability topics
                       ↓
                 Wait for Reconnect
                       ↓
                 Publish "online" + Republish Discovery
```

---

## Relationship Diagram

```
┌─────────────────┐
│  Configuration  │──────┐
└─────────────────┘      │
                         ↓
┌─────────────────┐   ┌──────────────┐
│  SessionToken   │←──│ MELCloud API │
└─────────────────┘   └──────────────┘
        ↓                     ↓
        │              ┌──────────────┐
        │              │ClimateDevice │ (1..N)
        │              └──────────────┘
        │                     ↓
        │              ┌──────────────────────┐
        └─────────────→│ MQTTDiscoveryMessage │
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

- Configuration → 1:1 → Application (singleton)
- SessionToken → 1:1 → MELCloud API (current session)
- MELCloud API → 1:N → ClimateDevice (discovered devices)
- ClimateDevice → 1:1 → MQTTDiscoveryMessage (mapping)
- Application → 1:1 → MQTT Broker (connection)
- MQTT Broker → 1:1 → Home Assistant (integration)

---

## Data Persistence

### /data/session.json

```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user_id": "user@example.com",
  "expires_at": 1698537600.0,
  "refresh_token": "",
  "context_key": "context_xyz"
}
```

**Persistence Strategy**:

- Write after successful authentication
- Read on startup before authentication
- Delete on authentication failure (3 attempts)
- Atomic write (write temp file, rename)

### In-Memory State

**Device Cache**:

- Dictionary: `{device_id: ClimateDevice}`
- Updated on each poll cycle
- Used for state comparison (detect changes)

**Connection State**:

- `melcloud_authenticated: bool`
- `mqtt_connected: bool`
- `last_poll_time: datetime`
- `error_backoff: ExponentialBackoff`

No other persistent storage required - Home Assistant maintains entity state.
