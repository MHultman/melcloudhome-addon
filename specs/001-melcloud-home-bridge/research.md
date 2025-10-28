# Research & Technology Decisions

**Feature**: MELCloud Home Bridge  
**Date**: 2025-10-28  
**Purpose**: Document technology choices, integration patterns, and best practices

## 1. pymelcloudhome Integration

### Decision: Async Wrapper with Session Persistence

**Rationale**: pymelcloudhome provides synchronous API but add-on needs async operation for concurrent polling and MQTT handling. Session tokens persist across restarts to minimize authentication overhead.

**Implementation Pattern**:

```python
# Async wrapper pattern
async def authenticate_melcloud(email: str, password: str) -> SessionToken:
    """Authenticate with MELCloud and return session token."""
    loop = asyncio.get_event_loop()
    token = await loop.run_in_executor(None, melcloud_login, email, password)
    return token

# Session token persistence
class SessionManager:
    def __init__(self, data_dir: str = "/data"):
        self.token_file = Path(data_dir) / "session.json"

    async def load_token(self) -> Optional[SessionToken]:
        """Load token from disk, validate expiration."""
        if self.token_file.exists():
            data = json.loads(self.token_file.read_text())
            if data["expires_at"] > time.time():
                return SessionToken(**data)
        return None

    async def save_token(self, token: SessionToken):
        """Persist token to disk."""
        self.token_file.write_text(json.dumps(token.dict()))
```

**Alternatives Considered**:

- Direct sync calls: Rejected - blocks event loop, poor concurrent performance
- No session persistence: Rejected - excessive authentication overhead, rate limit risks

### Decision: Playwright for Web Authentication

**Rationale**: MELCloud uses JavaScript-heavy login flow. pymelcloudhome uses Playwright under the hood for reliable authentication across different MELCloud regions.

**Container Integration**:

- Install Playwright with Chromium during Docker build: `RUN playwright install --with-deps chromium`
- Headless mode: `browser = await playwright.chromium.launch(headless=True)`
- Screenshot capture on failure: `await page.screenshot(path="/data/auth_failure.png")`
- Browser restart on crash: Try-except with exponential backoff

**Resource Impact**: ~150MB for Chromium binaries, ~50MB runtime memory

---

## 2. MQTT Discovery Protocol

### Decision: Home Assistant MQTT Discovery for Climate Platform

**Rationale**: HA's MQTT Discovery protocol automates entity creation. Climate platform provides standardized interface for HVAC devices with mode selection, temperature control, and state reporting.

**Discovery Topic Pattern**:

```
<base_topic>/climate/<device_id>/config
```

**Discovery Payload Schema** (see contracts/mqtt-discovery-schema.json):

```json
{
  "name": "Living Room AC",
  "unique_id": "melcloud_12345",
  "device": {
    "identifiers": ["melcloud_12345"],
    "name": "Living Room AC",
    "manufacturer": "Mitsubishi Electric",
    "model": "MSZ-FH25VE",
    "sw_version": "1.2.3"
  },
  "modes": ["off", "heat", "cool", "auto", "dry", "fan_only"],
  "current_temperature_topic": "homeassistant/climate/melcloud_12345/state",
  "temperature_command_topic": "homeassistant/climate/melcloud_12345/set_temperature",
  "mode_state_topic": "homeassistant/climate/melcloud_12345/state",
  "mode_command_topic": "homeassistant/climate/melcloud_12345/set_mode",
  "availability_topic": "homeassistant/climate/melcloud_12345/availability",
  "temperature_unit": "C",
  "min_temp": 16,
  "max_temp": 31,
  "temp_step": 0.5
}
```

**State Topic Payload**:

```json
{
  "mode": "cool",
  "current_temperature": 23.5,
  "target_temperature": 22.0,
  "action": "cooling"
}
```

**Availability Topic**:

```
online / offline
```

**Alternatives Considered**:

- Manual YAML configuration: Rejected - requires user to configure each device manually
- Generic sensor entities: Rejected - no standardized climate controls in HA UI
- Custom integration: Rejected - MQTT approach is simpler, no HA core changes needed

---

## 3. Error Recovery & Resilience

### Decision: Exponential Backoff with Jitter

**Algorithm Parameters**:

- Initial delay: 1 second
- Max delay: 300 seconds (5 minutes)
- Multiplier: 2
- Jitter: ±20% random variance

**Implementation**:

```python
class ExponentialBackoff:
    def __init__(self, initial=1.0, maximum=300.0, multiplier=2.0):
        self.initial = initial
        self.maximum = maximum
        self.multiplier = multiplier
        self.current = initial

    def get_delay(self) -> float:
        """Get next delay with jitter."""
        delay = min(self.current, self.maximum)
        jitter = delay * 0.2 * (random.random() * 2 - 1)  # ±20%
        self.current *= self.multiplier
        return delay + jitter

    def reset(self):
        """Reset to initial delay on success."""
        self.current = self.initial
```

**Session Expiration Detection**:

- HTTP 401 response → immediate re-authentication
- Store credentials in memory (not disk) for re-auth
- Max 3 re-auth attempts before requiring config update

**MQTT Reconnection**:

- paho-mqtt automatic reconnect with `connect_async()` and `loop_start()`
- On disconnect callback: log warning, backoff timer
- On reconnect: republish all device availability

**Alternatives Considered**:

- Fixed interval retry: Rejected - can overwhelm services during outages
- Circuit breaker pattern: Rejected - unnecessary complexity for this use case
- No backoff: Rejected - violates good API citizenship, risks rate limiting

---

## 4. Multi-Architecture Container Builds

### Decision: Docker Buildx with QEMU Emulation

