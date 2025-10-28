# Quickstart Guide: MELCloud Home Bridge

**Goal**: Integrate your Mitsubishi MELCloud climate devices into Home Assistant in under 5 minutes.

## Prerequisites

Before you begin, ensure you have:

- ✅ Home Assistant with Supervisor (HAOS, Container, or Supervised installation)
- ✅ MQTT broker installed (recommended: Mosquitto add-on)
- ✅ Home Assistant MQTT integration configured
- ✅ Active MELCloud account with devices
- ✅ Internet connectivity

## Step 1: Install MQTT Broker (if not already installed)

1. Navigate to **Settings** → **Add-ons** → **Add-on Store**
2. Search for "**Mosquitto broker**"
3. Click **Install** and wait for completion
4. Go to **Configuration** tab, leave default settings
5. Click **Start** and enable **Start on boot**

**Time**: ~2 minutes

---

## Step 2: Configure MQTT Integration

1. Navigate to **Settings** → **Devices & Services** → **Integrations**
2. If MQTT integration already exists, skip to Step 3
3. Click **+ Add Integration**, search for "**MQTT**"
4. Enter broker details:
   - Broker: `core-mosquitto`
   - Port: `1883`
   - Username/Password: leave empty (default)
5. Click **Submit**

**Time**: ~1 minute

---

## Step 3: Install MELCloud Home Bridge Add-on

1. Navigate to **Settings** → **Add-ons** → **Add-on Store**
2. Click **⋮** (three dots) → **Repositories**
3. Add repository: `https://github.com/YOUR_USERNAME/melcloudhome-addon`
4. Find "**MELCloud Home Bridge**" in add-on list
5. Click **Install** (may take 3-5 minutes for first install due to Playwright/Chromium download)

**Time**: ~5 minutes

---

## Step 4: Configure the Add-on

1. After installation, go to **Configuration** tab
2. Fill in required fields:
   ```yaml
   melcloud_email: your-email@example.com
   melcloud_password: your-melcloud-password
   mqtt_host: core-mosquitto
   mqtt_port: 1883
   ```
3. Optional settings (use defaults for now):
   - `mqtt_base_topic`: `homeassistant`
   - `poll_interval`: `60` (seconds)
   - `log_level`: `INFO`
4. Click **Save**

**Time**: ~1 minute

---

## Step 5: Start the Add-on and Verify Devices

1. Click **Start** on the add-on page
2. Enable **Start on boot** and **Watchdog**
3. Go to **Log** tab and look for:
   ```
   INFO | melcloud_client:authenticate - Authenticated successfully
   INFO | melcloud_client:discover_devices - Discovered 3 devices
   INFO | mqtt_bridge:publish_discovery - Published discovery for Living Room AC
   ```
4. Navigate to **Settings** → **Devices & Services** → **MQTT**
5. Your MELCloud devices should appear as new climate entities!

**Time**: ~1 minute

---

## Total Time: ~5 minutes ✅

## Verify It's Working

1. Go to **Settings** → **Devices & Services** → **MQTT** → **Devices**
2. Find your MELCloud device (e.g., "Living Room AC")
3. Click on device to see climate entity
4. Try changing temperature or mode
5. Check physical device or MELCloud app - changes should reflect within ~15 seconds

---

## Troubleshooting Quick Fixes

### ❌ "Authentication failed" in logs

**Solution**: Double-check your MELCloud email and password in add-on configuration. Ensure you can log into MELCloud website with same credentials.

### ❌ "MQTT connection failed" in logs

**Solution**: Verify Mosquitto add-on is running. Check `mqtt_host` is set to `core-mosquitto`. If using external broker, verify host/port/credentials.

### ❌ No devices appear in Home Assistant

**Solution**:

1. Check add-on logs for "Discovered X devices" message
2. Ensure MQTT integration is configured and running
3. Verify your MELCloud account actually has devices associated
4. Try restarting the add-on

### ❌ Devices discovered but not responsive

**Solution**:

1. Check if devices show as "unavailable" in HA
2. Verify MELCloud app can control devices (internet connectivity)
3. Check add-on logs for API errors
4. Increase `poll_interval` if seeing rate limit errors

---

## Next Steps

Once your devices are working:

- ✅ Create automations using your climate entities
- ✅ Add climate cards to Lovelace dashboards
- ✅ Adjust `poll_interval` if needed (faster updates = more API calls)
- ✅ Enable DEBUG logging if troubleshooting issues
- ✅ Monitor health endpoint at `http://homeassistant.local:8099/healthz`

---

## Advanced Configuration

### Custom MQTT Base Topic

If running multiple Home Assistant instances or want to isolate discovery messages:

```yaml
mqtt_base_topic: homeassistant_melcloud
```

Remember to reconfigure MQTT integration in HA to listen to this topic.

### Faster Updates

For near-real-time updates (at cost of more API calls):

```yaml
poll_interval: 30 # Poll every 30 seconds
```

⚠️ **Warning**: Very low intervals (<30s) may trigger MELCloud rate limits.

### Debug Logging

For detailed troubleshooting:

```yaml
log_level: DEBUG
```

View detailed API requests, MQTT messages, and session management in logs.

---

## Getting Help

- 📖 **Full Documentation**: [README.md](../../README.md)
- 🐛 **Report Issues**: [GitHub Issues](https://github.com/YOUR_USERNAME/melcloudhome-addon/issues)
- 💬 **Community Forum**: [Home Assistant Community](https://community.home-assistant.io/)
- 📋 **Check Logs**: Add-on → Log tab for error details

---

**Congratulations!** Your MELCloud devices are now integrated into Home Assistant. Enjoy automated climate control! 🎉
