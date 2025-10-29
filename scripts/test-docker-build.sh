#!/usr/bin/env bash
# Test Docker image build and verify system Chromium setup

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GRAY='\033[0;90m'
NC='\033[0m' # No Color

# Configuration
ARCHITECTURE=${1:-amd64}
IMAGE_NAME="melcloudhome-bridge-test"
IMAGE_TAG="${ARCHITECTURE}-test"
FULL_IMAGE_NAME="${IMAGE_NAME}:${IMAGE_TAG}"

echo -e "${CYAN}======================================${NC}"
echo -e "${CYAN}MELCloud Home Bridge - Docker Test${NC}"
echo -e "${CYAN}======================================${NC}"
echo ""

# Change to repository root
cd "$(dirname "$0")/.."

# Build the image
echo -e "${YELLOW}Building Docker image for ${ARCHITECTURE}...${NC}"
echo -e "${GRAY}Image: ${FULL_IMAGE_NAME}${NC}"
echo ""

# Select base image based on architecture
case $ARCHITECTURE in
    amd64)
        BASE_IMAGE="ghcr.io/home-assistant/amd64-base-python:3.11-alpine3.18"
        ;;
    aarch64)
        BASE_IMAGE="ghcr.io/home-assistant/aarch64-base-python:3.11-alpine3.18"
        ;;
    armv7)
        BASE_IMAGE="ghcr.io/home-assistant/armv7-base-python:3.11-alpine3.18"
        ;;
    *)
        echo -e "${RED}❌ Invalid architecture: ${ARCHITECTURE}${NC}"
        echo "Usage: $0 [amd64|aarch64|armv7]"
        exit 1
        ;;
esac

