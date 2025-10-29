# Feature Specification: MELCloud Home Bridge

**Feature Branch**: `001-melcloud-home-bridge`  
**Created**: 2025-10-28  
**Status**: Draft  
**Input**: User description: "MELCloud Home Bridge - Home Assistant add-on with Playwright-backed pymelcloudhome and MQTT Discovery"

## User Scenarios & Testing _(mandatory)_

### User Story 1 - Install and Configure Add-on (Priority: P1)

A Home Assistant user wants to integrate their Mitsubishi MELCloud climate devices (air conditioners, heat pumps) into Home Assistant without complex setup. They install the add-on through the Home Assistant Supervisor UI, configure their MELCloud credentials and MQTT settings, and start the add-on.

**Why this priority**: This is the foundational user journey - without successful installation and configuration, no other functionality is possible. This establishes the bridge between MELCloud and Home Assistant.

**Independent Test**: Can be fully tested by installing the add-on, entering configuration values, starting it, and verifying the add-on status shows as running with no errors in logs. Delivers value by establishing the connection infrastructure.

**Acceptance Scenarios**:

1. **Given** Home Assistant with Supervisor and MQTT broker running, **When** user installs MELCloud Home Bridge add-on from store, **Then** add-on appears in add-ons list with "Not running" status
2. **Given** add-on installed, **When** user opens add-on configuration page, **Then** configuration form displays fields for MELCloud email, password, MQTT host, MQTT port, MQTT credentials, base topic, poll interval, and log level
3. **Given** user enters valid configuration values, **When** user starts the add-on, **Then** add-on status changes to "Running" within 30 seconds
4. **Given** add-on running with invalid MELCloud credentials, **When** authentication fails, **Then** add-on logs show clear authentication error message and add-on remains running (ready for config fix)
5. **Given** add-on running with invalid MQTT settings, **When** MQTT connection fails, **Then** add-on logs show clear MQTT connection error and add-on remains running with retry attempts

---

### User Story 2 - Automatic Device Discovery (Priority: P1)

After successful configuration, the add-on automatically discovers all MELCloud climate devices associated with the user's account and publishes them to Home Assistant via MQTT Discovery protocol. Devices appear in Home Assistant's device registry without manual configuration.

**Why this priority**: This is the core value proposition - automatic integration of MELCloud devices into Home Assistant. Without this, users must manually configure each device.

**Independent Test**: Can be fully tested by configuring the add-on with a valid MELCloud account that has devices, waiting for the discovery cycle to complete, and verifying that climate entities appear in Home Assistant's MQTT integration. Delivers immediate value by making devices controllable.

**Acceptance Scenarios**:

1. **Given** add-on running with valid credentials, **When** first polling cycle completes, **Then** each MELCloud device appears as a climate entity in Home Assistant
2. **Given** device discovered, **When** viewing device in HA, **Then** device shows manufacturer as "Mitsubishi Electric", model information from MELCloud, and all available controls (mode, temperature setpoint, current temperature)
3. **Given** user has 5 MELCloud devices, **When** discovery completes, **Then** all 5 devices are published with unique entity IDs based on device names
4. **Given** user adds a new device to their MELCloud account, **When** next polling cycle runs, **Then** new device automatically appears in Home Assistant without restarting add-on
5. **Given** user removes a device from MELCloud account, **When** next polling cycle runs, **Then** device entity shows as unavailable in Home Assistant

---

### User Story 3 - Real-time Device Control and Monitoring (Priority: P1)

Users control their MELCloud climate devices through Home Assistant's UI (Lovelace dashboards, climate cards, automations). Changes made in Home Assistant are sent to MELCloud, and current device states are continuously synchronized from MELCloud to Home Assistant.

**Why this priority**: This completes the bidirectional integration - users can both monitor and control devices. This is essential for the add-on to be useful in daily operation.

