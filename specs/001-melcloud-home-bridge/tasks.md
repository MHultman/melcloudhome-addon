# Tasks: MELCloud Home Bridge

**Input**: Design documents from `/specs/001-melcloud-home-bridge/`  
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/  
**Branch**: `001-melcloud-home-bridge`  
**Date**: 2025-10-28

**Tests**: Acceptance tests are included per milestone as requested by user.

**Organization**: Tasks are grouped by implementation milestones (not user stories) per user request. Each milestone represents a logical implementation phase with acceptance tests.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Maps to user story from spec.md (US1-US5)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Container & Dependencies)

**Milestone**: Container & dependencies  
**Purpose**: Create Docker container with Playwright, Chromium, and Python runtime. Set up project structure and dependency management.

**Maps to**: Infrastructure for all user stories (US1-US5)

### Implementation Tasks

- [x] T001 Create root directory structure (app/, tests/, .github/)
- [x] T002 Create Dockerfile with Python 3.11 base image in Dockerfile
- [x] T003 [P] Create requirements.txt with dependencies (playwright>=1.40.0, pymelcloudhome>=1.0.0, paho-mqtt>=1.6.1, aiohttp>=3.9.0, loguru>=0.7.0, pytest, pytest-asyncio, pytest-mock)
- [x] T004 [P] Create build.yaml with multi-arch configuration (amd64, aarch64, armv7) in build.yaml
- [x] T005 Add Playwright installation to Dockerfile (RUN playwright install --with-deps chromium)
- [x] T006 [P] Create config.yaml with add-on metadata and options schema in config.yaml
- [x] T007 [P] Create run.sh entrypoint script in run.sh
- [x] T008 Create app/**init**.py module initializer

### Acceptance Tests for Milestone 1

- [ ] T009 [P] Test: Verify Docker image builds successfully for amd64 architecture
- [ ] T010 [P] Test: Verify Docker image builds successfully for aarch64 architecture
- [ ] T011 [P] Test: Verify Docker image builds successfully for armv7 architecture
- [ ] T012 Test: Verify Chromium launches in headless mode inside container
- [ ] T013 Test: Verify all Python dependencies install without conflicts
- [ ] T014 Test: Verify container starts and runs run.sh entrypoint successfully

**Checkpoint**: Container infrastructure ready for application code

---

## Phase 2: Foundational (Config & Logging)

**Milestone**: Config & logging  
**Purpose**: Implement configuration loading, validation, and structured logging setup. Required before any business logic.

**Maps to**: US1 (Install and Configure Add-on)

**⚠️ CRITICAL**: No further user story work can begin until this phase is complete

### Implementation Tasks

- [x] T015 Create app/config.py with Configuration dataclass matching config.yaml schema
- [x] T016 Add configuration loading from Supervisor options in app/config.py
- [x] T017 Add configuration validation with clear error messages in app/config.py
- [x] T018 Add default values (mqtt_host=localhost, mqtt_port=1883, base_topic=homeassistant, poll_interval=60, log_level=INFO) in app/config.py
- [x] T019 Create app/logging_conf.py with Loguru setup
- [x] T020 Add log level configuration (DEBUG/INFO/WARNING/ERROR) in app/logging_conf.py
- [x] T021 Add human-readable log format with structured fields in app/logging_conf.py
- [x] T022 Add credential sanitization for log messages in app/logging_conf.py
- [x] T023 Create app/utils.py with exponential backoff helper class

### Acceptance Tests for Milestone 2

- [x] T024 [P] Unit test: Valid configuration loads successfully in tests/unit/test_config.py
- [x] T025 [P] Unit test: Invalid configuration raises ValidationError with clear message in tests/unit/test_config.py
- [x] T026 [P] Unit test: Missing required fields are detected in tests/unit/test_config.py
- [x] T027 [P] Unit test: Default values are applied correctly in tests/unit/test_config.py
- [ ] T028 [P] Unit test: Log messages do not contain credentials in tests/unit/test_logging_conf.py
- [x] T029 [P] Unit test: Exponential backoff calculates delays correctly in tests/unit/test_utils.py
- [ ] T030 Test: Integration test - Configuration loads from mock Supervisor environment in tests/integration/test_config_integration.py

**Checkpoint**: Foundation ready - core business logic can now begin

---

## Phase 3: User Story 1 - Install and Configure (Priority: P1) 🎯 MVP

**Milestone**: Basic add-on lifecycle  
**Goal**: Add-on can be installed, configured, started, and shows running status  
**Independent Test**: Install add-on, enter credentials, start it, verify "Running" status and no errors in logs

**Maps to**: US1 (FR-001, FR-013, FR-015, FR-020)

### Implementation Tasks

- [x] T031 Create app/main.py with async main() entry point and signal handlers
- [x] T032 Add configuration loading in main() using app/config.py
- [x] T033 Add logging initialization in main() using app/logging_conf.py
- [x] T034 Add startup logging (version, configuration summary) in app/main.py
- [x] T035 Add graceful shutdown handler (SIGTERM, SIGINT) in app/main.py
- [x] T036 Add cleanup on shutdown (close connections, flush logs) in app/main.py
- [x] T037 Update run.sh to call python -m app.main with proper error handling

### Acceptance Tests for Milestone 3 (US1)

- [ ] T038 Test: Add-on starts successfully with valid configuration (verify exit code 0)
- [ ] T039 Test: Add-on logs startup message with version information
- [ ] T040 Test: Add-on handles SIGTERM gracefully and exits cleanly
- [ ] T041 Test: Invalid MELCloud credentials produce clear error message in logs
- [ ] T042 Test: Invalid MQTT settings produce clear error message in logs
- [ ] T043 Test: Add-on remains running (does not crash) when auth fails

**Checkpoint**: US1 complete - Add-on lifecycle working, ready for MELCloud integration

---

## Phase 4: MELCloud Integration (pymelcloudhome session + poller)

**Milestone**: pymelcloudhome session + poller  
**Purpose**: Authenticate with MELCloud, manage session, poll for device states

**Maps to**: US1 (authentication), US2 (device discovery)

### Implementation Tasks - Credentials Entity

- [x] T044 [P] Create app/models/**init**.py module initializer
- [x] T045 [P] Create app/models/credentials.py with Credentials dataclass per data-model.md
- [x] T046 [P] Add credential validation (email format) in app/models/credentials.py
- [x] T047 [P] Create app/models/climate_device.py with ClimateDevice dataclass per data-model.md
- [x] T048 [P] Add ClimateDevice.from_pymelcloud_device() classmethod in app/models/climate_device.py
- [x] T049 [P] Add ATW settings array parser methods (\_get_atw_setting, \_get_atw_bool, \_get_atw_float) in app/models/climate_device.py
- [x] T050 [P] Add device state accessor methods (get_power, get_temperature, get_target_temperature, get_tank_temperature) in app/models/climate_device.py
- [x] T051 [P] Add device error checking methods (is_in_error, get_error_code, has_zone_2) in app/models/climate_device.py

### Implementation Tasks - MELCloud Client

- [x] T052 Create app/melcloud_client.py with MelCloudClient wrapper class
- [x] T053 Add async authenticate() method using pymelcloudhome MelCloudHomeClient.login() in app/melcloud_client.py
- [x] T054 Add async list_devices() method using pymelcloudhome list_devices() in app/melcloud_client.py
- [x] T055 Add async get_device_state() method using pymelcloudhome get_device_state() in app/melcloud_client.py
- [x] T056 Add async set_device_state() method using pymelcloudhome set_device_state() in app/melcloud_client.py
- [x] T057 Add exception handling for pymelcloudhome errors (LoginError, ApiError, DeviceNotFound) in app/melcloud_client.py
- [x] T058 Add automatic re-authentication on 401 errors in app/melcloud_client.py
- [x] T059 Add MelCloudClient instance lifecycle management (keep alive, close on shutdown) in app/melcloud_client.py

### Implementation Tasks - Polling Loop

- [x] T060 Add polling loop in app/main.py with configurable interval (default 60s)
- [x] T061 Add device discovery on first poll cycle in app/main.py
- [x] T062 Add state polling for all devices in app/main.py
- [x] T063 Add state change detection (compare with previous state) in app/main.py
- [x] T064 Add exponential backoff on polling errors using app/utils.py
- [x] T065 Add logging for poll cycles (start, device count, errors, duration) in app/main.py

### Acceptance Tests for Milestone 4 (US1, US2)

- [ ] T066 [P] Unit test: Credentials validation accepts valid email in tests/unit/test_credentials.py
- [ ] T067 [P] Unit test: ClimateDevice parses ATA device state correctly in tests/unit/test_climate_device.py
- [ ] T068 [P] Unit test: ClimateDevice parses ATW device state with settings array in tests/unit/test_climate_device.py
- [ ] T069 [P] Unit test: ATW zone 2 detection works correctly in tests/unit/test_climate_device.py
- [ ] T070 Test: Integration test - MelCloudClient authenticates with mock credentials in tests/integration/test_melcloud_auth.py
- [ ] T071 Test: Integration test - MelCloudClient lists devices from mock API in tests/integration/test_device_discovery.py
- [ ] T072 Test: Integration test - MelCloudClient handles 401 with re-auth in tests/integration/test_session_recovery.py
- [ ] T073 Test: Integration test - Polling loop discovers devices within 60s in tests/integration/test_polling_loop.py
- [ ] T074 Test: Integration test - Polling loop detects state changes in tests/integration/test_state_detection.py
- [ ] T075 Test: Manual test - Live MELCloud account authentication (see quickstart.md for test procedure)

**Checkpoint**: US2 complete - Device discovery working, states being polled

---

## Phase 5: MQTT Integration (MQTT bridge & discovery)

**Milestone**: MQTT bridge & discovery  
**Purpose**: Connect to MQTT broker, publish device discovery messages, publish state updates

**Maps to**: US2 (device discovery), US3 (state monitoring)

### Implementation Tasks - MQTT Bridge

- [ ] T076 Create app/mqtt_bridge.py with MQTTBridge class using paho-mqtt
- [ ] T077 Add async connect() method with connection error handling in app/mqtt_bridge.py
- [ ] T078 Add async disconnect() method for graceful shutdown in app/mqtt_bridge.py
- [ ] T079 Add connection state tracking and auto-reconnect logic in app/mqtt_bridge.py
- [ ] T080 Add MQTT last will and testament configuration in app/mqtt_bridge.py

### Implementation Tasks - MQTT Discovery

- [ ] T081 Add publish_discovery() method for climate entities in app/mqtt_bridge.py
- [ ] T082 Add MQTT Discovery message formatting per contracts/mqtt-discovery-schema.json in app/mqtt_bridge.py
- [ ] T083 Add device metadata formatting (manufacturer, model, identifiers) in app/mqtt_bridge.py
- [ ] T084 Add climate entity configuration (modes, temperature ranges, topics) in app/mqtt_bridge.py
- [ ] T085 Add topic sanitization (remove special characters) in app/mqtt_bridge.py
- [ ] T086 Add base_topic configuration support in app/mqtt_bridge.py

### Implementation Tasks - State Publishing

- [ ] T087 Add publish_state() method for device state updates in app/mqtt_bridge.py
- [ ] T088 Add state payload formatting per contracts/mqtt-state-schema.json in app/mqtt_bridge.py
- [ ] T089 Add ClimateDevice.to_mqtt_state() implementation in app/models/climate_device.py
- [ ] T090 Add availability topic publishing (online/offline) in app/mqtt_bridge.py
- [ ] T091 Integrate MQTT publishing into polling loop in app/main.py
- [ ] T092 Add state publishing only on changes (not every poll) in app/main.py

### Acceptance Tests for Milestone 5 (US2, US3)

- [ ] T093 [P] Unit test: MQTT Discovery message matches schema in tests/unit/test_mqtt_bridge.py
- [ ] T094 [P] Unit test: State message matches schema in tests/unit/test_mqtt_bridge.py
- [ ] T095 [P] Unit test: Topic sanitization removes special characters in tests/unit/test_mqtt_bridge.py
- [ ] T096 [P] Unit test: ClimateDevice.to_mqtt_state() formats ATA device correctly in tests/unit/test_climate_device.py
- [ ] T097 [P] Unit test: ClimateDevice.to_mqtt_state() formats ATW device with zones in tests/unit/test_climate_device.py
- [ ] T098 Test: Integration test - MQTT connects to broker successfully in tests/integration/test_mqtt_connection.py
- [ ] T099 Test: Integration test - Discovery messages published for all devices in tests/integration/test_mqtt_discovery.py
- [ ] T100 Test: Integration test - State updates published on poll cycle in tests/integration/test_mqtt_state_publishing.py
- [ ] T101 Test: Integration test - Availability messages update on connection changes in tests/integration/test_availability_topics.py
- [ ] T102 Test: Manual test - Devices appear in Home Assistant MQTT integration (see quickstart.md Step 5)

**Checkpoint**: US2 and US3 (monitoring) complete - Devices discovered and states published to HA

---

## Phase 6: Command Handling (mode/setpoint)

**Milestone**: Command handling (mode/setpoint)  
**Purpose**: Subscribe to MQTT command topics, receive commands from HA, send to MELCloud API

**Maps to**: US3 (device control)

### Implementation Tasks - MQTT Command Subscription

- [ ] T103 Add subscribe_to_commands() method in app/mqtt_bridge.py
- [ ] T104 Add command topic pattern generation in app/mqtt_bridge.py
- [ ] T105 Add MQTT message callback handler in app/mqtt_bridge.py
- [ ] T106 Add command message parsing per contracts/mqtt-command-schema.json in app/mqtt_bridge.py
- [ ] T107 Add command validation (valid modes, temperature ranges) in app/mqtt_bridge.py

### Implementation Tasks - Command Execution

- [ ] T108 Create app/command_handler.py with CommandHandler class
- [ ] T109 Add handle_temperature_command() method in app/command_handler.py
- [ ] T110 Add handle_mode_command() method in app/command_handler.py
- [ ] T111 Add command-to-API mapping (HA modes → MELCloud operation modes) in app/command_handler.py
- [ ] T112 Add async command execution via MelCloudClient.set_device_state() in app/command_handler.py
- [ ] T113 Add command result logging (success/failure) in app/command_handler.py
- [ ] T114 Add immediate state refresh after command execution in app/command_handler.py
- [ ] T115 Integrate CommandHandler into app/main.py
- [ ] T116 Wire MQTT command callbacks to CommandHandler in app/main.py

### Acceptance Tests for Milestone 6 (US3)

- [ ] T117 [P] Unit test: Temperature command parses correctly in tests/unit/test_command_handler.py
- [ ] T118 [P] Unit test: Mode command parses correctly in tests/unit/test_command_handler.py
- [ ] T119 [P] Unit test: Invalid commands are rejected in tests/unit/test_command_handler.py
- [ ] T120 [P] Unit test: Command-to-API mapping is correct for all modes in tests/unit/test_command_handler.py
- [ ] T121 Test: Integration test - Temperature command sent to MELCloud API in tests/integration/test_temperature_commands.py
- [ ] T122 Test: Integration test - Mode command sent to MELCloud API in tests/integration/test_mode_commands.py
- [ ] T123 Test: Integration test - State refreshes immediately after command in tests/integration/test_command_state_refresh.py
- [ ] T124 Test: Manual test - Change temperature in HA climate card, verify device updates (see quickstart.md test scenario 1)
- [ ] T125 Test: Manual test - Change mode in HA, verify device responds (see quickstart.md test scenario 2)

**Checkpoint**: US3 complete - Bidirectional control working (HA ↔ MELCloud)

---

## Phase 7: Resilience (Error Recovery)

**Milestone**: Error recovery and resilience  
**Purpose**: Handle network failures, session expiration, rate limits, connection drops gracefully

**Maps to**: US4 (Resilient Operation with Error Recovery)

### Implementation Tasks - Network Resilience

- [ ] T126 Add network error detection and classification in app/melcloud_client.py
- [ ] T127 Add exponential backoff for failed API calls in app/melcloud_client.py
- [ ] T128 Add max retry limits (3 attempts) in app/melcloud_client.py
- [ ] T129 Add rate limit detection (HTTP 429) and backoff in app/melcloud_client.py
- [ ] T130 Add timeout configuration for API calls in app/melcloud_client.py

### Implementation Tasks - MQTT Resilience

- [ ] T131 Add MQTT reconnection logic with exponential backoff in app/mqtt_bridge.py
- [ ] T132 Add connection state monitoring in app/mqtt_bridge.py
- [ ] T133 Add republish of discovery messages on reconnection in app/mqtt_bridge.py
- [ ] T134 Add republish of availability messages on reconnection in app/mqtt_bridge.py
- [ ] T135 Add MQTT operation queuing during disconnection in app/mqtt_bridge.py

### Implementation Tasks - Session Management

- [ ] T136 Add session expiration detection (via pymelcloudhome 401 handling) in app/melcloud_client.py
- [ ] T137 Add automatic re-authentication flow in app/melcloud_client.py
- [ ] T138 Add authentication failure handling (max 3 attempts, then log error) in app/melcloud_client.py
- [ ] T139 Add last known state preservation during outages in app/main.py

### Implementation Tasks - Memory Management

- [ ] T140 Add memory usage monitoring in app/main.py
- [ ] T141 Add periodic connection refresh (every 24h) in app/main.py
- [ ] T142 Add garbage collection hints for large objects in app/main.py

### Acceptance Tests for Milestone 7 (US4)

- [ ] T143 Test: Integration test - Network disconnection triggers exponential backoff in tests/integration/test_network_resilience.py
- [ ] T144 Test: Integration test - MQTT broker restart triggers reconnection in tests/integration/test_mqtt_resilience.py
- [ ] T145 Test: Integration test - Session expiration triggers re-authentication in tests/integration/test_session_recovery.py
- [ ] T146 Test: Integration test - Rate limit extends polling interval in tests/integration/test_rate_limiting.py
- [ ] T147 Test: Integration test - Add-on maintains <200MB memory after 1000 poll cycles in tests/integration/test_memory_stability.py
- [ ] T148 Test: Stress test - Add-on runs for 7 days without restart (manual test on dev instance)

**Checkpoint**: US4 complete - Add-on handles failures gracefully

---

## Phase 8: Observability (Healthcheck & Monitoring)

**Milestone**: Healthcheck & graceful shutdown  
**Purpose**: Provide health endpoint, diagnostic logging, and proper shutdown handling

**Maps to**: US5 (Health Monitoring and Diagnostics)

### Implementation Tasks - Health Endpoint

- [ ] T149 Create app/health_server.py with aiohttp health server
- [ ] T150 Add /healthz endpoint handler in app/health_server.py
- [ ] T151 Add health status JSON response per spec (MELCloud status, MQTT status, last poll time, device count) in app/health_server.py
- [ ] T152 Add HTTP 200 for healthy, 503 for unhealthy in app/health_server.py
- [ ] T153 Add health checks (MELCloud authenticated, MQTT connected, recent successful poll) in app/health_server.py
- [ ] T154 Start health server on port 8099 in app/main.py

### Implementation Tasks - Diagnostic Logging

- [ ] T155 Add detailed DEBUG logging for API requests in app/melcloud_client.py
- [ ] T156 Add detailed DEBUG logging for MQTT operations in app/mqtt_bridge.py
- [ ] T157 Add structured logging fields (device_id, operation, duration) in app/melcloud_client.py and app/mqtt_bridge.py
- [ ] T158 Add error context in log messages (suggested resolution steps) in app/melcloud_client.py and app/mqtt_bridge.py
- [ ] T159 Add startup banner with configuration summary in app/main.py

### Implementation Tasks - Graceful Shutdown

- [ ] T160 Add shutdown timeout (30 seconds max) in app/main.py
- [ ] T161 Add connection cleanup on shutdown (MQTT, MELCloud, health server) in app/main.py
- [ ] T162 Add log flush on shutdown in app/main.py
- [ ] T163 Add final status log message on shutdown in app/main.py

### Acceptance Tests for Milestone 8 (US5)

- [ ] T164 [P] Unit test: Health endpoint returns 200 when healthy in tests/unit/test_health_server.py
- [ ] T165 [P] Unit test: Health endpoint returns 503 when MELCloud disconnected in tests/unit/test_health_server.py
- [ ] T166 [P] Unit test: Health JSON includes all required fields in tests/unit/test_health_server.py
- [ ] T167 Test: Integration test - Health endpoint accessible via HTTP GET in tests/integration/test_health_endpoint.py
- [ ] T168 Test: Integration test - DEBUG log level shows detailed information in tests/integration/test_debug_logging.py
- [ ] T169 Test: Integration test - Shutdown completes within 30 seconds in tests/integration/test_graceful_shutdown.py
- [ ] T170 Test: Manual test - Health endpoint returns accurate status (see quickstart.md diagnostics section)

**Checkpoint**: US5 complete - Full observability and health monitoring

---

## Phase 9: Documentation & Polish (README and examples)

**Milestone**: README and examples  
**Purpose**: User documentation, example configurations, troubleshooting guide, release preparation

**Maps to**: All user stories (documentation)

### Implementation Tasks - User Documentation

- [ ] T171 [P] Create README.md with project description and features
- [ ] T172 [P] Add prerequisites section to README.md
- [ ] T173 [P] Add installation instructions to README.md (link to quickstart.md)
- [ ] T174 [P] Add configuration reference to README.md (all options with descriptions)
- [ ] T175 [P] Add troubleshooting section to README.md (common errors and solutions)
- [ ] T176 [P] Add FAQ section to README.md
- [ ] T177 [P] Create CHANGELOG.md with initial release notes (v1.0.0)

### Implementation Tasks - Example Configurations

- [ ] T178 [P] Create examples/basic-config.yaml with minimal configuration
- [ ] T179 [P] Create examples/advanced-config.yaml with all options
- [ ] T180 [P] Create examples/docker-compose.yaml for local testing
- [ ] T181 [P] Add architecture diagram to docs/ (startup flow, data flow)

### Implementation Tasks - Test Fixtures

- [ ] T182 [P] Create tests/fixtures/mock_melcloud_devices.json with sample device data
- [ ] T183 [P] Create tests/fixtures/mock_config.yaml with test configuration
- [ ] T184 [P] Create tests/conftest.py with pytest fixtures for mocks

### Implementation Tasks - CI/CD

- [ ] T185 [P] Create .github/workflows/test.yaml with pytest runner
- [ ] T186 [P] Create .github/workflows/build.yaml with multi-arch Docker builds
- [ ] T187 [P] Add linting to CI (ruff check .)
- [ ] T188 [P] Add coverage reporting to CI

### Acceptance Tests for Milestone 9

- [ ] T189 Test: Verify README.md has all required sections
- [ ] T190 Test: Verify quickstart.md instructions work end-to-end (manual walkthrough)
- [ ] T191 Test: Verify example configurations are valid YAML
- [ ] T192 Test: Verify all tests pass in CI pipeline
- [ ] T193 Test: Verify multi-arch builds succeed in CI pipeline
- [ ] T194 Test: Run complete validation per quickstart.md (install → configure → devices discovered → control works)

**Checkpoint**: All documentation complete, ready for release

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Container & Dependencies)
    ↓
Phase 2 (Config & Logging) ← FOUNDATIONAL BLOCKER
    ↓
Phase 3 (US1 - Install/Configure) ← MVP START
    ↓
Phase 4 (MELCloud Integration)
    ↓
Phase 5 (MQTT Bridge & Discovery)
    ↓
Phase 6 (Command Handling)
    ↓
Phase 7 (Resilience)
    ↓
Phase 8 (Observability)
    ↓
Phase 9 (Documentation & Polish)
```

### Critical Path

1. **Phase 1 → Phase 2**: Container and foundational infrastructure MUST complete first
2. **Phase 2 → Phase 3**: Configuration/logging BLOCKS all user story work
3. **Phase 3 → Phase 4 → Phase 5 → Phase 6**: Sequential dependency (lifecycle → auth → discovery → control)
4. **Phase 7, Phase 8**: Can partially overlap with Phase 6
5. **Phase 9**: Can proceed once core functionality complete (Phase 6)

### Parallel Opportunities by Milestone

**Milestone 1 (Container)**:

- T003, T004, T006, T007 can run in parallel (different files)
- T009, T010, T011 can run in parallel (different architectures)

**Milestone 2 (Config & Logging)**:

- T024-T029 unit tests can run in parallel

**Milestone 4 (MELCloud)**:

- T044-T051 model tasks can run in parallel (different entities)
- T066-T069 unit tests can run in parallel

**Milestone 5 (MQTT)**:

- T093-T097 unit tests can run in parallel
- T098-T102 integration tests can run sequentially (require MQTT broker)

**Milestone 6 (Commands)**:

- T117-T120 unit tests can run in parallel

**Milestone 9 (Documentation)**:

- T171-T181 documentation tasks can run in parallel (different files)
- T185-T188 CI tasks can run in parallel

### MVP Scope (Recommended)

**Minimum Viable Product** = Phases 1-6

- Phase 1: Container infrastructure
- Phase 2: Config & logging (foundational)
- Phase 3: Add-on lifecycle (US1)
- Phase 4: MELCloud integration (US1, US2 - auth & discovery)
- Phase 5: MQTT publishing (US2, US3 - monitoring)
- Phase 6: Command handling (US3 - control)

This delivers core value: Users can install add-on, discover devices, monitor states, and control devices.

**Post-MVP** = Phases 7-9

- Phase 7: Resilience (US4 - production reliability)
- Phase 8: Observability (US5 - health monitoring)
- Phase 9: Documentation polish

---

## Parallel Example: Milestone 4 (MELCloud Integration)

```bash
# Developer 1: Model layer
git checkout -b feature/models
# Work on T044-T051 (all [P] marked)
pytest tests/unit/test_climate_device.py  # T067-T069

# Developer 2: MELCloud client
git checkout -b feature/melcloud-client
# Work on T052-T059 (sequential, depend on T044-T051)
pytest tests/integration/test_melcloud_auth.py  # T070

# Developer 3: Polling loop (after T052-T059)
git checkout -b feature/polling
# Work on T060-T065
pytest tests/integration/test_polling_loop.py  # T073-T074
```

---

## Implementation Strategy

### MVP-First Approach

1. **Week 1**: Complete Phases 1-2 (Container + Foundation)
2. **Week 2**: Complete Phases 3-4 (Lifecycle + MELCloud)
3. **Week 3**: Complete Phases 5-6 (MQTT + Commands) ← MVP COMPLETE
4. **Week 4**: Complete Phases 7-8 (Resilience + Observability)
5. **Week 5**: Complete Phase 9 (Documentation)

### Incremental Delivery

Each milestone delivers testable value:

- **Milestone 1**: Container builds and runs
- **Milestone 2**: Add-on starts and loads config
- **Milestone 3**: Add-on shows "Running" status in HA
- **Milestone 4**: Add-on authenticates and polls MELCloud
- **Milestone 5**: Devices appear in Home Assistant
- **Milestone 6**: Users can control devices from HA ← MVP
- **Milestone 7**: Add-on survives network failures
- **Milestone 8**: Health monitoring available
- **Milestone 9**: Documentation complete for public release

### Testing Strategy

- **Unit tests**: Run after each implementation task (fast feedback)
- **Integration tests**: Run after milestone complete (verify integration points)
- **Manual tests**: Run for end-to-end validation (see quickstart.md)
- **Acceptance tests**: Run at milestone boundaries (verify milestone goals met)

---

## Task Count Summary

- **Phase 1**: 14 tasks (8 implementation + 6 tests)
- **Phase 2**: 16 tasks (9 implementation + 7 tests)
- **Phase 3**: 13 tasks (7 implementation + 6 tests)
- **Phase 4**: 32 tasks (22 implementation + 10 tests)
- **Phase 5**: 27 tasks (17 implementation + 10 tests)
- **Phase 6**: 23 tasks (14 implementation + 9 tests)
- **Phase 7**: 23 tasks (17 implementation + 6 tests)
- **Phase 8**: 22 tasks (15 implementation + 7 tests)
- **Phase 9**: 24 tasks (18 implementation + 6 tests)

**Total**: 194 tasks (127 implementation + 67 tests)

**Parallel opportunities**: 45 tasks marked [P] (23% can run in parallel)

**MVP scope**: Phases 1-6 = 125 tasks (65% of total)

---

## Success Criteria Validation

Each milestone maps to success criteria from spec.md:

- **Milestone 3 → SC-001**: Installation and configuration < 5 minutes
- **Milestone 4 → SC-002**: Device discovery < 60 seconds
- **Milestone 6 → SC-003**: Control commands < 15 seconds
- **Milestone 7 → SC-004**: 7-day uptime, <200MB memory
- **Milestone 7 → SC-005**: Network recovery < 5 minutes
- **Milestone 5 → SC-006**: Works with core-mosquitto defaults
- **Milestone 8 → SC-007**: Health endpoint < 1 second response
- **Milestone 9 → SC-008**: 95% of issues self-diagnosable via logs
- **Milestone 1 → SC-009**: Multi-arch builds (amd64, aarch64, armv7)
- **Milestone 3 → SC-010**: Config changes without losing device state

All 10 success criteria covered by milestone acceptance tests.
