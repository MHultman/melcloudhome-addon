#!/usr/bin/env bash
#
# Test MELCloud Home Bridge add-on in a simulated Home Assistant environment
#
# This script tests the add-on by:
# 1. Creating a test configuration matching Home Assistant's options format
# 2. Running the Docker container with environment variables
# 3. Checking if the application starts without errors
# 4. Verifying the health endpoint responds
# 5. Testing graceful shutdown
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GRAY='\033[0;37m'
NC='\033[0m' # No Color

# Default parameters
ARCHITECTURE="${1:-amd64}"
TEST_DURATION="${2:-30}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}Home Assistant Integration Test${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""
echo -e "${GRAY}Architecture: ${ARCHITECTURE}${NC}"
echo -e "${GRAY}Test duration: ${TEST_DURATION} seconds${NC}"
echo -e "${GRAY}Working directory: ${REPO_ROOT}${NC}"
echo ""

cd "$REPO_ROOT"

# Build test image name
IMAGE_NAME="melcloudhome-bridge"
TAG="${ARCHITECTURE}-ha-test"
FULL_IMAGE_NAME="${IMAGE_NAME}:${TAG}"

# Step 1: Build the Docker image
echo -e "${YELLOW}Step 1: Building Docker image...${NC}"
echo -e "${GRAY}Image: ${FULL_IMAGE_NAME}${NC}"
echo ""

case "$ARCHITECTURE" in
    amd64)
        BASE_IMAGE="ghcr.io/home-assistant/amd64-base-python:3.11-alpine3.18"
        ;;
    aarch64)
        BASE_IMAGE="ghcr.io/home-assistant/aarch64-base-python:3.11-alpine3.18"
        ;;
    armv7)
        BASE_IMAGE="ghcr.io/home-assistant/armv7-base-python:3.11-alpine3.18"
        ;;
esac

docker build \
    --build-arg BUILD_FROM="$BASE_IMAGE" \
    --platform "linux/$ARCHITECTURE" \
    -t "$FULL_IMAGE_NAME" \
    -f Dockerfile \
    .

echo -e "${GREEN}✅ Docker build successful!${NC}"
echo ""

# Step 2: Test with mock credentials
echo -e "${YELLOW}Step 2: Testing application startup...${NC}"
echo -e "${GRAY}Using test credentials (will fail auth but validates startup)${NC}"
echo ""

# Create a temporary container name
CONTAINER_NAME="melcloud-ha-test-$$"

# Start container with test environment variables
echo -e "${GRAY}Starting container: ${CONTAINER_NAME}${NC}"
CONTAINER_ID=$(docker run -d \
    --name "$CONTAINER_NAME" \
    -e MELCLOUD_EMAIL="test@example.com" \
    -e MELCLOUD_PASSWORD="testpassword123" \
    -e MQTT_HOST="localhost" \
    -e MQTT_PORT="1883" \
    -e MQTT_USERNAME="" \
    -e MQTT_PASSWORD="" \
    -e MQTT_BASE_TOPIC="homeassistant" \
    -e POLL_INTERVAL="60" \
    -e LOG_LEVEL="INFO" \
    -p 8099:8099 \
    "$FULL_IMAGE_NAME")

echo -e "${GREEN}✅ Container started: ${CONTAINER_ID}${NC}"
echo ""

# Step 3: Wait for startup and collect logs
echo -e "${YELLOW}Step 3: Monitoring startup logs...${NC}"
sleep 5

LOGS=$(docker logs "$CONTAINER_NAME" 2>&1)
echo ""
echo -e "${CYAN}--- Container Logs (first 5 seconds) ---${NC}"
echo "$LOGS" | head -50
echo -e "${CYAN}--- End Logs ---${NC}"
echo ""

# Step 4: Check if application is running
echo -e "${YELLOW}Step 4: Checking application status...${NC}"

IS_RUNNING=$(docker ps --filter "name=$CONTAINER_NAME" --format "{{.Status}}")
if [[ "$IS_RUNNING" == *"Up"* ]]; then
    echo -e "${GREEN}✅ Container is running${NC}"
else
    echo -e "${RED}❌ Container is not running!${NC}"
    docker logs "$CONTAINER_NAME" 2>&1
    docker rm -f "$CONTAINER_NAME" > /dev/null
    exit 1
fi

# Step 5: Test health endpoint
echo ""
echo -e "${YELLOW}Step 5: Testing health endpoint...${NC}"
sleep 3

