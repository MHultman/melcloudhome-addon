# ATW Device Control Guide

## Overview

The MELCloud Home Bridge addon now provides complete control over Air-to-Water (ATW) heat pump devices through Home Assistant. This guide explains all the available control entities and how to use them.

## Available Control Entities

### Power Control

**Entity Type:** Switch  
**Entity ID:** `switch.<device_name>_power`  
**Description:** Turn the ATW device on or off  
**Values:** ON, OFF

### Zone 1 Controls

#### Zone 1 Temperature Setpoint

**Entity Type:** Number  
**Entity ID:** `number.<device_name>_zone_1_temperature`  
**Description:** Set the target temperature for Zone 1  
**Range:** 16-30°C (from device capabilities)  
**Step:** 0.5°C (if device supports half degrees)  
**Mode:** Slider

#### Zone 1 Operation Mode

**Entity Type:** Select  
**Entity ID:** `select.<device_name>_zone_1_operation_mode`  
**Description:** Select the operation mode for Zone 1  
**Options:**

- `HeatRoomTemperature` - Control based on room temperature
- `HeatFlowTemperature` - Control based on water flow temperature
- `HeatCurve` - Control based on weather compensation curve

#### Zone 1 Heat Flow Temperature

**Entity Type:** Number  
**Entity ID:** `number.<device_name>_zone_1_heat_flow_temperature`  
**Description:** Set the heat flow temperature for Zone 1  
**Range:** 20-60°C  
**Step:** 1°C  
**Mode:** Box

#### Zone 1 Cool Flow Temperature

**Entity Type:** Number  
**Entity ID:** `number.<device_name>_zone_1_cool_flow_temperature`  
**Description:** Set the cool flow temperature for Zone 1  
**Range:** 5-25°C  
**Step:** 1°C  
**Mode:** Box

### Hot Water Controls (if supported)

#### Tank Temperature Setpoint

**Entity Type:** Number  
**Entity ID:** `number.<device_name>_tank_temperature_setpoint`  
**Description:** Set the target temperature for the hot water tank  
**Range:** 40-60°C (from device capabilities)  
**Step:** 1°C  
**Mode:** Slider

#### Forced Hot Water Mode

**Entity Type:** Switch  
**Entity ID:** `switch.<device_name>_forced_hot_water_mode`  
**Description:** Enable/disable forced hot water heating mode  
**Values:** ON, OFF

### Zone 2 Controls (if supported)

If your ATW device has a second zone, the following additional controls will be available:

- `number.<device_name>_zone_2_temperature`
- `select.<device_name>_zone_2_operation_mode`
- `number.<device_name>_zone_2_heat_flow_temperature`
- `number.<device_name>_zone_2_cool_flow_temperature`

All Zone 2 controls work identically to their Zone 1 counterparts.

## Monitoring Entities

In addition to control entities, the following read-only sensors are available:

### Temperature Sensors

- `sensor.<device_name>_tank_temperature` - Current tank water temperature
- `sensor.<device_name>_tank_target_temperature` - Target tank water temperature

### Status Sensors

- `sensor.<device_name>_zone_1_operation_mode` - Current Zone 1 operation mode
- `binary_sensor.<device_name>_forced_hot_water` - Forced hot water mode status
- `binary_sensor.<device_name>_prohibit_hot_water` - Prohibit hot water status
- `binary_sensor.<device_name>_standby_mode` - Standby mode status
- `binary_sensor.<device_name>_error` - Error state indicator
- `sensor.<device_name>_error_code` - Error code (if in error state)

## Usage Examples

### Basic Temperature Control

```yaml
# Set Zone 1 temperature to 22°C
service: number.set_value
target:
  entity_id: number.varmepanna_zone_1_temperature
data:
  value: 22
```

### Change Operation Mode

```yaml
# Switch to room temperature control mode
service: select.select_option
target:
  entity_id: select.varmepanna_zone_1_operation_mode
data:
  option: "HeatRoomTemperature"
```

### Enable Forced Hot Water

```yaml
# Turn on forced hot water mode
service: switch.turn_on
target:
  entity_id: switch.varmepanna_forced_hot_water_mode
```

### Set Tank Temperature

