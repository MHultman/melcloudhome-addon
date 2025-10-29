# MELCloud Home Bridge

Home Assistant add-on that bridges Mitsubishi MELCloud climate devices to Home Assistant via MQTT Discovery protocol. Automatically discovers your MELCloud devices and makes them available in Home Assistant as native climate entities.

## Features

- ✅ **Automatic Device Discovery**: All MELCloud devices automatically appear in Home Assistant
- ✅ **Real-time Control**: Change temperature, mode, and power state from Home Assistant
- ✅ **State Synchronization**: Device states update automatically (configurable poll interval)
- ✅ **Multiple Device Types**: Supports both ATA (Air-to-Air) and ATW (Air-to-Water) units
- ✅ **Resilient Operation**: Automatic recovery from network failures and session expiration
- ✅ **Health Monitoring**: Built-in health check endpoint for monitoring
- ✅ **Multi-Architecture**: Supports amd64, aarch64, and armv7 platforms

## Prerequisites

Before installing this add-on, ensure you have:

1. **Home Assistant** with Supervisor (HAOS, Container, or Supervised installation)
2. **MQTT Broker** installed (recommended: Mosquitto broker add-on)
3. **MQTT Integration** configured in Home Assistant
4. **MELCloud Account** with at least one registered device
5. **Internet Connectivity** for MELCloud API access

## Installation

### Step 1: Install MQTT Broker (if not already installed)

1. Navigate to **Settings** → **Add-ons** → **Add-on Store**
2. Search for "**Mosquitto broker**"
3. Click **Install** and wait for completion
4. Go to the **Configuration** tab, leave default settings
5. Click **Start** and enable **Start on boot**
6. Click **Watchdog** to enable automatic restart

### Step 2: Configure MQTT Integration (if not already configured)

1. Navigate to **Settings** → **Devices & Services** → **Integrations**
2. If MQTT integration already exists, skip to Step 3
3. Click **+ Add Integration**, search for "**MQTT**"
4. Enter broker details:
   - **Broker**: `core-mosquitto`
   - **Port**: `1883`
   - **Username**: (leave empty for default configuration)
   - **Password**: (leave empty for default configuration)
5. Click **Submit**

### Step 3: Add Repository

1. Navigate to **Settings** → **Add-ons** → **Add-on Store**
2. Click the **⋮** (three dots menu) in the top-right corner
3. Select **Repositories**
4. Add this repository URL:
   ```
   https://github.com/MHultman/melcloudhome-addon
   ```
5. Click **Add** → **Close**

### Step 4: Install MELCloud Home Bridge Add-on

1. Refresh the Add-on Store page
2. Find "**MELCloud Home Bridge**" in the list
3. Click on it, then click **Install**
4. Wait for installation to complete (may take 3-5 minutes for first install)

### Step 5: Configure the Add-on

1. After installation, go to the **Configuration** tab
2. Enter your MELCloud credentials:
   ```yaml
   melcloud_email: your.email@example.com
   melcloud_password: your_melcloud_password
   mqtt_host: core-mosquitto
   mqtt_port: 1883
   mqtt_base_topic: homeassistant
   poll_interval: 60
   log_level: INFO
   ```
3. **Required settings**:

   - `melcloud_email`: Your MELCloud account email
   - `melcloud_password`: Your MELCloud account password

4. **Optional settings** (use defaults if unsure):

   - `mqtt_host`: MQTT broker hostname (default: `core-mosquitto`)
   - `mqtt_port`: MQTT broker port (default: `1883`)
   - `mqtt_username`: MQTT username (leave empty for no authentication)
   - `mqtt_password`: MQTT password (leave empty for no authentication)
   - `mqtt_base_topic`: MQTT base topic (default: `homeassistant`)
   - `poll_interval`: Polling interval in seconds, 10-600 (default: `60`)
   - `log_level`: Logging level - `DEBUG`, `INFO`, `WARNING`, `ERROR` (default: `INFO`)

5. Click **Save**

### Step 6: Start the Add-on

1. Go to the **Info** tab
2. Click **Start**
3. Enable **Start on boot** for automatic startup
4. Enable **Watchdog** for automatic restart on failures

### Step 7: Verify Installation

1. Click **Log** tab to view add-on logs
2. Look for successful startup messages:

   ```
   MELCloud Home Bridge v1.0.0
   Configuration loaded successfully
   Authenticated with MELCloud
   Discovered X devices
   Connected to MQTT broker
   Application started successfully
   ```

3. Navigate to **Settings** → **Devices & Services** → **MQTT**
4. Your MELCloud devices should appear as climate entities
5. Click on a device to view and control it

## Configuration Options

