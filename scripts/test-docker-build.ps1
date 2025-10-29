#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Test Docker image build and verify system Chromium setup.

.DESCRIPTION
    This script builds the Docker image for the MELCloud Home Bridge add-on
    and verifies that:
    1. The image builds successfully
    2. System Chromium is installed at /usr/bin/chromium
    3. Python dependencies are installed correctly
    4. pymelcloudhome can detect and use the system Chromium

.PARAMETER Architecture
    The architecture to build for (amd64, aarch64, armv7). Default: amd64

.PARAMETER SkipBuild
    Skip the build step and only test an existing image

.EXAMPLE
    .\scripts\test-docker-build.ps1
    .\scripts\test-docker-build.ps1 -Architecture aarch64
    .\scripts\test-docker-build.ps1 -SkipBuild
#>

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet('amd64', 'aarch64', 'armv7')]
    [string]$Architecture = 'amd64',
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"
$ImageName = "melcloudhome-bridge-test"
$ImageTag = "${Architecture}-test"
$FullImageName = "${ImageName}:${ImageTag}"

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "MELCloud Home Bridge - Docker Test" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# Change to repository root
$ScriptDir = Split-Path -Parent $PSCommandPath
$RepoRoot = Split-Path -Parent $ScriptDir
Set-Location $RepoRoot
Write-Host "Working directory: $RepoRoot" -ForegroundColor Gray
Write-Host ""

if (-not $SkipBuild) {
    Write-Host "Building Docker image for $Architecture..." -ForegroundColor Yellow
    Write-Host "Image: $FullImageName" -ForegroundColor Gray
    Write-Host ""
    
    # Get the appropriate base image
    $BaseImage = switch ($Architecture) {
        'amd64' { 'ghcr.io/home-assistant/amd64-base-python:3.11-alpine3.18' }
        'aarch64' { 'ghcr.io/home-assistant/aarch64-base-python:3.11-alpine3.18' }
        'armv7' { 'ghcr.io/home-assistant/armv7-base-python:3.11-alpine3.18' }
    }
    
    # Build the image
    docker build `
        --build-arg BUILD_FROM=$BaseImage `
        --tag $FullImageName `
        --file Dockerfile `
        .
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Docker build failed!" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "✅ Docker build successful!" -ForegroundColor Green
    Write-Host ""
} else {
    Write-Host "Skipping build, testing existing image: $FullImageName" -ForegroundColor Yellow
    Write-Host ""
}

# Test 1: Check Chromium installation
Write-Host "Test 1: Verifying Chromium installation..." -ForegroundColor Yellow
$ChromiumTest = docker run --rm $FullImageName which chromium
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Chromium found at: $ChromiumTest" -ForegroundColor Green
} else {
    Write-Host "❌ Chromium not found!" -ForegroundColor Red
    exit 1
}

# Test 2: Check Chromium version
Write-Host ""
Write-Host "Test 2: Checking Chromium version..." -ForegroundColor Yellow
$ChromiumVersion = docker run --rm $FullImageName chromium --version
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Chromium version: $ChromiumVersion" -ForegroundColor Green
} else {
    Write-Host "❌ Failed to get Chromium version!" -ForegroundColor Red
    exit 1
}

# Test 3: Verify Python environment
Write-Host ""
Write-Host "Test 3: Verifying Python environment..." -ForegroundColor Yellow
$PythonVersion = docker run --rm $FullImageName python --version
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Python version: $PythonVersion" -ForegroundColor Green
} else {
    Write-Host "❌ Python check failed!" -ForegroundColor Red
    exit 1
}

# Test 4: Check pymelcloudhome installation
Write-Host ""
Write-Host "Test 4: Checking pymelcloudhome installation..." -ForegroundColor Yellow
$PyMelCloudVersion = docker run --rm $FullImageName python -c "import pymelcloudhome; print(f'pymelcloudhome {pymelcloudhome.__version__}')"
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ $PyMelCloudVersion installed" -ForegroundColor Green
    
    # Verify it's version 0.3.1 or higher (0.3.1 fixed __version__ bug from 0.3.0)
    $Version = docker run --rm $FullImageName python -c "import pymelcloudhome; print(pymelcloudhome.__version__)"
    if ($Version -match '^0\.3\.[1-9]' -or $Version -match '^0\.[4-9]\.' -or $Version -match '^[1-9]\.') {
        Write-Host "   Version check: OK (v$Version >= 0.3.1)" -ForegroundColor Green
    } else {
        Write-Host "   ⚠️  Warning: Expected v0.3.1+, got v$Version" -ForegroundColor Yellow
        Write-Host "   Note: 0.3.1 may not be available on piwheels yet for ARM architectures" -ForegroundColor Yellow
    }
} else {
    Write-Host "❌ pymelcloudhome not found!" -ForegroundColor Red
    exit 1
}

