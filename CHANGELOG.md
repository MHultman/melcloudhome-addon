# Changelog

All notable changes to MELCloud Home Bridge will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