| Option              | Required | Default          | Description                              |
| ------------------- | -------- | ---------------- | ---------------------------------------- |
| `melcloud_email`    | Yes      | -                | MELCloud account email address           |
| `melcloud_password` | Yes      | -                | MELCloud account password                |
| `mqtt_host`         | No       | `core-mosquitto` | MQTT broker hostname                     |
| `mqtt_port`         | No       | `1883`           | MQTT broker port                         |
| `mqtt_username`     | No       | -                | MQTT username (optional)                 |
| `mqtt_password`     | No       | -                | MQTT password (optional)                 |
| `mqtt_base_topic`   | No       | `homeassistant`  | MQTT base topic for HA Discovery         |
| `poll_interval`     | No       | `60`             | Device polling interval (10-600 seconds) |
| `log_level`         | No       | `INFO`           | Log level (DEBUG, INFO, WARNING, ERROR)  |

## Usage

Once installed and configured, your MELCloud devices will automatically appear in Home Assistant as climate entities. You can:

### Control from Home Assistant

- **Change Temperature**: Adjust target temperature using the climate card
- **Switch Modes**: Select operation mode (heat, cool, auto, fan, dry, off)
- **Power On/Off**: Turn devices on or off
- **Automation**: Use devices in automations and scripts
- **Dashboards**: Add climate cards to your Lovelace dashboards

### Example Automation

```yaml
automation:
  - alias: "Morning Warmup"
    trigger:
      - platform: time
        at: "06:00:00"
    action:
      - service: climate.set_temperature
        target:
          entity_id: climate.living_room_ac
        data:
          temperature: 22
          hvac_mode: heat
```

## Health Monitoring

The add-on exposes a health check endpoint on port `8099`:

```bash
curl http://homeassistant.local:8099/healthz
```

Response:

```json
{
  "status": "healthy",
  "melcloud_connected": true,
  "mqtt_connected": true,
  "last_poll": "2025-10-28T10:30:00Z",
  "device_count": 3,
  "uptime_seconds": 86400
}
```

## Troubleshooting

### Add-on won't start

1. **Check logs** in the **Log** tab for error messages
2. **Verify credentials**: Ensure MELCloud email and password are correct
3. **Test MELCloud access**: Try logging into https://app.melcloud.com/ with your credentials
4. **Check MQTT broker**: Ensure Mosquitto add-on is running

### Devices not appearing in Home Assistant

1. **Verify MQTT integration**: Check Settings → Devices & Services → MQTT
2. **Check MQTT broker**: Ensure core-mosquitto add-on is running
3. **Review logs**: Look for "Discovered X devices" in add-on logs
4. **Restart MQTT integration**: Go to Settings → Devices & Services → MQTT → ⋮ → Reload

### Authentication fails

1. **Verify credentials**: Double-check email and password (case-sensitive)
2. **Check MELCloud status**: Ensure MELCloud service is online
3. **Review logs**: Look for detailed error messages in add-on logs with `log_level: DEBUG`

### State updates are slow

1. **Adjust poll_interval**: Reduce from 60 seconds to 30 seconds (minimum recommended: 30)
2. **Check network**: Ensure stable internet connection
3. **Review logs**: Look for polling errors or timeouts

### High memory usage

1. **Check device count**: Add-on uses ~50MB + ~10MB per device
2. **Reduce poll frequency**: Increase poll_interval to reduce API calls
3. **Restart add-on**: Memory should stabilize under 200MB

## Support

- **Issues**: Report bugs at [GitHub Issues](https://github.com/MHultman/melcloudhome-addon/issues)
- **Discussions**: Ask questions at [GitHub Discussions](https://github.com/MHultman/melcloudhome-addon/discussions)
- **Documentation**: Full documentation in `/specs/` directory

## Technical Details

- **Architecture**: Python 3.11 async application using pymelcloudhome library v0.3.0+
- **Authentication**: Chromium-based browser automation for MELCloud login (via Pyppeteer)
- **Browser**: System Chromium (`/usr/bin/chromium`) pre-installed in Alpine Linux container
- **ARM64 Support**: Native support for Raspberry Pi (aarch64) and armv7 architectures
- **Protocol**: MQTT Discovery for Home Assistant integration
- **Container**: Alpine Linux base with optimized Chromium installation
- **Supported Devices**: ATA (Air-to-Air) and ATW (Air-to-Water) MELCloud units

### Browser Automation

This add-on uses **pymelcloudhome v0.3.0** which provides improved browser automation support:

- **System Chromium**: Uses the Alpine Linux system Chromium installation instead of downloading browsers
- **Pyppeteer**: Uses Pyppeteer (Puppeteer for Python) for headless browser automation, replacing Playwright
- **Reduced Image Size**: No need to bundle browser binaries in the container
- **Multi-Architecture**: Full support for amd64, aarch64 (Raspberry Pi), and armv7 platforms
- **Headless Mode**: Runs Chromium in headless mode for authentication without GUI requirements

The add-on automatically configures pymelcloudhome to use the system Chromium at `/usr/bin/chromium`.

## License

MIT License - See LICENSE file for details

## Credits

- **pymelcloudhome**: MELCloud API client library
- **Playwright**: Browser automation framework
- **Home Assistant**: Home automation platform