**Independent Test**: Can be fully tested by changing a device's temperature or mode in Home Assistant, verifying the change reflects in the MELCloud app, then changing settings in MELCloud app and verifying Home Assistant updates. Delivers full control integration value.

**Acceptance Scenarios**:

1. **Given** device discovered in HA, **When** user changes temperature setpoint in HA climate card, **Then** new setpoint is sent to MELCloud API and device updates within 10 seconds
2. **Given** device operating, **When** user changes mode (heat/cool/auto/fan/dry) in HA, **Then** device mode changes in MELCloud and physical device responds
3. **Given** device state changes in MELCloud app, **When** next polling cycle runs, **Then** Home Assistant climate entity updates to reflect current state
4. **Given** device is turned off physically, **When** next polling cycle runs, **Then** Home Assistant entity shows device as off
5. **Given** device loses internet connection, **When** polling cycle cannot reach device, **Then** Home Assistant entity shows as unavailable with clear availability status

---

### User Story 4 - Resilient Operation with Error Recovery (Priority: P2)

The add-on handles transient network issues, API rate limits, session expiration, and MELCloud service outages gracefully. It automatically recovers from errors without requiring user intervention or add-on restart.

**Why this priority**: Ensures long-term reliability in production use. While not essential for initial functionality, it's critical for user satisfaction and reducing support burden.

**Independent Test**: Can be fully tested by simulating various failure scenarios (disconnect network, invalidate session token, stop MQTT broker) and verifying automatic recovery when conditions normalize. Delivers reliability value.

**Acceptance Scenarios**:

1. **Given** add-on running normally, **When** network connection is lost, **Then** add-on logs network error and uses exponential backoff to retry connection
2. **Given** MELCloud session expired (401 error), **When** API call fails with 401, **Then** add-on automatically re-authenticates using stored credentials and retries the operation
3. **Given** MQTT broker restarts, **When** MQTT connection drops, **Then** add-on detects disconnection, attempts reconnection with backoff, and republishes device availability when reconnected
4. **Given** MELCloud API returns rate limit error, **When** rate limit detected, **Then** add-on extends polling interval temporarily and logs the rate limit
5. **Given** add-on has been running for 7 days, **When** memory or connection leaks occur, **Then** add-on maintains stable memory usage under 200MB and automatically refreshes connections

---

### User Story 5 - Health Monitoring and Diagnostics (Priority: P3)

System administrators and advanced users can monitor add-on health status through a health check endpoint and detailed logs. This enables integration with monitoring systems and troubleshooting issues.

**Why this priority**: Useful for advanced users and troubleshooting, but not essential for basic operation. Enhances operational visibility.

**Independent Test**: Can be fully tested by accessing the health endpoint via HTTP GET, reviewing various log levels, and verifying diagnostic information helps identify issues. Delivers observability value.

**Acceptance Scenarios**:

1. **Given** add-on running, **When** health endpoint `/healthz` is accessed on port 8099, **Then** endpoint returns HTTP 200 with JSON status including MELCloud connection status, MQTT connection status, last successful poll time, and device count
2. **Given** MELCloud authentication failing, **When** health endpoint accessed, **Then** endpoint returns HTTP 503 with error details in JSON
3. **Given** log level set to DEBUG, **When** add-on performs operations, **Then** logs show detailed API requests, MQTT messages, and session management details
4. **Given** log level set to INFO (default), **When** add-on operates normally, **Then** logs show startup messages, device discovery events, configuration changes, and errors without excessive verbosity
5. **Given** error occurs (auth failure, network timeout), **When** user checks logs, **Then** error messages are human-readable with clear context and suggested resolution steps

---

### Edge Cases

