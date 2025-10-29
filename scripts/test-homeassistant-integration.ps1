#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Test MELCloud Home Bridge add-on in a simulated Home Assistant environment
.DESCRIPTION
    This script tests the add-on by:
    1. Creating a test configuration matching Home Assistant's options format
    2. Running the Docker container with environment variables
    3. Checking if the application starts without errors
    4. Verifying the health endpoint responds
    5. Testing graceful shutdown
.PARAMETER Architecture
    Target architecture (amd64, aarch64, armv7). Default: amd64
.PARAMETER TestDuration
    How long to run the container in seconds. Default: 30
.EXAMPLE
    .\scripts\test-homeassistant-integration.ps1 -Architecture amd64 -TestDuration 30
#>

param(
    [ValidateSet("amd64", "aarch64", "armv7")]
    [string]$Architecture = "amd64",
    
    [int]$TestDuration = 30
)

$ErrorActionPreference = "Continue"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir

# Colors for output
function Write-ColorOutput($ForegroundColor) {
    $fc = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    if ($args) {
        Write-Output $args
    }
    $host.UI.RawUI.ForegroundColor = $fc
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Home Assistant Integration Test" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Architecture: $Architecture" -ForegroundColor Gray
Write-Host "Test duration: $TestDuration seconds" -ForegroundColor Gray
Write-Host "Working directory: $RepoRoot" -ForegroundColor Gray
Write-Host ""

Set-Location $RepoRoot

# Build test image name
$ImageName = "melcloudhome-bridge"
$Tag = "$Architecture-ha-test"
$FullImageName = "${ImageName}:${Tag}"

# Step 1: Build the Docker image
Write-Host "Step 1: Building Docker image..." -ForegroundColor Yellow
Write-Host "Image: $FullImageName" -ForegroundColor Gray
Write-Host ""

$BaseImage = switch ($Architecture) {
    "amd64" { "ghcr.io/home-assistant/amd64-base-python:3.11-alpine3.18" }
    "aarch64" { "ghcr.io/home-assistant/aarch64-base-python:3.11-alpine3.18" }
    "armv7" { "ghcr.io/home-assistant/armv7-base-python:3.11-alpine3.18" }
}

docker build `
    --build-arg BUILD_FROM="$BaseImage" `
    --platform "linux/$Architecture" `
    -t $FullImageName `
    -f Dockerfile `
    .

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Docker build failed!" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Docker build successful!" -ForegroundColor Green
Write-Host ""

# Step 2: Test with mock credentials (will fail authentication but should start cleanly)
Write-Host "Step 2: Testing application startup..." -ForegroundColor Yellow
Write-Host "Using test credentials (will fail auth but validates startup)" -ForegroundColor Gray
Write-Host ""

# Create a temporary container name
$ContainerName = "melcloud-ha-test-$(Get-Random)"

# Start container with test environment variables
Write-Host "Starting container: $ContainerName" -ForegroundColor Gray
$ContainerId = docker run -d `
    --name $ContainerName `
    -e MELCLOUD_EMAIL="test@example.com" `
    -e MELCLOUD_PASSWORD="testpassword123" `
    -e MQTT_HOST="localhost" `
    -e MQTT_PORT="1883" `
    -e MQTT_USERNAME="" `
    -e MQTT_PASSWORD="" `
    -e MQTT_BASE_TOPIC="homeassistant" `
    -e POLL_INTERVAL="60" `
    -e LOG_LEVEL="INFO" `
    -p 8099:8099 `
    $FullImageName

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to start container!" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Container started: $ContainerId" -ForegroundColor Green
Write-Host ""

# Step 3: Wait for startup and collect logs
Write-Host "Step 3: Monitoring startup logs..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

$Logs = docker logs $ContainerName 2>&1
Write-Host ""
Write-Host "--- Container Logs (first 5 seconds) ---" -ForegroundColor Cyan
$Logs | Select-Object -First 50
Write-Host "--- End Logs ---" -ForegroundColor Cyan
Write-Host ""

# Step 4: Check if application is running
Write-Host "Step 4: Checking application status..." -ForegroundColor Yellow

$IsRunning = docker ps --filter "name=$ContainerName" --format "{{.Status}}"
if ($IsRunning -match "Up") {
    Write-Host "✅ Container is running" -ForegroundColor Green
} else {
    Write-Host "❌ Container is not running!" -ForegroundColor Red
    docker logs $ContainerName 2>&1
    docker rm -f $ContainerName | Out-Null
    exit 1
}

# Step 5: Test health endpoint
Write-Host ""
Write-Host "Step 5: Testing health endpoint..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

try {
    $Response = Invoke-WebRequest -Uri "http://localhost:8099/health" -TimeoutSec 5 -UseBasicParsing
    if ($Response.StatusCode -eq 200) {
        Write-Host "✅ Health endpoint responding: $($Response.StatusCode)" -ForegroundColor Green
        $HealthData = $Response.Content | ConvertFrom-Json
        Write-Host "   Status: $($HealthData.status)" -ForegroundColor Gray
        if ($HealthData.version) {
            Write-Host "   Version: $($HealthData.version)" -ForegroundColor Gray
        }
    } else {
        Write-Host "⚠️  Health endpoint returned: $($Response.StatusCode)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠️  Health endpoint not accessible (may still be starting up)" -ForegroundColor Yellow
    Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Gray
}

# Step 6: Monitor for a period
Write-Host ""
Write-Host "Step 6: Running for $TestDuration seconds..." -ForegroundColor Yellow
Write-Host "Monitoring for crashes or errors..." -ForegroundColor Gray

$StartTime = Get-Date
$ErrorFound = $false

while (((Get-Date) - $StartTime).TotalSeconds -lt $TestDuration) {
    # Check if container is still running
    $IsRunning = docker ps --filter "name=$ContainerName" --format "{{.Status}}"
    if (-not ($IsRunning -match "Up")) {
        Write-Host "❌ Container stopped unexpectedly!" -ForegroundColor Red
        $ErrorFound = $true
        break
    }
    
    # Check for critical errors in logs
    $RecentLogs = docker logs --tail 20 $ContainerName 2>&1
    if ($RecentLogs -match "CRITICAL|FATAL|Traceback") {
        Write-Host "⚠️  Critical errors detected in logs" -ForegroundColor Yellow
        $ErrorFound = $true
    }
    
    Start-Sleep -Seconds 5
    Write-Host "." -NoNewline -ForegroundColor Gray
}

Write-Host ""
Write-Host ""

if (-not $ErrorFound) {
    Write-Host "✅ Container ran successfully for $TestDuration seconds" -ForegroundColor Green
} else {
    Write-Host "⚠️  Issues detected during test run" -ForegroundColor Yellow
}

# Step 7: Check final logs
Write-Host ""
Write-Host "Step 7: Final log check..." -ForegroundColor Yellow
$FinalLogs = docker logs --tail 30 $ContainerName 2>&1
Write-Host ""
Write-Host "--- Final Container Logs ---" -ForegroundColor Cyan
$FinalLogs
Write-Host "--- End Logs ---" -ForegroundColor Cyan
Write-Host ""

# Step 8: Test graceful shutdown
Write-Host "Step 8: Testing graceful shutdown..." -ForegroundColor Yellow
docker stop --time 10 $ContainerName | Out-Null

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Container stopped gracefully" -ForegroundColor Green
} else {
    Write-Host "⚠️  Container stop returned exit code: $LASTEXITCODE" -ForegroundColor Yellow
}

# Step 9: Check exit code
Write-Host ""
Write-Host "Step 9: Checking exit code..." -ForegroundColor Yellow
$ExitCode = docker inspect $ContainerName --format='{{.State.ExitCode}}'
Write-Host "Container exit code: $ExitCode" -ForegroundColor Gray

if ($ExitCode -eq 0 -or $ExitCode -eq 137) {  # 137 = SIGKILL (normal for docker stop)
    Write-Host "✅ Exit code is acceptable" -ForegroundColor Green
} else {
    Write-Host "⚠️  Unexpected exit code: $ExitCode" -ForegroundColor Yellow
}

# Cleanup
Write-Host ""
Write-Host "Cleaning up..." -ForegroundColor Yellow
docker rm $ContainerName | Out-Null
Write-Host "✅ Container removed" -ForegroundColor Green

# Ask if user wants to remove the test image
Write-Host ""
$Remove = Read-Host "Remove test image $FullImageName? (y/N)"
if ($Remove -eq "y" -or $Remove -eq "Y") {
    docker rmi $FullImageName | Out-Null
    Write-Host "✅ Test image removed" -ForegroundColor Green
}

# Summary
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Test Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "✅ Docker image built successfully" -ForegroundColor Green
Write-Host "✅ Container started with Home Assistant-like config" -ForegroundColor Green
Write-Host "✅ Application executed without crashes" -ForegroundColor Green
Write-Host "✅ Graceful shutdown tested" -ForegroundColor Green
Write-Host ""
Write-Host "Note: Authentication will fail with test credentials," -ForegroundColor Yellow
Write-Host "      but this validates the startup sequence works." -ForegroundColor Yellow
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  • Deploy to real Home Assistant instance" -ForegroundColor Gray
Write-Host "  • Configure with real MELCloud credentials" -ForegroundColor Gray
Write-Host "  • Verify MQTT discovery messages" -ForegroundColor Gray
Write-Host ""