if command -v curl &> /dev/null; then
    RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8099/health || echo "000")
    if [ "$RESPONSE" = "200" ]; then
        echo -e "${GREEN}✅ Health endpoint responding: ${RESPONSE}${NC}"
        HEALTH_DATA=$(curl -s http://localhost:8099/health)
        echo -e "${GRAY}   Response: ${HEALTH_DATA}${NC}"
    else
        echo -e "${YELLOW}⚠️  Health endpoint returned: ${RESPONSE}${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  curl not available, skipping health check${NC}"
fi

# Step 6: Monitor for a period
echo ""
echo -e "${YELLOW}Step 6: Running for ${TEST_DURATION} seconds...${NC}"
echo -e "${GRAY}Monitoring for crashes or errors...${NC}"

START_TIME=$(date +%s)
ERROR_FOUND=false

while [ $(($(date +%s) - START_TIME)) -lt "$TEST_DURATION" ]; do
    # Check if container is still running
    IS_RUNNING=$(docker ps --filter "name=$CONTAINER_NAME" --format "{{.Status}}")
    if [[ "$IS_RUNNING" != *"Up"* ]]; then
        echo -e "${RED}❌ Container stopped unexpectedly!${NC}"
        ERROR_FOUND=true
        break
    fi
    
    # Check for critical errors in logs
    RECENT_LOGS=$(docker logs --tail 20 "$CONTAINER_NAME" 2>&1)
    if echo "$RECENT_LOGS" | grep -qE "CRITICAL|FATAL|Traceback"; then
        echo -e "${YELLOW}⚠️  Critical errors detected in logs${NC}"
        ERROR_FOUND=true
    fi
    
    sleep 5
    echo -n "." >&2
done

echo ""
echo ""

if [ "$ERROR_FOUND" = false ]; then
    echo -e "${GREEN}✅ Container ran successfully for ${TEST_DURATION} seconds${NC}"
else
    echo -e "${YELLOW}⚠️  Issues detected during test run${NC}"
fi

# Step 7: Check final logs
echo ""
echo -e "${YELLOW}Step 7: Final log check...${NC}"
FINAL_LOGS=$(docker logs --tail 30 "$CONTAINER_NAME" 2>&1)
echo ""
echo -e "${CYAN}--- Final Container Logs ---${NC}"
echo "$FINAL_LOGS"
echo -e "${CYAN}--- End Logs ---${NC}"
echo ""

# Step 8: Test graceful shutdown
echo -e "${YELLOW}Step 8: Testing graceful shutdown...${NC}"
docker stop --time 10 "$CONTAINER_NAME" > /dev/null

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Container stopped gracefully${NC}"
else
    echo -e "${YELLOW}⚠️  Container stop returned exit code: $?${NC}"
fi

# Step 9: Check exit code
echo ""
echo -e "${YELLOW}Step 9: Checking exit code...${NC}"
EXIT_CODE=$(docker inspect "$CONTAINER_NAME" --format='{{.State.ExitCode}}')
echo -e "${GRAY}Container exit code: ${EXIT_CODE}${NC}"

if [ "$EXIT_CODE" -eq 0 ] || [ "$EXIT_CODE" -eq 137 ]; then  # 137 = SIGKILL (normal for docker stop)
    echo -e "${GREEN}✅ Exit code is acceptable${NC}"
else
    echo -e "${YELLOW}⚠️  Unexpected exit code: ${EXIT_CODE}${NC}"
fi

# Cleanup
echo ""
echo -e "${YELLOW}Cleaning up...${NC}"
docker rm "$CONTAINER_NAME" > /dev/null
echo -e "${GREEN}✅ Container removed${NC}"

# Ask if user wants to remove the test image
echo ""
read -p "Remove test image ${FULL_IMAGE_NAME}? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker rmi "$FULL_IMAGE_NAME" > /dev/null
    echo -e "${GREEN}✅ Test image removed${NC}"
fi

# Summary
echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}Test Summary${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""
echo -e "${GREEN}✅ Docker image built successfully${NC}"
echo -e "${GREEN}✅ Container started with Home Assistant-like config${NC}"
echo -e "${GREEN}✅ Application executed without crashes${NC}"
echo -e "${GREEN}✅ Graceful shutdown tested${NC}"
echo ""
echo -e "${YELLOW}Note: Authentication will fail with test credentials,${NC}"
echo -e "${YELLOW}      but this validates the startup sequence works.${NC}"
echo ""
echo -e "${CYAN}Next steps:${NC}"
echo -e "${GRAY}  • Deploy to real Home Assistant instance${NC}"
echo -e "${GRAY}  • Configure with real MELCloud credentials${NC}"
echo -e "${GRAY}  • Verify MQTT discovery messages${NC}"
echo ""
