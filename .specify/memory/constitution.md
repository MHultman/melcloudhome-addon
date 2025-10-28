<!--
SYNC IMPACT REPORT - Constitution v1.0.0
========================================
Version Change: INITIAL → 1.0.0 (Initial constitution ratification)

Principles Created:
  - I. Code Clarity First
  - II. Simple Logging
  - III. Minimal Configuration
  - IV. Containerized Browser Automation
  - V. Home Assistant Add-on Conventions
  - VI. Test-Driven Development
  - VII. Step-by-Step Documentation

Sections Added:
  - Core Principles (7 principles)
  - Technical Constraints
  - Development Workflow
  - Governance

Templates Requiring Updates:
  ✅ plan-template.md - Constitution Check section aligns with principles
  ✅ spec-template.md - Requirements and user stories support testability principle
  ✅ tasks-template.md - Task structure supports incremental testing and clear deliverables

Follow-up TODOs:
  - None - all placeholders filled

Next Actions:
  - Review and approve constitution
  - Begin feature specification using established principles
  - Ensure all future work validates against these principles
-->

# MELCloudHome Add-on Constitution

## Core Principles

### I. Code Clarity First

Code MUST be written for human understanding before machine execution. Every module, class, and
function MUST have a single, clearly stated purpose. Complex logic MUST be broken into named,
self-documenting functions. Variable and function names MUST describe intent without requiring
comments. Avoid clever one-liners; prefer explicit, multi-step implementations.

**Rationale**: This add-on integrates multiple complex systems (Playwright, MELCloud API, MQTT,
Home Assistant). Clear code reduces maintenance burden and makes debugging tractable when issues
arise in production environments where users have limited troubleshooting capabilities.

### II. Simple Logging

Logging MUST use Python's standard `logging` module with clearly defined levels: DEBUG for
development traces, INFO for operational milestones (startup, device discovery, state changes),
WARNING for recoverable issues, ERROR for failures requiring attention. Log messages MUST be
human-readable with sufficient context. MUST NOT log sensitive data (passwords, tokens).
Structured logging (JSON format) is OPTIONAL but encouraged for log aggregation.

**Rationale**: Add-on users rely on Home Assistant's log viewer for troubleshooting. Clear,
leveled logging enables users to diagnose issues without deep technical knowledge while
providing developers with actionable debugging information.

### III. Minimal Configuration

Configuration options MUST be kept to the absolute minimum required for functionality. Default
values MUST work for 80% of users out-of-the-box. Required settings are: MELCloud email,
MELCloud password, MQTT broker connection details. All other behaviors (polling intervals,
device naming patterns, MQTT topics) MUST have sensible defaults. Configuration schema MUST be
validated on startup with clear error messages.

**Rationale**: Home Assistant add-ons succeed through simplicity. Users installing this add-on
want MELCloud devices in Home Assistant with minimal friction. Complex configuration increases
support burden and installation failures.

### IV. Containerized Browser Automation

Playwright MUST run entirely within the Docker container with all required dependencies
(browser binaries, system libraries) pre-installed during image build. MUST NOT require users
to install browsers on the host system. Browser automation MUST be headless by default.
Container MUST include error handling for browser crashes with automatic restart capability.
Screenshot capture MUST be available for debugging authentication failures.

**Rationale**: Browser automation is notoriously fragile across different host environments.
Containerization ensures consistent behavior regardless of user's host OS or Home Assistant
installation type (HAOS, Container, Supervised, Core).

### V. Home Assistant Add-on Conventions

Add-on MUST follow Home Assistant Supervisor add-on architecture: configuration via
`config.json` schema, environment variables for runtime settings, `/data` directory for
persistent state, health check endpoint for Supervisor monitoring. Discovery MUST use Home
Assistant's MQTT Discovery protocol with proper device, entity, and availability topics.
Entities MUST include device_class, unit_of_measurement, and state_class attributes where
applicable. Add-on MUST support Ingress for any web UI components.

**Rationale**: Adhering to Home Assistant conventions ensures seamless integration with the
ecosystem, automatic UI generation, proper lifecycle management by Supervisor, and familiar
user experience consistent with other add-ons.

### VI. Test-Driven Development

Automated tests MUST exist for: MELCloud authentication flow, device discovery logic, MQTT
message formatting, configuration validation, error handling paths. Integration tests MUST
validate the complete flow from MELCloud API to MQTT Discovery. Tests MUST be runnable in CI
without requiring actual MELCloud credentials (use mocking). Manual test procedures MUST be
documented for scenarios requiring live MELCloud accounts.

**Rationale**: The add-on bridges three external systems (MELCloud, Playwright, MQTT) with
complex interactions. Automated testing prevents regressions and provides confidence during
refactoring. Manual test documentation ensures maintainers can validate against real MELCloud
infrastructure.

### VII. Step-by-Step Documentation

Documentation MUST include: Prerequisites (Home Assistant requirements, MQTT broker setup),
Installation steps with screenshots, Configuration guide with example values, Troubleshooting
section addressing common issues (authentication failures, MQTT connection errors, missing
devices), FAQ covering expected behaviors. Each major feature (add-on install, first device
discovery, MQTT integration) MUST have a quickstart guide accomplishing the goal in <5 steps.

**Rationale**: Users range from Home Assistant experts to newcomers. Clear documentation
reduces support requests, improves adoption rates, and enables community contributions by
lowering the knowledge barrier.

## Technical Constraints

- **Language**: Python 3.11+ (matches Home Assistant's current Python version)
- **Key Dependencies**: `playwright`, `paho-mqtt` (MQTT client), `aiohttp` (async HTTP)
- **Container Base**: Home Assistant's official Python base images with Playwright system deps
- **Persistent Storage**: `/data` directory for caching session tokens, device state
- **Network**: MUST handle transient network failures gracefully with exponential backoff
- **Performance**: Device state updates MUST complete within 30 seconds per polling cycle
- **Security**: Credentials MUST be stored in Home Assistant's secrets management, never in logs

## Development Workflow

- **Branch Strategy**: Feature branches from `main`, PR required for all changes
- **Code Review**: All PRs MUST pass automated tests, linting (pylint/flake8), and peer review
- **Testing Gate**: New features MUST include tests; PRs reducing test coverage are blocked
- **Documentation Gate**: User-facing changes MUST update relevant documentation sections
- **Release Process**: Semantic versioning (MAJOR.MINOR.PATCH), changelog required for releases
- **CI/CD**: GitHub Actions MUST run tests, build container images, validate add-on config schema

## Governance

This constitution supersedes all other development practices. Principles are binding; violations
require explicit justification and approval in PR discussions. Amendments to this constitution
require: (1) documented rationale, (2) migration plan for affected code, (3) approval from
maintainers. Complexity that conflicts with principles MUST be justified with technical
necessity and alternative approaches must be documented as considered and rejected.

All code reviews MUST verify compliance with these principles. When principles conflict in a
specific situation, prioritize in this order: Testability → Simplicity → Clarity → Conventions.

**Version**: 1.0.0 | **Ratified**: 2025-10-28 | **Last Amended**: 2025-10-28