- What happens when user's MELCloud account has no devices? (Add-on runs successfully, logs indicate zero devices discovered, health endpoint shows healthy status)
- What happens when MELCloud device has special characters in name? (Device name is sanitized for MQTT topic compatibility while preserving readability)
- What happens when user changes MELCloud password externally? (Add-on receives 401 on next poll, re-auth fails, logs clear message that credentials need updating in config)
- What happens when MQTT broker has authentication enabled but user provides wrong credentials? (Add-on fails to connect to MQTT, logs authentication error, remains running ready for config fix)
- What happens when multiple Home Assistant instances use the same MQTT base topic? (Each instance receives all discovery messages; suggest unique base topics in documentation)
- What happens when MELCloud API is temporarily down (500 errors)? (Add-on logs API errors, uses exponential backoff, maintains last known device states until API recovers)
- What happens when user restarts Home Assistant while add-on is polling? (Add-on continues running in container, MQTT connection may briefly disconnect but reconnects automatically)
- What happens when add-on is stopped and restarted? (Session token loaded from `/data/session.json` if valid, otherwise re-authenticates)

## Requirements _(mandatory)_

### Functional Requirements

- **FR-001**: Add-on MUST authenticate to MELCloud using user-provided email and password credentials
- **FR-002**: Add-on MUST persist authenticated session tokens to `/data/session.json` to avoid re-authentication on every poll
- **FR-003**: Add-on MUST discover all climate devices associated with the MELCloud account on startup and during periodic polls
- **FR-004**: Add-on MUST publish discovered devices to MQTT broker using Home Assistant's MQTT Discovery protocol
- **FR-005**: Add-on MUST include device metadata in MQTT Discovery messages (manufacturer, model, unique_id, device name)
- **FR-006**: Add-on MUST publish climate entity attributes: current temperature, target temperature setpoint, HVAC mode (heat/cool/auto/fan_only/dry/off), availability status
- **FR-007**: Add-on MUST subscribe to MQTT command topics to receive control commands from Home Assistant (setpoint changes, mode changes)
- **FR-008**: Add-on MUST send control commands to MELCloud API when receiving commands via MQTT
- **FR-009**: Add-on MUST poll MELCloud API at user-configured intervals (default 60 seconds) to retrieve current device states
- **FR-010**: Add-on MUST implement exponential backoff for retry logic when network requests fail
- **FR-011**: Add-on MUST detect session expiration (HTTP 401) and automatically re-authenticate using stored credentials
- **FR-012**: Add-on MUST publish device availability status based on MELCloud API reachability and device online status
- **FR-013**: Add-on MUST validate configuration on startup and log clear error messages for invalid or missing required settings
- **FR-014**: Add-on MUST expose health check endpoint on port 8099 at `/healthz` path returning JSON status
- **FR-015**: Add-on MUST support configuration via Home Assistant Supervisor config UI with schema validation
- **FR-016**: Add-on MUST include Playwright and Chromium browser within container image (no external dependencies)
- **FR-017**: Add-on MUST support multi-architecture builds (amd64, aarch64, armv7)
- **FR-018**: Add-on MUST log operational events using structured, human-readable format with configurable log levels (DEBUG, INFO, WARNING, ERROR)
- **FR-019**: Add-on MUST provide default MQTT settings compatible with Home Assistant's core-mosquitto add-on (localhost:1883, no auth by default)
- **FR-020**: Add-on MUST handle graceful shutdown when stopped by Supervisor (close connections, flush logs, save session state)

### Key Entities

- **Climate Device**: Represents a Mitsubishi MELCloud-connected HVAC unit. Attributes include device ID (from MELCloud), device name, current temperature, target temperature setpoint, HVAC mode (heat/cool/auto/fan_only/dry/off), online status, and firmware version. Discovered from MELCloud API and mapped to Home Assistant climate entity.

- **Session Token**: Authentication credential persisted to `/data/session.json`. Contains MELCloud API token, expiration timestamp, and user account identifier. Used to maintain authenticated session across add-on restarts and polling cycles.

