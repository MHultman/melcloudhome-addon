# Home Assistant Add-on Deployment Guide

## Current Status: Ready for Deployment ✅

The repository has been configured to work as a Home Assistant add-on repository. All required files are in place and properly configured.

## What Was Fixed

### 1. Repository Structure

- ✅ Created `repository.json` with metadata (required by Home Assistant)
- ✅ Verified single add-on layout (config.yaml, Dockerfile, run.sh at root)
- ✅ Created `ICONS.md` documenting icon/logo requirements (optional but recommended)

### 2. Image Naming

**Before:**

```yaml
image: "ghcr.io/{arch}-melcloudhome-bridge" # ❌ Wrong format
```

**After:**

```yaml
image: "ghcr.io/mhultman/melcloudhome-addon-{arch}" # ✅ Correct format
```

Home Assistant replaces `{arch}` at runtime with:

- `amd64` for x86_64 systems
- `aarch64` for ARM 64-bit systems
- `armv7` for ARM 32-bit systems

### 3. GitHub Actions Build Workflow

Updated `.github/workflows/build.yaml` to:

- ✅ Build per-architecture images with correct naming
- ✅ Tag images as: `ghcr.io/mhultman/melcloudhome-addon-amd64:latest`, etc.
- ✅ Removed multi-arch manifest job (HA pulls per-arch images directly)

Example generated image names:

- `ghcr.io/mhultman/melcloudhome-addon-amd64:latest`
- `ghcr.io/mhultman/melcloudhome-addon-aarch64:latest`
- `ghcr.io/mhultman/melcloudhome-addon-armv7:latest`

## Next Steps

### Step 1: Commit and Push Changes

```powershell
git add .
git commit -m "fix: Configure repository for Home Assistant add-on deployment"
git push origin main
```

### Step 2: Publish Docker Images

The GitHub Actions workflow will automatically:

1. Build Docker images for all three architectures
2. Push them to GitHub Container Registry (ghcr.io)

**Important:** Make sure the images are set to **public** in GitHub Container Registry settings:

1. Go to: https://github.com/users/MHultman/packages/container/melcloudhome-addon-amd64/settings
2. Repeat for `melcloudhome-addon-aarch64` and `melcloudhome-addon-armv7`
3. Change visibility from "Private" to "Public"

### Step 3: Verify Images Are Published

Check that all three architecture images are available:

- https://github.com/MHultman/melcloudhome-addon/pkgs/container/melcloudhome-addon-amd64
- https://github.com/MHultman/melcloudhome-addon/pkgs/container/melcloudhome-addon-aarch64
- https://github.com/MHultman/melcloudhome-addon/pkgs/container/melcloudhome-addon-armv7

### Step 4: Add Repository to Home Assistant

1. Navigate to **Settings** → **Add-ons** → **Add-on Store**
2. Click the **⋮** (three dots) in the top-right corner
3. Select **Repositories**
4. Add: `https://github.com/MHultman/melcloudhome-addon`
5. Click **Add** → **Close**

### Step 5: Install and Test

1. Refresh the Add-on Store
2. Find "**MELCloud Home Bridge**" in the list
3. Click **Install**
4. Configure with your MELCloud credentials
5. Start the add-on
6. Check logs for successful startup

## Troubleshooting

### "Not a valid add-on repository" Error

**Causes:**

1. Docker images not yet published to ghcr.io
2. Images are private (need to be public)
3. Image names don't match config.yaml pattern

**Solution:**
Wait for GitHub Actions to complete, make images public, then try again.

### "Failed to pull image" Error

**Causes:**

1. Images are private in GitHub Container Registry
2. Wrong image architecture for your system

**Solution:**
Make all three architecture images public in GitHub Container Registry settings.

### Add-on Fails to Start

**Causes:**

1. Invalid MELCloud credentials
2. MQTT broker not available
3. Network connectivity issues

**Solution:**
Check add-on logs for specific error messages. Verify:

- MELCloud credentials are correct
- MQTT broker (core-mosquitto) is installed and running
- Internet connectivity for MELCloud API access

## Architecture Overview

```
GitHub Repository
├── repository.json          # HA repository metadata
├── config.yaml              # Add-on configuration (references images)
├── Dockerfile               # Multi-arch image definition
└── run.sh                   # Startup script (bashio integration)

GitHub Container Registry (ghcr.io)
├── melcloudhome-addon-amd64:latest
├── melcloudhome-addon-aarch64:latest
└── melcloudhome-addon-armv7:latest

Home Assistant Supervisor
└── Pulls correct architecture image based on system
```

## Optional: Add Icons

To improve visual presentation in the Home Assistant UI, add:

1. **icon.png** - 256x256 PNG for add-on icon
2. **logo.png** - 256x256 PNG for add-on logo

Place these files in the repository root. See `ICONS.md` for details.

The add-on will work fine without icons, but they make it look more professional.

## Testing Checklist

Before publishing to the community:

- [ ] GitHub Actions build succeeds for all architectures
- [ ] All three Docker images are public in ghcr.io
- [ ] Repository can be added to Home Assistant
- [ ] Add-on appears in the Add-on Store
- [ ] Add-on installs successfully
- [ ] Add-on starts with valid MELCloud credentials
- [ ] Devices appear in Home Assistant via MQTT Discovery
- [ ] Device controls (temperature, mode) work correctly
- [ ] State updates reflect within poll_interval seconds
- [ ] Health endpoint responds on port 8099
- [ ] Logs show no errors during normal operation

## Support

If you encounter issues:

1. Check the [troubleshooting section](#troubleshooting)
2. Review add-on logs: Settings → Add-ons → MELCloud Home Bridge → Log
3. Open an issue: https://github.com/MHultman/melcloudhome-addon/issues
