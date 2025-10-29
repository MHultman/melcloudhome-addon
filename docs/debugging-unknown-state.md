# Debugging Guide - "Unknown" State Issues

## Problem

All entities showing as "unknown" in Home Assistant even though the addon appears to be running.

## Diagnostic Steps

### 1. Enable Debug Logging

Edit your addon configuration and set the log level to DEBUG:

```yaml
log_level: "DEBUG"
```

Then restart the addon.

### 2. Check the Logs

Go to the addon logs and look for the following debug messages:

#### Device Discovery

```
Discovered X climate devices
```

#### Raw State Fetch

Look for messages like:

```
Raw state for device <device_id>: {...}
```

This shows the actual response from the MELCloud API. Check:

- Is the response a dict?
- Does it have a "settings" array (for ATW devices)?
- Does it have "capabilities"?

#### State Conversion

Look for messages like:

```
Converting state to MQTT for device <name> (atwunit)
```

This shows:

- How many settings were found
- Whether the state has the expected structure

#### Temperature Extraction

For ATW devices:

```
ATW device <name> temps: current=<X>, target=<Y>, tank=<Z>, ...
```

Check if these values are:

- `None` (not found in settings)
- Valid numbers
- The expected values from your device

#### MQTT Publishing

```
Publishing state to MQTT for <name>
MQTT payload JSON for <name>: {...}
```

This shows the exact JSON being sent to Home Assistant. Verify:

- `power`: Should be "ON" or "OFF"
- `temperature`: Should be a number (target temp)
- `current_temperature`: Should be a number (room temp)
- `available`: Should be `true`

### 3. Common Issues and Solutions

#### Issue: Settings array is empty

**Symptoms:** Log shows `settings_count: 0`

**Cause:** Device state not properly fetched from MELCloud API

**Solution:**

1. Check your MELCloud credentials
2. Verify the device is online in the MELCloud app
3. Try re-authenticating (restart addon)

#### Issue: Temperature values are None

**Symptoms:** Log shows `current=None, target=None`

**Cause:** Settings names don't match expected values

**Solution:**

1. Look at the raw state response in debug logs
2. Check what the actual setting names are
3. If they differ from expected (e.g., "RoomTemperatureZone1", "SetTemperatureZone1"), report this as a bug

#### Issue: MQTT payload looks good but HA still shows "unknown"

**Symptoms:** Payload has valid values but HA doesn't update

**Possible Causes:**

1. **MQTT broker not receiving messages**

   - Check MQTT broker logs
   - Verify MQTT connection in addon logs

2. **Home Assistant not subscribed to topics**

   - Check if discovery messages were sent
   - Look for: `Published MQTT discovery for <device_name>`
   - Try restarting Home Assistant

3. **Template parsing issues**
   - The value templates in discovery might not match payload structure
   - Check discovery topic: `homeassistant/climate/<device_id>/config`

#### Issue: Power state wrong but temps are correct

**Symptoms:** Temperature shows but entity appears off

**Cause:** Power state extraction not working

**Solution:**

1. Check debug log for power extraction: `Device <name> power state: ...`
2. For ATW devices, verify "Power" setting exists in settings array
3. Check if value is "True" or "False" (string)

### 4. Manual MQTT Verification

You can manually check what's being sent to MQTT:

```bash
# Subscribe to all topics for your device
mosquitto_sub -h <mqtt_host> -u <user> -P <pass> -t "homeassistant/climate/<device_id>/#" -v

# You should see:
# homeassistant/climate/<device_id>/config (discovery message)
# homeassistant/climate/<device_id>/state (state updates)
# homeassistant/climate/<device_id>/availability (online/offline)
```

### 5. Expected Log Flow (Normal Operation)

When everything is working, you should see this sequence in DEBUG logs:

```
1. Authentication:
   Authenticating with MELCloud...
   Login successful: Session token obtained

2. Device Discovery:
   Fetching devices from MELCloud...
   Discovered X climate devices

3. State Fetch (per device):
   Fetching state for device <id>
   Raw state for device <id>: {...}
   Device <id> has N settings

4. State Conversion:
   Converting state to MQTT for device <name>
   Device <name> power state: ON, online: true
   ATW device <name> temps: current=22.5, target=22.0, ...

5. MQTT Publishing:
   Publishing state to MQTT for <name>
   MQTT payload JSON for <name>: {"power":"ON","temperature":22.0,...}
   Published state for <name>

6. Repeat step 3-5 every poll_interval seconds
```

### 6. Report Issues

If debug logs show unexpected behavior, please report with:

1. Full debug logs (sanitize any credentials)
2. Device type (ATA vs ATW)
3. Expected vs actual behavior
4. Raw state response from logs
5. MQTT payload from logs

## Quick Fixes

### Reset Everything

1. Set `log_level: "DEBUG"`
2. Restart addon
3. Restart Home Assistant
4. Wait 2 minutes
5. Check logs for the expected flow above

### Force Re-discovery

1. Delete the addon configuration for MQTT topics:
   ```bash
   mosquitto_pub -h <mqtt_host> -u <user> -P <pass> \
     -t "homeassistant/climate/<device_id>/config" -n -r
   ```
2. Restart addon
3. Discovery messages will be resent

### Clear Home Assistant MQTT Cache

1. Go to Developer Tools → Services
2. Call: `mqtt.reload`
3. Wait 30 seconds
4. Check if entities update