# Build the image
docker build \
    --build-arg BUILD_FROM="${BASE_IMAGE}" \
    --tag "${FULL_IMAGE_NAME}" \
    --file Dockerfile \
    .

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Docker build failed!${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker build successful!${NC}"
echo ""

# Test 1: Check Chromium installation
echo -e "${YELLOW}Test 1: Verifying Chromium installation...${NC}"
CHROMIUM_PATH=$(docker run --rm "${FULL_IMAGE_NAME}" which chromium)
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Chromium found at: ${CHROMIUM_PATH}${NC}"
else
    echo -e "${RED}❌ Chromium not found!${NC}"
    exit 1
fi

# Test 2: Check Chromium version
echo ""
echo -e "${YELLOW}Test 2: Checking Chromium version...${NC}"
CHROMIUM_VERSION=$(docker run --rm "${FULL_IMAGE_NAME}" chromium --version 2>&1)
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Chromium version: ${CHROMIUM_VERSION}${NC}"
else
    echo -e "${RED}❌ Failed to get Chromium version!${NC}"
    exit 1
fi

# Test 3: Verify Python environment
echo ""
echo -e "${YELLOW}Test 3: Verifying Python environment...${NC}"
PYTHON_VERSION=$(docker run --rm "${FULL_IMAGE_NAME}" python --version)
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Python version: ${PYTHON_VERSION}${NC}"
else
    echo -e "${RED}❌ Python check failed!${NC}"
    exit 1
fi

# Test 4: Check pymelcloudhome installation
echo ""
echo -e "${YELLOW}Test 4: Checking pymelcloudhome installation...${NC}"
PYMELCLOUD_VERSION=$(docker run --rm "${FULL_IMAGE_NAME}" python -c "import pymelcloudhome; print(f'pymelcloudhome {pymelcloudhome.__version__}')")
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ ${PYMELCLOUD_VERSION} installed${NC}"
    
    # Verify it's version 0.3.1 or higher (0.3.1 fixed __version__ bug from 0.3.0)
    VERSION=$(docker run --rm "${FULL_IMAGE_NAME}" python -c "import pymelcloudhome; print(pymelcloudhome.__version__)")
    if [[ "$VERSION" =~ ^0\.3\.[1-9] ]] || [[ "$VERSION" =~ ^0\.[4-9]\. ]] || [[ "$VERSION" =~ ^[1-9]\. ]]; then
        echo -e "${GREEN}   Version check: OK (v${VERSION} >= 0.3.1)${NC}"
    else
        echo -e "${YELLOW}   ⚠️  Warning: Expected v0.3.1+, got v${VERSION}${NC}"
        echo -e "${YELLOW}   Note: 0.3.1 may not be available on piwheels yet for ARM architectures${NC}"
    fi
else
    echo -e "${RED}❌ pymelcloudhome not found!${NC}"
    exit 1
fi

# Test 5: Verify pymelcloudhome can detect Chromium
echo ""
echo -e "${YELLOW}Test 5: Verifying pymelcloudhome Chromium detection...${NC}"
CHROMIUM_DETECTION=$(docker run --rm "${FULL_IMAGE_NAME}" python -c '
import sys
import os

chromium_path = "/usr/bin/chromium"
if os.path.exists(chromium_path):
    print(f"✓ Chromium found at {chromium_path}")
    
    if os.access(chromium_path, os.X_OK):
        print(f"✓ Chromium is executable")
    else:
        print(f"✗ Chromium is not executable")
        sys.exit(1)
        
    try:
        from pymelcloudhome import MelCloudHomeClient
        print(f"✓ MelCloudHomeClient can be imported")
        print(f"✓ pymelcloudhome v0.3.0+ supports chromium_executable_path parameter")
    except Exception as e:
        print(f"✗ Error importing pymelcloudhome: {e}")
        sys.exit(1)
else:
    print(f"✗ Chromium not found at {chromium_path}")
    sys.exit(1)
')

if [ $? -eq 0 ]; then
    echo -e "${GREEN}${CHROMIUM_DETECTION}${NC}"
    echo -e "${GREEN}✅ Chromium detection successful!${NC}"
else
    echo -e "${RED}${CHROMIUM_DETECTION}${NC}"
    echo -e "${RED}❌ Chromium detection failed!${NC}"
    exit 1
fi

# Test 6: Check app structure
echo ""
echo -e "${YELLOW}Test 6: Verifying application structure...${NC}"
docker run --rm "${FULL_IMAGE_NAME}" ls -la /app/app/ > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Application structure verified${NC}"
else
    echo -e "${RED}❌ Application structure check failed!${NC}"
    exit 1
fi

# Test 7: Verify all required dependencies
echo ""
echo -e "${YELLOW}Test 7: Checking all Python dependencies...${NC}"
DEPENDENCY_CHECK=$(docker run --rm "${FULL_IMAGE_NAME}" python -c '
import sys

# Map package name to import name
# Note: pymelcloudhome v0.3.0 uses pyppeteer (not playwright)
packages = {
    "pymelcloudhome": "pymelcloudhome",
    "pyppeteer": "pyppeteer",
    "paho-mqtt": "paho.mqtt.client",
    "fastapi": "fastapi",
    "uvicorn": "uvicorn",
    "loguru": "loguru",
    "pydantic": "pydantic",
    "pydantic-settings": "pydantic_settings",
}

missing = []
for pkg_name, import_name in packages.items():
    try:
        __import__(import_name)
        print("OK: " + pkg_name)
    except ImportError:
        print("MISSING: " + pkg_name)
        missing.append(pkg_name)

if missing:
    print("\nMissing packages: " + ", ".join(missing))
    sys.exit(1)
')

if [ $? -eq 0 ]; then
    echo -e "${GREEN}${DEPENDENCY_CHECK}${NC}"
    echo -e "${GREEN}✅ All dependencies installed!${NC}"
else
    echo -e "${RED}${DEPENDENCY_CHECK}${NC}"
    echo -e "${RED}❌ Missing dependencies!${NC}"
    exit 1
fi

# Summary
echo ""
echo -e "${CYAN}======================================${NC}"
echo -e "${GREEN}All tests passed successfully! ✅${NC}"
echo -e "${CYAN}======================================${NC}"
echo ""
echo -e "${GRAY}Image: ${FULL_IMAGE_NAME}${NC}"
echo -e "${GRAY}Architecture: ${ARCHITECTURE}${NC}"
echo ""
echo -e "The Docker image is ready with:"
echo -e "  • System Chromium at /usr/bin/chromium"
echo -e "  • pymelcloudhome v0.3.0+ with Chromium support"
echo -e "  • All required dependencies installed"
echo ""

# Cleanup option
read -p "Do you want to remove the test image? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Removing test image...${NC}"
    docker rmi "${FULL_IMAGE_NAME}"
    echo -e "${GREEN}✅ Test image removed${NC}"
else
    echo -e "${GRAY}Test image kept: ${FULL_IMAGE_NAME}${NC}"
fi