```yaml
# Set hot water tank to 55°C
service: number.set_value
target:
  entity_id: number.varmepanna_tank_temperature_setpoint
data:
  value: 55
```

## Automation Examples

### Temperature Scheduling

```yaml
automation:
  - alias: "Lower temperature at night"
    trigger:
      - platform: time
        at: "22:00:00"
    action:
      - service: number.set_value
        target:
          entity_id: number.varmepanna_zone_1_temperature
        data:
          value: 19

  - alias: "Raise temperature in morning"
    trigger:
      - platform: time
        at: "06:00:00"
    action:
      - service: number.set_value
        target:
          entity_id: number.varmepanna_zone_1_temperature
        data:
          value: 22
```

### Hot Water Boost During Off-Peak Hours

```yaml
automation:
  - alias: "Hot water boost during off-peak"
    trigger:
      - platform: time
        at: "01:00:00"
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.varmepanna_forced_hot_water_mode
      - delay:
          hours: 2
      - service: switch.turn_off
        target:
          entity_id: switch.varmepanna_forced_hot_water_mode
```

### Adaptive Heating Based on Weather

```yaml
automation:
  - alias: "Adjust heating for cold weather"
    trigger:
      - platform: numeric_state
        entity_id: weather.home
        attribute: temperature
        below: 0
    action:
      - service: number.set_value
        target:
          entity_id: number.varmepanna_zone_1_heat_flow_temperature
        data:
          value: 50
```

## Technical Details

### Command Topics

Control commands are sent via MQTT to the following topics:

- `homeassistant/climate/<device_id>/set_power`
- `homeassistant/climate/<device_id>/set_zone1_temperature`
- `homeassistant/climate/<device_id>/set_zone1_operation_mode`
- `homeassistant/climate/<device_id>/set_zone1_heat_flow_temperature`
- `homeassistant/climate/<device_id>/set_zone1_cool_flow_temperature`
- `homeassistant/climate/<device_id>/set_tank_temperature`
- `homeassistant/climate/<device_id>/set_forced_hot_water`
- (Zone 2 variants if supported)

### State Synchronization

- All commands are immediately executed via the MELCloud API
- Device state is automatically refreshed after each command
- Updated state is published back to Home Assistant via MQTT
- Typical response time: 2-5 seconds

### Capability Detection

The addon automatically detects device capabilities from the MELCloud API:

- `hasHotWater` - Enables tank temperature and forced hot water controls
- `hasZone2` - Enables Zone 2 control entities
- `minSetTemperature` / `maxSetTemperature` - Sets temperature control ranges
- `minSetTankTemperature` / `maxSetTankTemperature` - Sets tank temperature range
- `hasHalfDegrees` - Enables 0.5°C temperature steps

### Error Handling

- Invalid temperature values are rejected with warning logs
- Commands for unsupported features (e.g., Zone 2 on single-zone device) are ignored
- MELCloud API errors are logged and reported
- Connection failures trigger automatic reconnection

## Troubleshooting

### Controls Not Appearing

1. Verify your device is an ATW (Air-to-Water) unit
2. Check the addon logs for discovery messages
3. Restart Home Assistant to reload MQTT discovery
4. Check MQTT topic `homeassistant/+/+/config` for published discovery messages

### Commands Not Working

1. Check addon logs for API errors
2. Verify MQTT broker connectivity
3. Ensure MELCloud credentials are valid
4. Check device is online in MELCloud app
5. Verify temperature values are within valid ranges

### State Not Updating

1. Check `poll_interval` configuration (default: 60 seconds)
2. Verify MQTT state topic messages are being published
3. Check for network connectivity issues
4. Review addon logs for state refresh errors

## References

- [pymelcloudhome Library](https://github.com/MHultman/pymelcloudhome)
- [Home Assistant MQTT Discovery](https://www.home-assistant.io/integrations/mqtt/#mqtt-discovery)
- [Home Assistant Number Entity](https://www.home-assistant.io/integrations/number.mqtt/)
- [Home Assistant Select Entity](https://www.home-assistant.io/integrations/select.mqtt/)
- [Home Assistant Switch Entity](https://www.home-assistant.io/integrations/switch.mqtt/)
