#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Test MELCloud Home Bridge with real credentials
.DESCRIPTION
    This script runs the add-on with your actual MELCloud credentials to test
    authentication and device discovery. Credentials are loaded from .env.local file.
.PARAMETER Duration
    How long to run the container in seconds. Default: 60
.PARAMETER CredentialsFile
    Path to credentials file. Default: .env.local
.EXAMPLE
    .\scripts\test-with-real-credentials.ps1 -Duration 60
#>

param(
    [int]$Duration = 60,
    [string]$CredentialsFile = ".env.local"
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
$CredentialsPath = Join-Path $RepoRoot $CredentialsFile

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "MELCloud Home Bridge - Real Credentials Test" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Set-Location $RepoRoot

# Check if credentials file exists
if (-not (Test-Path $CredentialsPath)) {
    Write-Host "❌ Credentials file not found: $CredentialsPath" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please create $CredentialsFile with your MELCloud credentials:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  1. Copy .env.local.example to .env.local:" -ForegroundColor Gray
    Write-Host "     cp .env.local.example .env.local" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  2. Edit .env.local and add your real credentials:" -ForegroundColor Gray
    Write-Host "     MELCLOUD_EMAIL=your-email@example.com" -ForegroundColor Gray
    Write-Host "     MELCLOUD_PASSWORD=your-password" -ForegroundColor Gray
    Write-Host ""
    exit 1
}

Write-Host "Loading credentials from: $CredentialsFile" -ForegroundColor Gray
Write-Host ""

# Read credentials file and create environment variables
$EnvVars = @()
Get-Content $CredentialsPath | ForEach-Object {
    $line = $_.Trim()
    # Skip comments and empty lines
    if ($line -and -not $line.StartsWith("#")) {
        if ($line -match "^([^=]+)=(.*)$") {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            
            # Show masked value for sensitive fields
            if ($key -match "PASSWORD|SECRET") {
                Write-Host "  $key = ********" -ForegroundColor Gray
            } else {
                Write-Host "  $key = $value" -ForegroundColor Gray
            }
            
            $EnvVars += "-e"
            $EnvVars += "$key=$value"
        }
    }
}

Write-Host ""

# Build image name
$ImageName = "melcloudhome-bridge:amd64-real-test"

# Build the image
Write-Host "Building Docker image..." -ForegroundColor Yellow
docker build `
    --build-arg BUILD_FROM="ghcr.io/home-assistant/amd64-base-python:3.11-alpine3.18" `
    -t $ImageName `
    -f Dockerfile `
    . | Out-Null

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Docker build failed!" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Docker image built" -ForegroundColor Green
Write-Host ""

# Start container
$ContainerName = "melcloud-real-test-$(Get-Random)"

Write-Host "Starting container with real credentials..." -ForegroundColor Yellow
Write-Host "Container: $ContainerName" -ForegroundColor Gray
Write-Host "Duration: $Duration seconds" -ForegroundColor Gray
Write-Host ""

$DockerArgs = @(
    "run"
    "-d"
    "--name"
    $ContainerName
    "-p"
    "8099:8099"
) + $EnvVars + @($ImageName)

$ContainerId = & docker $DockerArgs

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to start container!" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Container started: $ContainerId" -ForegroundColor Green
Write-Host ""

# Wait a bit for startup
Write-Host "Waiting for startup (10 seconds)..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Show initial logs
Write-Host ""
Write-Host "--- Initial Startup Logs ---" -ForegroundColor Cyan
docker logs $ContainerName 2>&1 | Select-Object -First 60
Write-Host "--- End Initial Logs ---" -ForegroundColor Cyan
Write-Host ""

# Check if container is still running
$IsRunning = docker ps --filter "name=$ContainerName" --format "{{.Status}}"
if (-not ($IsRunning -match "Up")) {
    Write-Host "❌ Container stopped during startup!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Full logs:" -ForegroundColor Yellow
    docker logs $ContainerName 2>&1
    docker rm $ContainerName | Out-Null
    exit 1
}

Write-Host "✅ Container is running!" -ForegroundColor Green
Write-Host ""

# Test health endpoint
Write-Host "Testing health endpoint..." -ForegroundColor Yellow
Start-Sleep -Seconds 2

try {
    $Response = Invoke-WebRequest -Uri "http://localhost:8099/health" -TimeoutSec 5 -UseBasicParsing
    if ($Response.StatusCode -eq 200) {
        Write-Host "✅ Health endpoint responding: $($Response.StatusCode)" -ForegroundColor Green
        $HealthData = $Response.Content | ConvertFrom-Json
        Write-Host ""
        Write-Host "Health Status:" -ForegroundColor Cyan
        Write-Host "  Status: $($HealthData.status)" -ForegroundColor Gray
        Write-Host "  Version: $($HealthData.version)" -ForegroundColor Gray
        if ($HealthData.devices_count) {
            Write-Host "  Devices: $($HealthData.devices_count)" -ForegroundColor Gray
        }
        Write-Host ""
    }
} catch {
    Write-Host "⚠️  Health endpoint not ready yet: $($_.Exception.Message)" -ForegroundColor Yellow
    Write-Host ""
}

# Monitor for specified duration
Write-Host "Monitoring container for $Duration seconds..." -ForegroundColor Yellow
Write-Host "(Press Ctrl+C to stop early)" -ForegroundColor Gray
Write-Host ""

$StartTime = Get-Date
$LastCheck = Get-Date

while (((Get-Date) - $StartTime).TotalSeconds -lt $Duration) {
    # Check every 5 seconds
    if (((Get-Date) - $LastCheck).TotalSeconds -ge 5) {
        # Check if still running
        $IsRunning = docker ps --filter "name=$ContainerName" --format "{{.Status}}"
        if (-not ($IsRunning -match "Up")) {
            Write-Host ""
            Write-Host "❌ Container stopped unexpectedly!" -ForegroundColor Red
            break
        }
        
        $LastCheck = Get-Date
        Write-Host "." -NoNewline -ForegroundColor Gray
    }
    
    Start-Sleep -Seconds 1
}

Write-Host ""
Write-Host ""

# Show final logs
Write-Host "--- Final Container Logs (last 50 lines) ---" -ForegroundColor Cyan
docker logs --tail 50 $ContainerName 2>&1
Write-Host "--- End Logs ---" -ForegroundColor Cyan
Write-Host ""

# Stop container
Write-Host "Stopping container..." -ForegroundColor Yellow
docker stop --time 10 $ContainerName | Out-Null
docker rm $ContainerName | Out-Null

Write-Host "✅ Container stopped and removed" -ForegroundColor Green
Write-Host ""

# Cleanup
$Remove = Read-Host "Remove test image $ImageName? (y/N)"
if ($Remove -eq "y" -or $Remove -eq "Y") {
    docker rmi $ImageName | Out-Null
    Write-Host "✅ Test image removed" -ForegroundColor Green
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Test Complete" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Check the logs above to verify:" -ForegroundColor Yellow
Write-Host "  • MELCloud authentication succeeded" -ForegroundColor Gray
Write-Host "  • Devices were discovered" -ForegroundColor Gray
Write-Host "  • MQTT connection established (if broker available)" -ForegroundColor Gray
Write-Host ""
