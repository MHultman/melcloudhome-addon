# Docker Build Testing

This directory contains scripts for testing the Docker image build and verification.

## Test Scripts

### PowerShell (Windows)

```powershell
.\scripts\test-docker-build.ps1 -Architecture amd64
```

### Bash (Linux/Mac)

```bash
chmod +x scripts/test-docker-build.sh
./scripts/test-docker-build.sh amd64
```

## What the Tests Verify

1. ✅ **Docker Build**: Image builds successfully for the target architecture
2. ✅ **Chromium Installation**: System Chromium is installed at `/usr/bin/chromium`
3. ✅ **Chromium Version**: Chromium can be executed and version is reported
4. ✅ **Python Environment**: Python 3.11 is available
5. ✅ **pymelcloudhome**: Package is installed correctly
6. ✅ **Chromium Detection**: pymelcloudhome can detect and use system Chromium
7. ✅ **App Structure**: Application files are correctly copied
8. ✅ **Dependencies**: All required Python packages are installed

## Supported Architectures

- `amd64` - Intel/AMD 64-bit (default)
- `aarch64` - ARM 64-bit (Raspberry Pi 4, etc.)
- `armv7` - ARM 32-bit (Raspberry Pi 3, etc.)

## Example Output

```
======================================
MELCloud Home Bridge - Docker Test
======================================

Building Docker image for amd64...
✅ Docker build successful!

Test 1: Verifying Chromium installation...
✅ Chromium found at: /usr/bin/chromium

Test 2: Checking Chromium version...
✅ Chromium version: Chromium 119.0.6045.159 Alpine Linux

Test 3: Verifying Python environment...
✅ Python version: Python 3.11.9

Test 4: Checking pymelcloudhome installation...
✅ pymelcloudhome 0.3.1 installed
   Version check: OK (v0.3.1 >= 0.3.1)

Test 5: Verifying pymelcloudhome Chromium detection...
✅ Chromium detection successful!

Test 6: Verifying application structure...
✅ Application structure verified

Test 7: Checking all Python dependencies...
✅ All dependencies installed!

======================================
All tests passed successfully! ✅
======================================
```

## Important Notes

### pymelcloudhome Version

The code requires **pymelcloudhome v0.3.0**, which:

- Introduces the `chromium_executable_path` parameter for ARM64/Raspberry Pi support
- Switches from Playwright to Pyppeteer (Puppeteer for Python) for browser automation
- Adds native system Chromium support

**Availability**:

- ✅ **PyPI**: v0.3.0 is available at https://pypi.org/project/pymelcloudhome/
- ⏳ **piwheels**: May be pending build at https://www.piwheels.org/project/pymelcloudhome/
  - AMD64 builds use PyPI directly
  - ARM builds (aarch64, armv7) will use piwheels when available, or build from source

**Forward Compatibility**: The `chromium_executable_path` parameter with `# type: ignore[call-arg]` comment ensures compatibility.

### Testing

The Docker test scripts verify:

- pymelcloudhome 0.3.1 is installed
- All dependencies (including pyppeteer) are present
- System Chromium is correctly configured
- The application structure is valid

If testing on ARM architecture and piwheels doesn't have 0.3.0 yet, the build will compile from source (slower but functional).

## Cleanup

After testing, you can remove the test image:

```powershell
docker rmi melcloudhome-bridge-test:amd64-test
```

Or the script will prompt you at the end.