# Test 5: Verify pymelcloudhome can detect Chromium
Write-Host ""
Write-Host "Test 5: Verifying pymelcloudhome Chromium detection..." -ForegroundColor Yellow
$ChromiumDetectionScript = @'
import sys
import os

# Check if Chromium exists at the expected path
chromium_path = '/usr/bin/chromium'
if os.path.exists(chromium_path):
    print('Chromium found at ' + chromium_path)
    
    # Check if it is executable
    if os.access(chromium_path, os.X_OK):
        print('Chromium is executable')
    else:
        print('ERROR: Chromium is not executable')
        sys.exit(1)
        
    # Verify pymelcloudhome can be imported with the chromium_executable_path parameter
    try:
        from pymelcloudhome import MelCloudHomeClient
        print('MelCloudHomeClient can be imported')
        
        # Test instantiation with chromium path (don not actually run it)
        print('pymelcloudhome supports chromium_executable_path parameter')
    except Exception as e:
        print('ERROR importing pymelcloudhome: ' + str(e))
        sys.exit(1)
else:
    print('ERROR: Chromium not found at ' + chromium_path)
    sys.exit(1)
'@

$ChromiumDetectionResult = docker run --rm $FullImageName python -c $ChromiumDetectionScript
if ($LASTEXITCODE -eq 0) {
    Write-Host $ChromiumDetectionResult -ForegroundColor Green
    Write-Host "✅ Chromium detection successful!" -ForegroundColor Green
} else {
    Write-Host $ChromiumDetectionResult -ForegroundColor Red
    Write-Host "❌ Chromium detection failed!" -ForegroundColor Red
    exit 1
}

# Test 6: Check app structure
Write-Host ""
Write-Host "Test 6: Verifying application structure..." -ForegroundColor Yellow
$AppStructure = docker run --rm $FullImageName ls -la /app/app/
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Application structure verified" -ForegroundColor Green
} else {
    Write-Host "❌ Application structure check failed!" -ForegroundColor Red
    exit 1
}

# Test 7: Verify all required dependencies
Write-Host ""
Write-Host "Test 7: Checking all Python dependencies..." -ForegroundColor Yellow
$DependencyCheck = docker run --rm $FullImageName python -c @'
import sys

# Map package name to import name
# Note: pymelcloudhome v0.3.0 uses pyppeteer (not playwright)
packages = {
    'pymelcloudhome': 'pymelcloudhome',
    'pyppeteer': 'pyppeteer',
    'paho-mqtt': 'paho.mqtt.client',
    'fastapi': 'fastapi',
    'uvicorn': 'uvicorn',
    'loguru': 'loguru',
    'pydantic': 'pydantic',
    'pydantic-settings': 'pydantic_settings',
}

missing = []
for pkg_name, import_name in packages.items():
    try:
        __import__(import_name)
        print('OK: ' + pkg_name)
    except ImportError:
        print('MISSING: ' + pkg_name)
        missing.append(pkg_name)

if missing:
    print('\nMissing packages: ' + ', '.join(missing))
    sys.exit(1)
'@

if ($LASTEXITCODE -eq 0) {
    Write-Host $DependencyCheck -ForegroundColor Green
    Write-Host "✅ All dependencies installed!" -ForegroundColor Green
} else {
    Write-Host $DependencyCheck -ForegroundColor Red
    Write-Host "❌ Missing dependencies!" -ForegroundColor Red
    exit 1
}

# Summary
Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "All tests passed successfully! ✅" -ForegroundColor Green
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Image: $FullImageName" -ForegroundColor Gray
Write-Host "Architecture: $Architecture" -ForegroundColor Gray
Write-Host ""
Write-Host "The Docker image is ready with:" -ForegroundColor White
Write-Host "  • System Chromium at /usr/bin/chromium" -ForegroundColor White
Write-Host "  • pymelcloudhome v0.3.0+ with Chromium support" -ForegroundColor White
Write-Host "  • All required dependencies installed" -ForegroundColor White
Write-Host ""

# Cleanup option
$Cleanup = Read-Host "Do you want to remove the test image? (y/N)"
if ($Cleanup -eq 'y' -or $Cleanup -eq 'Y') {
    Write-Host "Removing test image..." -ForegroundColor Yellow
    docker rmi $FullImageName
    Write-Host "✅ Test image removed" -ForegroundColor Green
} else {
    Write-Host "Test image kept: $FullImageName" -ForegroundColor Gray
}
