# Changelog

All notable changes to MELCloud Home Bridge will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.4.5] - 2025-10-29

### Fixed

- **Critical**: Commands now use correct camelCase API keys
  - Fixed `setTankWaterTemperature` (was `SetTankWaterTemperature`)
  - Fixed `forcedHotWaterMode` (was `ForcedHotWaterMode`) - now sends boolean
  - Fixed `prohibitHotWater` (was `ProhibitHotWater`) - now sends boolean
  - Fixed ATW temperature commands to use `setTemperatureZone1` (was `setTemperature`)
  - Removed unnecessary string conversions - API accepts proper types
  - Commands now actually execute on MELCloud API

## [1.4.4] - 2025-10-29

### Fixed

- **Critical**: Temperature commands and other MQTT commands now work correctly
  - Fixed "No event loop available" error when sending commands from Home Assistant
  - MQTT callbacks now properly schedule async operations using `run_coroutine_threadsafe()`
  - Commands like set_temperature, set_tank_temperature, etc. now execute successfully

## [1.4.3] - 2025-10-29

### Changed

- Version bump for release

## [1.4.2] - 2025-10-29

### Changed

- Map MELCloud operation modes to Home Assistant climate modes
  - Climate entity `mode` now shows: `heat`, `cool`, `auto`, `off` (HA standard)
  - Original MELCloud mode preserved in `operation_mode` attribute
  - Ensures proper integration with HA climate entity controls

## [1.2.1] - 2025-10-29

### Fixed

- **Enhanced Debug Logging** - Added comprehensive debug logging for troubleshooting state issues
  - Log raw MELCloud API responses when fetching device state
  - Log device settings array structure and sample settings for ATW devices
  - Log device capabilities (hasHotWater, hasZone2, temperature ranges)
  - Log power state extraction and online status
  - Log ATW temperature values (current, target, tank, tank_target)
  - Log operation modes and zone settings
  - Log final MQTT state payload before publishing
  - Log MQTT publish operations with topic and payload details

### Improved

- Better diagnostics for "unknown" state issues
- More detailed logging of state conversion process
- Enhanced visibility into ClimateDevice model state extraction
- Improved MQTT payload visibility for debugging

### Usage

To enable debug logging, set `log_level: "DEBUG"` in the addon configuration:

```yaml
log_level: "DEBUG"
```

This will provide detailed logs showing:

- Raw API responses from MELCloud
- State extraction from device settings
- MQTT payload generation
- Publishing operations

## [1.2.0] - 2025-10-28

### Added

- **Full ATW Device Control Support** - Complete control interface for Air-to-Water heat pump devices
  - Power switch entity for device on/off control
  - Zone 1 temperature setpoint (16-30°C with 0.5°C steps)
  - Zone 1 operation mode selector (HeatRoomTemperature, HeatFlowTemperature, HeatCurve)
  - Zone 1 heat flow temperature control (20-60°C)
  - Zone 1 cool flow temperature control (5-25°C)
  - Hot water tank temperature setpoint (40-60°C) when supported
  - Forced hot water mode switch when supported
  - Zone 2 controls (temperature, operation mode, flow temperatures) when supported
- **Additional ATW Sensors** - Enhanced monitoring for ATW devices
  - Tank water temperature (current)
  - Tank water temperature (target/setpoint)
  - Zone operation mode sensor
  - Forced hot water mode binary sensor
  - Prohibit hot water binary sensor
  - Standby mode binary sensor
  - Error state binary sensor with error code
- **State Synchronization** - All control values are properly synchronized back to Home Assistant
- **Capability-Based Discovery** - Control entities are automatically created based on device capabilities (hasHotWater, hasZone2)

### Improved

- Enhanced MQTT command routing with support for 12+ new command topics
- Improved state payload with all controllable parameters exposed
- Better command validation with device-specific temperature ranges
- Extended command handler with ATW-specific control methods
- Automatic state refresh after command execution
- Comprehensive logging for all control operations

### Technical

- Added `_publish_atw_controls()` method to mqtt_bridge.py for control entity discovery
- Extended CommandHandler with 7 new control methods for ATW devices
- Enhanced `to_mqtt_state()` in ClimateDevice model to include all control parameters
- Updated MQTT subscription logic to handle all new command topics
- Implemented proper capability detection from device state
- Added command topic routing in main.py for all new entity types

### Changed

- Updated config.yaml version to 1.2.0
- Enhanced description to mention "full ATW control support"

## [1.1.0] - 2025-10-28

### Added

- Current temperature display in Home Assistant climate entity
- Temperature state templates for proper HA integration
- Comprehensive ATW sensor suite (tank temps, operation modes, status flags)

### Changed

- Updated pymelcloudhome dependency to v0.3.0
- Switched from Playwright to Pyppeteer for browser automation
- Switched to system Chromium (`/usr/bin/chromium`) for browser automation
- Removed Playwright browser installation step from Dockerfile
- Simplified Docker image by using Alpine Linux system Chromium

### Improved

- Reduced Docker image size by eliminating bundled browser binaries
- Enhanced ARM64/Raspberry Pi support with native system Chromium
- Improved authentication reliability across all architectures
- Better documentation of browser automation implementation

## [1.0.0] - 2025-10-28

### Added

- Initial release of MELCloud Home Bridge
- Automatic device discovery via MQTT Discovery protocol
- Support for ATA (Air-to-Air) climate devices
- Support for ATW (Air-to-Water) hydronic heating devices
- Bidirectional control (Home Assistant ↔ MELCloud)
- Real-time state synchronization with configurable poll interval
- Automatic session management and re-authentication
- Exponential backoff retry logic for network failures
- Health check endpoint on port 8099
- Multi-architecture support (amd64, aarch64, armv7)
- Structured logging with credential sanitization
- Graceful shutdown handling (SIGTERM, SIGINT)
- Comprehensive configuration validation
- MQTT broker reconnection logic
- Zone 2 support for multi-zone ATW devices
- Error state monitoring and reporting
- Human-readable log format with Loguru
- Pydantic v2 for configuration and data validation
- FastAPI + Uvicorn for health endpoint

### Technical

- Python 3.11 runtime
- Home Assistant Supervisor add-on architecture
- Playwright-based authentication with pre-installed Chromium
- pymelcloudhome library for MELCloud API integration
- paho-mqtt for MQTT communication
- Alpine Linux container base

### Documentation

- Installation guide with step-by-step instructions
- Configuration reference
- Troubleshooting section
- Usage examples
- Health monitoring documentation

[1.0.0]: https://github.com/MHultman/melcloudhome-addon/releases/tag/v1.0.0
