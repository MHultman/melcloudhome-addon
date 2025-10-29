# Home Assistant Entity Reference for MELCloud ATW Heat Pumps

## Quick Reference

All entities are automatically discovered in Home Assistant when you have an ATW (Air-to-Water) heat pump.

### Main Climate Control

**Entity**: `climate.{your_device_name}`

Controls Zone 1 heating/cooling:

- Set target temperature
- Change HVAC mode (heat, cool, auto, off)
- View current room temperature

### Hot Water Control

| Entity                                | Type   | Description                   | Control                  |
| ------------------------------------- | ------ | ----------------------------- | ------------------------ |
| `sensor.{device}_tank_temperature`    | Sensor | Current hot water temperature | Read-only                |
| `number.{device}_tank_water_setpoint` | Number | Hot water target temperature  | **Adjustable** (40-60°C) |
| `switch.{device}_forced_hot_water`    | Switch | Force hot water heating now   | **Toggle ON/OFF**        |
| `switch.{device}_prohibit_hot_water`  | Switch | Block hot water heating       | **Toggle ON/OFF**        |

### Zone Information

**Zone 1 (Main Zone)**:

- `sensor.{device}_zone1_operation_mode` - Current operation mode

**Zone 2 (If Available)**:

- `sensor.{device}_zone2_temperature` - Current temperature
- `sensor.{device}_zone2_target_temperature` - Target temperature
- `sensor.{device}_zone2_operation_mode` - Current operation mode

### System Status

| Entity                                | Type          | Description                   |
| ------------------------------------- | ------------- | ----------------------------- |
| `sensor.{device}_operation_mode`      | Sensor        | Overall device operation mode |
| `binary_sensor.{device}_standby_mode` | Binary Sensor | Device in standby             |
| `binary_sensor.{device}_error`        | Binary Sensor | Error indicator               |
| `sensor.{device}_error_code`          | Sensor        | Error code if any             |

### Device Capabilities

| Entity                                    | Type          | Description             |
| ----------------------------------------- | ------------- | ----------------------- |
| `binary_sensor.{device}_has_zone2`        | Binary Sensor | Device has second zone  |
| `binary_sensor.{device}_has_cooling_mode` | Binary Sensor | Device supports cooling |

## Example Automations

### Boost Hot Water Before Morning Shower

```yaml
automation:
  - alias: "Morning Hot Water Boost"
    trigger:
      - platform: time
        at: "06:00:00"
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.heat_pump_forced_hot_water
      - delay: "01:00:00"
      - service: switch.turn_off
        target:
          entity_id: switch.heat_pump_forced_hot_water
```

### Set Tank Temperature Based on Outside Temperature

```yaml
automation:
  - alias: "Adjust Tank Temperature"
    trigger:
      - platform: numeric_state
        entity_id: sensor.outside_temperature
        below: 5
    action:
      - service: number.set_value
        target:
          entity_id: number.heat_pump_tank_water_setpoint
        data:
          value: 55
```

### Alert on Error State

```yaml
automation:
  - alias: "Heat Pump Error Alert"
    trigger:
      - platform: state
        entity_id: binary_sensor.heat_pump_error
        to: "on"
    action:
      - service: notify.mobile_app
        data:
          title: "Heat Pump Error"
          message: "Error code: {{ states('sensor.heat_pump_error_code') }}"
```

### Summer Mode - Disable Heating, Hot Water Only

```yaml
automation:
  - alias: "Summer Mode"
    trigger:
      - platform: time
        at: "00:00:00"
    condition:
      - condition: numeric_state
        entity_id: sensor.outside_temperature
        above: 20
    action:
      - service: climate.set_hvac_mode
        target:
          entity_id: climate.heat_pump
        data:
          hvac_mode: "off"
```

## Lovelace Dashboard Example

```yaml
type: entities
title: Heat Pump Control
entities:
  - entity: climate.heat_pump
  - type: divider
  - entity: sensor.heat_pump_tank_temperature
    name: Tank Temperature
  - entity: number.heat_pump_tank_water_setpoint
    name: Tank Setpoint
  - entity: switch.heat_pump_forced_hot_water
    name: Boost Hot Water
  - type: divider
  - entity: sensor.heat_pump_operation_mode
  - entity: binary_sensor.heat_pump_standby_mode
  - entity: binary_sensor.heat_pump_error
```

## Tips

1. **Tank Temperature Range**: 40-60°C is the safe operating range
2. **Forced Hot Water**: Use sparingly - it prioritizes hot water over heating
3. **Prohibit Hot Water**: Useful for vacation mode or when maintenance is needed
4. **Error Monitoring**: Set up notifications for error states
5. **Zone 2**: Only appears if your system has a second heating zone

## Troubleshooting

### Entities Not Appearing

- Check that your device type is "atwunit" (ATW heat pump)
- Restart Home Assistant after the bridge starts
- Check MQTT broker logs

### Commands Not Working

- Verify MQTT broker is running and accessible
- Check MELCloud authentication is valid
- Look at bridge logs: `docker logs melcloudhome-bridge`

### Values Not Updating

- Default poll interval is 60 seconds
- Check device is online in MELCloud app
- Verify network connectivity