- **MQTT Discovery Message**: Configuration payload sent to Home Assistant's MQTT Discovery topic. Contains device metadata (manufacturer, model, identifiers), entity configuration (name, unique_id, device_class, state topic, command topic), and availability topic. Follows Home Assistant's MQTT Discovery schema for climate platforms.

- **Configuration**: User-provided settings loaded from Home Assistant config UI. Required fields: MELCloud email, MELCloud password, MQTT host, MQTT port. Optional fields: MQTT username, MQTT password, MQTT base topic (default: homeassistant), poll interval (default: 60 seconds), log level (default: INFO).

## Success Criteria _(mandatory)_

### Measurable Outcomes

- **SC-001**: Users can complete add-on installation and configuration in under 5 minutes, including entering credentials and verifying devices appear in Home Assistant
- **SC-002**: Device discovery completes within 60 seconds of add-on startup for accounts with up to 10 devices
- **SC-003**: Temperature or mode changes made in Home Assistant are reflected on physical MELCloud devices within 15 seconds under normal network conditions
- **SC-004**: Add-on maintains stable operation for at least 7 days continuously without requiring restart, consuming less than 200MB memory
- **SC-005**: Add-on automatically recovers from network interruptions within 5 minutes of connectivity restoration without user intervention
- **SC-006**: Add-on successfully authenticates and operates on Home Assistant installations using core-mosquitto add-on with default settings (no MQTT configuration required beyond defaults)
- **SC-007**: Health check endpoint responds within 1 second and accurately reflects current connection status (MELCloud and MQTT)
- **SC-008**: 95% of users can identify and resolve common issues (authentication failures, MQTT connection errors) using log messages without consulting external documentation
- **SC-009**: Add-on container image builds successfully for all three target architectures (amd64, aarch64, armv7) without manual intervention
- **SC-010**: User can change add-on configuration (poll interval, log level) and apply changes by restarting add-on without losing discovered device configuration in Home Assistant

## Assumptions _(mandatory)_

- Home Assistant Supervisor environment is available (HAOS, Container, or Supervised installation types)
- MQTT broker is installed and accessible (either core-mosquitto add-on or external broker)
- User has valid MELCloud account with at least view permissions on devices
- Home Assistant MQTT integration is enabled and configured to use the same MQTT broker
- Network connectivity exists between Home Assistant host and MELCloud API endpoints (internet access required)
- MELCloud API remains stable and compatible with pymelcloudhome library
- Users have basic familiarity with Home Assistant add-on installation process
- Session tokens from MELCloud API have reasonable expiration timeframes (hours to days, not minutes)

## Dependencies _(include if there are external dependencies)_

- **pymelcloudhome**: Python library for MELCloud API interaction (provides authentication, device discovery, state management, control commands)
- **Playwright**: Browser automation framework for handling JavaScript-heavy MELCloud web authentication flows
- **Chromium**: Browser engine included in container for Playwright execution
- **paho-mqtt**: Python MQTT client library for broker communication
- **Home Assistant Supervisor**: Provides add-on lifecycle management, configuration UI, and logging integration
- **Home Assistant MQTT Integration**: Receives MQTT Discovery messages and creates/manages climate entities
- **MQTT Broker**: Message broker for communication between add-on and Home Assistant (typically core-mosquitto add-on)

## Out of Scope _(include if scope boundaries need clarification)_

- Support for other Mitsubishi cloud services (kumo cloud, MELCloud alternative regions with different APIs)
- Direct device control without MELCloud cloud service (local LAN API not supported by MELCloud devices)
- Historical data storage or analytics (use Home Assistant's built-in recorder for history)
- Advanced climate features not supported by MELCloud API (fan speed control if not exposed, louver position control)
- GUI configuration of individual device mappings (all discovered devices automatically published)
- Integration with non-climate MELCloud devices if they exist (focus is HVAC climate control)
- MQTT broker installation or configuration (assumes pre-existing broker)
- Home Assistant installation or MQTT integration setup (assumes existing functional HA installation)