**Target Architectures**:

- amd64 (x86_64): Intel/AMD systems, most common
- aarch64 (ARM64): Raspberry Pi 4, modern ARM servers
- armv7 (ARM 32-bit): Raspberry Pi 3, older ARM devices

**Build Configuration** (build.yaml):

```yaml
build_from:
  amd64: ghcr.io/home-assistant/amd64-base-python:3.11
  aarch64: ghcr.io/home-assistant/aarch64-base-python:3.11
  armv7: ghcr.io/home-assistant/armv7-base-python:3.11
```

**Playwright Installation Challenge**:

- ARM architectures require explicit Chromium builds
- Solution: `playwright install --with-deps chromium` downloads arch-specific binaries
- Fallback: Pre-compiled Chromium for ARM if Playwright fails

**GitHub Actions Workflow**:

```yaml
- name: Set up QEMU
  uses: docker/setup-qemu-action@v2
- name: Set up Docker Buildx
  uses: docker/setup-buildx-action@v2
- name: Build multi-arch
  run: docker buildx build --platform linux/amd64,linux/arm64,linux/arm/v7 .
```

**Alternatives Considered**:

- Native builders per architecture: Rejected - complex CI setup, slow
- amd64 only: Rejected - excludes Raspberry Pi users (large HA community)
- Separate images per arch: Rejected - maintenance burden

---

## 5. Logging Strategy

### Decision: Loguru with Structured Fields

**Rationale**: Loguru provides cleaner API than stdlib logging, supports structured fields for log aggregation, excellent readability for users in HA log viewer.

**Configuration**:

```python
from loguru import logger
import sys

def setup_logging(level: str = "INFO"):
    logger.remove()  # Remove default handler
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level=level,
        colorize=False  # HA log viewer doesn't support colors
    )

    # Structured fields for critical events
    logger.bind(component="mqtt").info("Connected to broker", host=mqtt_host, port=mqtt_port)
    logger.bind(component="melcloud").info("Authenticated", email=email, device_count=len(devices))
```

**Log Levels Usage**:

- DEBUG: API request/response details, MQTT message payloads
- INFO: Startup, device discovery, configuration changes, successful operations
- WARNING: Recoverable errors (network timeouts, retrying), deprecated config
- ERROR: Authentication failures, unrecoverable errors, shutdown triggers

**Alternatives Considered**:

- stdlib logging: Rejected - verbose configuration, less readable output
- Print statements: Rejected - no level filtering, poor integration with HA
- JSON logging only: Rejected - hard for users to read in HA log viewer

---

## 6. Configuration Schema

### Decision: config.yaml with JSON Schema Validation

**Schema Definition** (see contracts/addon-config-schema.json):

```yaml
name: MELCloud Home Bridge
version: 1.0.0
slug: melcloudhome
description: Integrate Mitsubishi MELCloud devices via MQTT
arch:
  - amd64
  - aarch64
  - armv7
ports:
  8099/tcp: 8099
options:
  melcloud_email: ""
  melcloud_password: ""
  mqtt_host: core-mosquitto
  mqtt_port: 1883
  mqtt_username: ""
  mqtt_password: ""
  mqtt_base_topic: homeassistant
  poll_interval: 60
  log_level: INFO
schema:
  melcloud_email: email
  melcloud_password: password
  mqtt_host: str
  mqtt_port: port
  mqtt_username: str?
  mqtt_password: password?
  mqtt_base_topic: str
  poll_interval: int(10,3600)
  log_level: list(DEBUG|INFO|WARNING|ERROR)
```

**Validation Strategy**:

- HA Supervisor validates schema on save
- App validates loaded config on startup
- Missing required fields → ERROR log with specific field name
- Invalid types/ranges → ERROR log with expected format

**Alternatives Considered**:

- Environment variables only: Rejected - poor UX in HA Supervisor UI
- Python config files: Rejected - security risk, violates HA conventions
- No validation: Rejected - poor error messages, user frustration

---

## 7. Health Endpoint Design

### Decision: Simple HTTP Server with JSON Status

**Implementation** (app/health_server.py):

```python
from aiohttp import web

async def health_handler(request):
    status = {
        "status": "healthy" if all_systems_ok() else "unhealthy",
        "melcloud": {
            "authenticated": session_manager.has_valid_token(),
            "last_poll": last_poll_time.isoformat(),
            "device_count": len(discovered_devices)
        },
        "mqtt": {
            "connected": mqtt_client.is_connected(),
            "broker": mqtt_config.host
        },
        "uptime_seconds": time.time() - start_time
    }
    status_code = 200 if status["status"] == "healthy" else 503
    return web.json_response(status, status=status_code)

app = web.Application()
app.router.add_get('/healthz', health_handler)
web.run_app(app, host='0.0.0.0', port=8099)
```

**Health Criteria**:

- Healthy: Valid MELCloud session AND MQTT connected
- Unhealthy: Auth failed OR MQTT disconnected for >5 minutes

**Alternatives Considered**:

- No health endpoint: Rejected - no way for Supervisor to monitor add-on
- Complex health checks: Rejected - adds latency, complexity
- Separate metrics endpoint: Rejected - overkill for this use case

---

## Summary

All technical decisions align with constitution principles:

- ✅ Code Clarity: Simple patterns, no clever abstractions
- ✅ Simple Logging: Loguru with clear levels
- ✅ Minimal Config: 4 required fields, sensible defaults
- ✅ Containerized: Playwright fully contained
- ✅ HA Conventions: config.yaml schema, MQTT Discovery
- ✅ Testability: All patterns support mocking
- ✅ Documentation: Patterns documented for contributors
