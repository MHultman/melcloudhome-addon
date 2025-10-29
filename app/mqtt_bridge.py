"""MQTT Bridge for Home Assistant integration."""

import asyncio
import json
from typing import Optional, Dict, Callable, List, Tuple
from loguru import logger
import paho.mqtt.client as mqtt

from app.models import ClimateDevice
from app.utils import sanitize_mqtt_topic, ExponentialBackoff


class MQTTBridge:
    """
    MQTT Bridge for publishing device discovery and state updates.
    
    Handles:
    - Connection management with auto-reconnect and exponential backoff
    - Home Assistant MQTT Discovery
    - State publishing with queuing during disconnection
    - Command subscription
    - Availability tracking
    """
    
    def __init__(
        self,
        host: str,
        port: int = 1883,
        username: Optional[str] = None,
        password: Optional[str] = None,
        base_topic: str = "homeassistant"
    ):
        """
        Initialize MQTT bridge.
        
        Args:
            host: MQTT broker hostname
            port: MQTT broker port
            username: Optional MQTT username
            password: Optional MQTT password
            base_topic: Base topic for Home Assistant discovery
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.base_topic = base_topic.rstrip("/")
        
        self._client: Optional[mqtt.Client] = None
        self._connected = False
        self._logger = logger.bind(component="mqtt_bridge")
        self._command_callbacks: Dict[str, Callable] = {}
        self._reconnect_task: Optional[asyncio.Task] = None
        
        # Resilience features
        self._backoff = ExponentialBackoff(
            initial_delay=1.0,
            max_delay=60.0,
            multiplier=2.0
        )
        self._message_queue: List[Tuple[str, str, bool]] = []  # (topic, payload, retain)
        self._max_queue_size = 100
        self._last_discovery_devices: List[ClimateDevice] = []
        self._connection_state_callbacks: List[Callable] = []
    
    async def connect(self) -> None:
        """
        Connect to MQTT broker with error handling.
        
        Raises:
            ConnectionError: If connection fails
        """
        self._logger.info(
            f"Connecting to MQTT broker at {self.host}:{self.port}",
            extra={"operation": "mqtt_connect", "host": self.host, "port": self.port}
        )
        self._logger.debug(
            f"MQTT configuration: base_topic={self.base_topic}, username={'***' if self.username else None}",
            extra={"operation": "mqtt_connect"}
        )
        
        try:
            import time
            start_time = time.time()
            
            # Create MQTT client
            self._client = mqtt.Client(
                client_id="melcloud_home_bridge",
                protocol=mqtt.MQTTv311
            )
            
            # Configure authentication
            if self.username and self.password:
                self._client.username_pw_set(self.username, self.password)
                self._logger.debug(
                    "MQTT authentication configured",
                    extra={"operation": "mqtt_connect"}
                )
            
            # Configure last will and testament (availability)
            self._client.will_set(
                f"{self.base_topic}/bridge/status",
                payload="offline",
                qos=1,
                retain=True
            )
            self._logger.debug(
                "MQTT last will and testament configured",
                extra={"operation": "mqtt_connect"}
            )
            
            # Set up callbacks
            self._client.on_connect = self._on_connect
            self._client.on_disconnect = self._on_disconnect
            self._client.on_message = self._on_message
            
            # Connect (blocking call)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self._client.connect,
                self.host,
                self.port,
                60  # keepalive
            )
            
            # Start network loop in background
            self._client.loop_start()
            
            # Wait for connection to be established
            for attempt in range(50):  # 5 seconds max
                if self._connected:
                    break
                await asyncio.sleep(0.1)
            
            duration = time.time() - start_time
            
            if not self._connected:
                error_msg = "Failed to establish MQTT connection within timeout"
                self._logger.error(
                    error_msg,
                    extra={
                        "operation": "mqtt_connect",
                        "duration_seconds": f"{duration:.2f}",
                        "resolution": "Check MQTT broker is running and accessible"
                    }
                )
                raise ConnectionError(error_msg)
            
            self._logger.info(
                "MQTT connection established",
                extra={"operation": "mqtt_connect", "duration_seconds": f"{duration:.2f}"}
            )
            
            # Publish bridge status as online
            await self.publish(
                f"{self.base_topic}/bridge/status",
                "online",
                retain=True
            )
            self._logger.debug(
                "Published bridge online status",
                extra={"operation": "mqtt_connect"}
            )
            
        except Exception as e:
            self._logger.error(
                f"MQTT connection failed: {e}",
                extra={
                    "operation": "mqtt_connect",
                    "host": self.host,
                    "port": self.port,
                    "error_type": type(e).__name__,
                    "resolution": "Verify MQTT broker address, port, and credentials"
                }
            )
            raise ConnectionError(f"Failed to connect to MQTT broker: {e}") from e
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback when connected to MQTT broker."""
        if rc == 0:
            self._connected = True
            self._logger.info("MQTT connected successfully")
        else:
            error_msgs = {
                1: "Incorrect protocol version",
                2: "Invalid client identifier",
                3: "Server unavailable",
                4: "Bad username or password",
                5: "Not authorized"
            }
            error_msg = error_msgs.get(rc, f"Unknown error code {rc}")
            self._logger.error(f"MQTT connection failed: {error_msg}")
            self._connected = False
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback when disconnected from MQTT broker."""
        was_connected = self._connected
        self._connected = False
        
        if rc != 0:
            self._logger.warning(f"Unexpected MQTT disconnection (code {rc}), will auto-reconnect")
            # Trigger automatic reconnection
            if was_connected and not self._reconnect_task:
                # Schedule reconnection in the event loop
                try:
                    loop = asyncio.get_event_loop()
                    self._reconnect_task = loop.create_task(self._auto_reconnect())
                except RuntimeError:
                    self._logger.error("Cannot schedule reconnection: no event loop running")
        else:
            self._logger.info("MQTT disconnected cleanly")
        
        # Notify connection state callbacks
        for callback in self._connection_state_callbacks:
            try:
                callback(False)  # disconnected
            except Exception as e:
                self._logger.error(f"Error in connection state callback: {e}")
    
    async def _auto_reconnect(self) -> None:
        """
        Automatic reconnection with exponential backoff.
        
        Attempts to reconnect indefinitely with increasing delays between attempts.
        """
        self._logger.info("Starting automatic MQTT reconnection...")
        attempt = 0
        
        while not self._connected:
            attempt += 1
            delay = self._backoff.get_delay()
            
            self._logger.info(
                f"Attempting MQTT reconnection (attempt {attempt}) after {delay:.1f}s delay..."
            )
            await asyncio.sleep(delay)
            
            try:
                # Attempt to connect
                await self.connect()
                
                if self._connected:
                    self._logger.info("MQTT reconnection successful")
                    self._backoff.reset()
                    
                    # Republish discovery messages
                    await self._republish_discovery()
                    
                    # Republish availability messages
                    await self._republish_availability()
                    
                    # Flush message queue
                    await self._flush_message_queue()
                    
                    break
                    
            except Exception as e:
                self._logger.warning(f"MQTT reconnection attempt {attempt} failed: {e}")
                # Continue loop to retry
        
        self._reconnect_task = None
    
    async def _republish_discovery(self) -> None:
        """Republish MQTT Discovery messages after reconnection."""
        if not self._last_discovery_devices:
            return
        
        self._logger.info(
            f"Republishing discovery messages for {len(self._last_discovery_devices)} devices"
        )
        
        for device in self._last_discovery_devices:
            try:
                await self.publish_discovery(device)
            except Exception as e:
                self._logger.error(f"Failed to republish discovery for {device.device_name}: {e}")
    
    async def _republish_availability(self) -> None:
        """Republish availability messages after reconnection."""
        if not self._last_discovery_devices:
            return
        
        self._logger.info(
            f"Republishing availability for {len(self._last_discovery_devices)} devices"
        )
        
        for device in self._last_discovery_devices:
            try:
                await self.publish_availability(device, available=True)
            except Exception as e:
                self._logger.error(f"Failed to republish availability for {device.device_name}: {e}")
    
    async def _flush_message_queue(self) -> None:
        """Flush queued messages after reconnection."""
        if not self._message_queue:
            return
        
        self._logger.info(f"Flushing {len(self._message_queue)} queued MQTT messages")
        
        while self._message_queue:
            topic, payload, retain = self._message_queue.pop(0)
            try:
                await self.publish(topic, payload, retain=retain)
            except Exception as e:
                self._logger.error(f"Failed to publish queued message to {topic}: {e}")
                # Re-queue if still not connected
                if not self._connected:
                    self._message_queue.insert(0, (topic, payload, retain))
                    break
    
    def add_connection_state_callback(self, callback: Callable) -> None:
        """
        Register callback for connection state changes.
        
        Args:
            callback: Function(is_connected: bool) to call on state change
        """
        self._connection_state_callbacks.append(callback)
    
    def _on_message(self, client, userdata, msg):
        """Callback when message received from MQTT broker."""
        topic = msg.topic
        payload = msg.payload.decode('utf-8')
        
        self._logger.debug(f"MQTT message received: {topic} = {payload}")
        
        # Dispatch to registered callback if exists
        if topic in self._command_callbacks:
            try:
                callback = self._command_callbacks[topic]
                # If callback is a coroutine function, schedule it in the event loop
                if asyncio.iscoroutinefunction(callback):
                    try:
                        loop = asyncio.get_event_loop()
                        loop.create_task(callback(topic, payload))
                    except RuntimeError:
                        # No event loop, try to get running loop
                        try:
                            loop = asyncio.get_running_loop()
                            loop.create_task(callback(topic, payload))
                        except RuntimeError:
                            self._logger.error(f"No event loop available to handle async callback for {topic}")
                else:
                    # Synchronous callback
                    callback(topic, payload)
            except Exception as e:
                self._logger.error(f"Error handling MQTT message on {topic}: {e}")

    
    async def disconnect(self) -> None:
        """Gracefully disconnect from MQTT broker."""
        if not self._client:
            return
        
        self._logger.info("Disconnecting from MQTT broker")
        
        try:
            # Publish offline status
            if self._connected:
                await self.publish(
                    f"{self.base_topic}/bridge/status",
                    "offline",
                    retain=True
                )
            
            # Stop network loop
            self._client.loop_stop()
            
            # Disconnect
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._client.disconnect)
            
            self._connected = False
            self._logger.info("MQTT disconnected")
            
        except Exception as e:
            self._logger.error(f"Error during MQTT disconnect: {e}")
    
    async def publish_discovery(self, device: ClimateDevice) -> None:
        """
        Publish Home Assistant MQTT Discovery message for a climate device.
        
        Args:
            device: ClimateDevice to publish discovery for
        """
        # Cache device for republishing on reconnection
        if device not in self._last_discovery_devices:
            self._last_discovery_devices.append(device)
        
        # Sanitize device ID for topic usage
        device_id_sanitized = sanitize_mqtt_topic(device.device_id)
        
        # Discovery topic: <base_topic>/climate/<device_id>/config
        discovery_topic = f"{self.base_topic}/climate/{device_id_sanitized}/config"
        
        # Build discovery payload
        discovery_payload = {
            "name": device.device_name,
            "unique_id": f"melcloud_{device_id_sanitized}",
            "device": {
                "identifiers": [f"melcloud_{device_id_sanitized}"],
                "name": device.device_name,
                "manufacturer": "Mitsubishi Electric",
                "model": device.device_type.upper(),
                "sw_version": "1.0.0"  # TODO: Get from device if available
            },
            "modes": self._get_modes_for_device(device),
            "current_temperature_topic": f"{self.base_topic}/climate/{device_id_sanitized}/state",
            "current_temperature_template": "{{ value_json.current_temperature }}",
            "temperature_state_topic": f"{self.base_topic}/climate/{device_id_sanitized}/state",
            "temperature_state_template": "{{ value_json.temperature }}",
            "temperature_command_topic": f"{self.base_topic}/climate/{device_id_sanitized}/set_temperature",
            "mode_state_topic": f"{self.base_topic}/climate/{device_id_sanitized}/state",
            "mode_state_template": "{{ value_json.mode }}",
            "mode_command_topic": f"{self.base_topic}/climate/{device_id_sanitized}/set_mode",
            "availability_topic": f"{self.base_topic}/climate/{device_id_sanitized}/availability",
            "json_attributes_topic": f"{self.base_topic}/climate/{device_id_sanitized}/state",
            "temperature_unit": "C",
            "min_temp": 16.0,
            "max_temp": 31.0,
            "temp_step": 0.5
        }
        
        # Publish discovery message (retained)
        await self.publish(
            discovery_topic,
            json.dumps(discovery_payload),
            retain=True
        )
        
        self._logger.info(f"Published MQTT discovery for {device.device_name}")
        
        # Publish additional sensors for ATW devices
        if device.device_type == "atwunit":
            await self._publish_atw_sensors(device)
            await self._publish_atw_controls(device)
    
    async def _publish_atw_sensors(self, device: ClimateDevice) -> None:
        """
        Publish additional sensor discoveries for ATW devices.
        
        ATW devices have extra data points that should be exposed as separate sensors:
        - Tank water temperature (current)
        - Tank water temperature (target)
        - Zone operation modes
        - Error states
        - Additional status flags
        
        Args:
            device: ATW ClimateDevice
        """
        device_id_sanitized = sanitize_mqtt_topic(device.device_id)
        state_topic = f"{self.base_topic}/climate/{device_id_sanitized}/state"
        availability_topic = f"{self.base_topic}/climate/{device_id_sanitized}/availability"
        
        # Device info (shared across all sensors)
        device_info = {
            "identifiers": [f"melcloud_{device_id_sanitized}"],
            "name": device.device_name,
            "manufacturer": "Mitsubishi Electric",
            "model": device.device_type.upper(),
            "sw_version": "1.0.0"
        }
        
        # Tank Water Temperature (Current)
        await self.publish(
            f"{self.base_topic}/sensor/{device_id_sanitized}_tank_temp/config",
            json.dumps({
                "name": f"{device.device_name} Tank Temperature",
                "unique_id": f"melcloud_{device_id_sanitized}_tank_temp",
                "device": device_info,
                "state_topic": state_topic,
                "value_template": "{{ value_json.tank_temperature }}",
                "availability_topic": availability_topic,
                "unit_of_measurement": "°C",
                "device_class": "temperature",
                "state_class": "measurement",
            }),
            retain=True
        )
        
        # Tank Water Temperature (Target/Setpoint)
        await self.publish(
            f"{self.base_topic}/sensor/{device_id_sanitized}_tank_target/config",
            json.dumps({
                "name": f"{device.device_name} Tank Target Temperature",
                "unique_id": f"melcloud_{device_id_sanitized}_tank_target",
                "device": device_info,
                "state_topic": state_topic,
                "value_template": "{{ value_json.tank_target_temperature }}",
                "availability_topic": availability_topic,
                "unit_of_measurement": "°C",
                "device_class": "temperature",
                "state_class": "measurement",
            }),
            retain=True
        )
        
        # Zone 1 Operation Mode
        await self.publish(
            f"{self.base_topic}/sensor/{device_id_sanitized}_zone1_mode/config",
            json.dumps({
                "name": f"{device.device_name} Zone 1 Operation Mode",
                "unique_id": f"melcloud_{device_id_sanitized}_zone1_mode",
                "device": device_info,
                "state_topic": state_topic,
                "value_template": "{{ value_json.operation_mode_zone1 }}",
                "availability_topic": availability_topic,
                "icon": "mdi:home-thermometer",
            }),
            retain=True
        )
        
        # Forced Hot Water Mode (Binary Sensor)
        await self.publish(
            f"{self.base_topic}/binary_sensor/{device_id_sanitized}_forced_hw/config",
            json.dumps({
                "name": f"{device.device_name} Forced Hot Water",
                "unique_id": f"melcloud_{device_id_sanitized}_forced_hw",
                "device": device_info,
                "state_topic": state_topic,
                "value_template": "{{ 'ON' if value_json.forced_hot_water else 'OFF' }}",
                "availability_topic": availability_topic,
                "payload_on": "ON",
                "payload_off": "OFF",
                "icon": "mdi:water-boiler",
            }),
            retain=True
        )
        
        # Prohibit Hot Water (Binary Sensor)
        await self.publish(
            f"{self.base_topic}/binary_sensor/{device_id_sanitized}_prohibit_hw/config",
            json.dumps({
                "name": f"{device.device_name} Prohibit Hot Water",
                "unique_id": f"melcloud_{device_id_sanitized}_prohibit_hw",
                "device": device_info,
                "state_topic": state_topic,
                "value_template": "{{ 'ON' if value_json.prohibit_hot_water else 'OFF' }}",
                "availability_topic": availability_topic,
                "payload_on": "ON",
                "payload_off": "OFF",
                "icon": "mdi:water-off",
            }),
            retain=True
        )
        
        # In Standby Mode (Binary Sensor)
        await self.publish(
            f"{self.base_topic}/binary_sensor/{device_id_sanitized}_standby/config",
            json.dumps({
                "name": f"{device.device_name} Standby Mode",
                "unique_id": f"melcloud_{device_id_sanitized}_standby",
                "device": device_info,
                "state_topic": state_topic,
                "value_template": "{{ 'ON' if value_json.in_standby else 'OFF' }}",
                "availability_topic": availability_topic,
                "payload_on": "ON",
                "payload_off": "OFF",
                "icon": "mdi:sleep",
            }),
            retain=True
        )
        
        # Error State (Binary Sensor)
        await self.publish(
            f"{self.base_topic}/binary_sensor/{device_id_sanitized}_error/config",
            json.dumps({
                "name": f"{device.device_name} Error",
                "unique_id": f"melcloud_{device_id_sanitized}_error",
                "device": device_info,
                "state_topic": state_topic,
                "value_template": "{{ 'ON' if value_json.error else 'OFF' }}",
                "availability_topic": availability_topic,
                "payload_on": "ON",
                "payload_off": "OFF",
                "device_class": "problem",
            }),
            retain=True
        )
        
        # Error Code (Sensor - only if error exists)
        await self.publish(
            f"{self.base_topic}/sensor/{device_id_sanitized}_error_code/config",
            json.dumps({
                "name": f"{device.device_name} Error Code",
                "unique_id": f"melcloud_{device_id_sanitized}_error_code",
                "device": device_info,
                "state_topic": state_topic,
                "value_template": "{{ value_json.error_code if value_json.error else 'None' }}",
                "availability_topic": availability_topic,
                "icon": "mdi:alert-circle",
            }),
            retain=True
        )
        
        self._logger.info(f"Published ATW sensor discoveries for {device.device_name}")
    
    async def _publish_atw_controls(self, device: ClimateDevice) -> None:
        """
        Publish control entity discoveries for ATW devices.
        
        These entities allow users to control device settings from Home Assistant:
        - Power switch
        - Tank water temperature setpoint
        - Forced hot water mode switch
        - Zone 1 temperature setpoint
        - Zone 1 operation mode select
        - Zone 1 heat/cool flow temperatures
        - Zone 2 controls (if supported)
        
        Args:
            device: ATW ClimateDevice
        """
        device_id_sanitized = sanitize_mqtt_topic(device.device_id)
        availability_topic = f"{self.base_topic}/climate/{device_id_sanitized}/availability"
        
        # Device info (shared across all entities)
        device_info = {
            "identifiers": [f"melcloud_{device_id_sanitized}"],
            "name": device.device_name,
            "manufacturer": "Mitsubishi Electric",
            "model": device.device_type.upper(),
            "sw_version": "1.0.0"
        }
        
        # Get device capabilities for validation
        capabilities = device.state.get("Capabilities", {})
        has_hot_water = capabilities.get("hasHotWater", False)
        has_zone2 = capabilities.get("hasZone2", False)
        min_temp = capabilities.get("minSetTemperature", 16)
        max_temp = capabilities.get("maxSetTemperature", 30)
        temp_step = capabilities.get("temperatureIncrement", 0.5)
        min_tank_temp = capabilities.get("minSetTankTemperature", 40)
        max_tank_temp = capabilities.get("maxSetTankTemperature", 60)
        
        # Power Switch
        await self.publish(
            f"{self.base_topic}/switch/{device_id_sanitized}_power/config",
            json.dumps({
                "name": f"{device.device_name} Power",
                "unique_id": f"melcloud_{device_id_sanitized}_power",
                "device": device_info,
                "state_topic": f"{self.base_topic}/climate/{device_id_sanitized}/state",
                "value_template": "{{ 'ON' if value_json.power else 'OFF' }}",
                "command_topic": f"{self.base_topic}/climate/{device_id_sanitized}/set_power",
                "availability_topic": availability_topic,
                "payload_on": "ON",
                "payload_off": "OFF",
                "icon": "mdi:power",
            }),
            retain=True
        )
        
        # Zone 1 Temperature Setpoint (Number)
        await self.publish(
            f"{self.base_topic}/number/{device_id_sanitized}_zone1_temp/config",
            json.dumps({
                "name": f"{device.device_name} Zone 1 Temperature",
                "unique_id": f"melcloud_{device_id_sanitized}_zone1_temp",
                "device": device_info,
                "state_topic": f"{self.base_topic}/climate/{device_id_sanitized}/state",
                "value_template": "{{ value_json.set_temperature_zone1 }}",
                "command_topic": f"{self.base_topic}/climate/{device_id_sanitized}/set_zone1_temperature",
                "availability_topic": availability_topic,
                "min": min_temp,
                "max": max_temp,
                "step": temp_step,
                "unit_of_measurement": "°C",
                "device_class": "temperature",
                "mode": "slider",
            }),
            retain=True
        )
        
        # Zone 1 Operation Mode (Select)
        await self.publish(
            f"{self.base_topic}/select/{device_id_sanitized}_zone1_op_mode/config",
            json.dumps({
                "name": f"{device.device_name} Zone 1 Operation Mode",
                "unique_id": f"melcloud_{device_id_sanitized}_zone1_op_mode",
                "device": device_info,
                "state_topic": f"{self.base_topic}/climate/{device_id_sanitized}/state",
                "value_template": "{{ value_json.operation_mode_zone1 }}",
                "command_topic": f"{self.base_topic}/climate/{device_id_sanitized}/set_zone1_operation_mode",
                "availability_topic": availability_topic,
                "options": ["HeatRoomTemperature", "HeatFlowTemperature", "HeatCurve"],
                "icon": "mdi:home-thermometer-outline",
            }),
            retain=True
        )
        
        # Zone 1 Heat Flow Temperature (Number)
        await self.publish(
            f"{self.base_topic}/number/{device_id_sanitized}_zone1_heat_flow/config",
            json.dumps({
                "name": f"{device.device_name} Zone 1 Heat Flow Temperature",
                "unique_id": f"melcloud_{device_id_sanitized}_zone1_heat_flow",
                "device": device_info,
                "state_topic": f"{self.base_topic}/climate/{device_id_sanitized}/state",
                "value_template": "{{ value_json.set_heat_flow_temperature_zone1 }}",
                "command_topic": f"{self.base_topic}/climate/{device_id_sanitized}/set_zone1_heat_flow_temperature",
                "availability_topic": availability_topic,
                "min": 20,
                "max": 60,
                "step": 1,
                "unit_of_measurement": "°C",
                "device_class": "temperature",
                "mode": "box",
            }),
            retain=True
        )
        
        # Zone 1 Cool Flow Temperature (Number)
        await self.publish(
            f"{self.base_topic}/number/{device_id_sanitized}_zone1_cool_flow/config",
            json.dumps({
                "name": f"{device.device_name} Zone 1 Cool Flow Temperature",
                "unique_id": f"melcloud_{device_id_sanitized}_zone1_cool_flow",
                "device": device_info,
                "state_topic": f"{self.base_topic}/climate/{device_id_sanitized}/state",
                "value_template": "{{ value_json.set_cool_flow_temperature_zone1 }}",
                "command_topic": f"{self.base_topic}/climate/{device_id_sanitized}/set_zone1_cool_flow_temperature",
                "availability_topic": availability_topic,
                "min": 5,
                "max": 25,
                "step": 1,
                "unit_of_measurement": "°C",
                "device_class": "temperature",
                "mode": "box",
            }),
            retain=True
        )
        
        # Hot Water Controls (only if supported)
        if has_hot_water:
            # Tank Water Temperature Setpoint (Number)
            await self.publish(
                f"{self.base_topic}/number/{device_id_sanitized}_tank_temp_set/config",
                json.dumps({
                    "name": f"{device.device_name} Tank Temperature Setpoint",
                    "unique_id": f"melcloud_{device_id_sanitized}_tank_temp_set",
                    "device": device_info,
                    "state_topic": f"{self.base_topic}/climate/{device_id_sanitized}/state",
                    "value_template": "{{ value_json.tank_target_temperature }}",
                    "command_topic": f"{self.base_topic}/climate/{device_id_sanitized}/set_tank_temperature",
                    "availability_topic": availability_topic,
                    "min": min_tank_temp,
                    "max": max_tank_temp,
                    "step": 1,
                    "unit_of_measurement": "°C",
                    "device_class": "temperature",
                    "mode": "slider",
                }),
                retain=True
            )
            
            # Forced Hot Water Mode (Switch)
            await self.publish(
                f"{self.base_topic}/switch/{device_id_sanitized}_forced_hw/config",
                json.dumps({
                    "name": f"{device.device_name} Forced Hot Water Mode",
                    "unique_id": f"melcloud_{device_id_sanitized}_forced_hw_switch",
                    "device": device_info,
                    "state_topic": f"{self.base_topic}/climate/{device_id_sanitized}/state",
                    "value_template": "{{ 'ON' if value_json.forced_hot_water else 'OFF' }}",
                    "command_topic": f"{self.base_topic}/climate/{device_id_sanitized}/set_forced_hot_water",
                    "availability_topic": availability_topic,
                    "payload_on": "ON",
                    "payload_off": "OFF",
                    "icon": "mdi:water-boiler-alert",
                }),
                retain=True
            )
        
        # Zone 2 Controls (only if supported)
        if has_zone2:
            # Zone 2 Temperature Setpoint
            await self.publish(
                f"{self.base_topic}/number/{device_id_sanitized}_zone2_temp/config",
                json.dumps({
                    "name": f"{device.device_name} Zone 2 Temperature",
                    "unique_id": f"melcloud_{device_id_sanitized}_zone2_temp",
                    "device": device_info,
                    "state_topic": f"{self.base_topic}/climate/{device_id_sanitized}/state",
                    "value_template": "{{ value_json.set_temperature_zone2 }}",
                    "command_topic": f"{self.base_topic}/climate/{device_id_sanitized}/set_zone2_temperature",
                    "availability_topic": availability_topic,
                    "min": min_temp,
                    "max": max_temp,
                    "step": temp_step,
                    "unit_of_measurement": "°C",
                    "device_class": "temperature",
                    "mode": "slider",
                }),
                retain=True
            )
            
            # Zone 2 Operation Mode
            await self.publish(
                f"{self.base_topic}/select/{device_id_sanitized}_zone2_op_mode/config",
                json.dumps({
                    "name": f"{device.device_name} Zone 2 Operation Mode",
                    "unique_id": f"melcloud_{device_id_sanitized}_zone2_op_mode",
                    "device": device_info,
                    "state_topic": f"{self.base_topic}/climate/{device_id_sanitized}/state",
                    "value_template": "{{ value_json.operation_mode_zone2 }}",
                    "command_topic": f"{self.base_topic}/climate/{device_id_sanitized}/set_zone2_operation_mode",
                    "availability_topic": availability_topic,
                    "options": ["HeatRoomTemperature", "HeatFlowTemperature", "HeatCurve"],
                    "icon": "mdi:home-thermometer-outline",
                }),
                retain=True
            )
            
            # Zone 2 Heat Flow Temperature
            await self.publish(
                f"{self.base_topic}/number/{device_id_sanitized}_zone2_heat_flow/config",
                json.dumps({
                    "name": f"{device.device_name} Zone 2 Heat Flow Temperature",
                    "unique_id": f"melcloud_{device_id_sanitized}_zone2_heat_flow",
                    "device": device_info,
                    "state_topic": f"{self.base_topic}/climate/{device_id_sanitized}/state",
                    "value_template": "{{ value_json.set_heat_flow_temperature_zone2 }}",
                    "command_topic": f"{self.base_topic}/climate/{device_id_sanitized}/set_zone2_heat_flow_temperature",
                    "availability_topic": availability_topic,
                    "min": 20,
                    "max": 60,
                    "step": 1,
                    "unit_of_measurement": "°C",
                    "device_class": "temperature",
                    "mode": "box",
                }),
                retain=True
            )
            
            # Zone 2 Cool Flow Temperature
            await self.publish(
                f"{self.base_topic}/number/{device_id_sanitized}_zone2_cool_flow/config",
                json.dumps({
                    "name": f"{device.device_name} Zone 2 Cool Flow Temperature",
                    "unique_id": f"melcloud_{device_id_sanitized}_zone2_cool_flow",
                    "device": device_info,
                    "state_topic": f"{self.base_topic}/climate/{device_id_sanitized}/state",
                    "value_template": "{{ value_json.set_cool_flow_temperature_zone2 }}",
                    "command_topic": f"{self.base_topic}/climate/{device_id_sanitized}/set_zone2_cool_flow_temperature",
                    "availability_topic": availability_topic,
                    "min": 5,
                    "max": 25,
                    "step": 1,
                    "unit_of_measurement": "°C",
                    "device_class": "temperature",
                    "mode": "box",
                }),
                retain=True
            )
        
        self._logger.info(f"Published ATW control entity discoveries for {device.device_name}")
    
    def _get_modes_for_device(self, device: ClimateDevice) -> list:
        """
        Get available modes for device type.
        
        Args:
            device: ClimateDevice instance
            
        Returns:
            List of available mode strings
        """
        # Default modes for all devices
        modes = ["off", "heat", "cool", "auto", "dry", "fan_only"]
        
        # ATW devices may have limited modes
        if device.device_type == "atwunit":
            # Check if cooling is supported
            has_cooling = device.state.get("HasCoolingMode") == "True"
            if not has_cooling:
                modes = ["off", "heat", "auto"]
        
        return modes
    
    async def publish_state(self, device: ClimateDevice) -> None:
        """
        Publish device state update to MQTT.
        
        Args:
            device: ClimateDevice with current state
        """
        device_id_sanitized = sanitize_mqtt_topic(device.device_id)
        state_topic = f"{self.base_topic}/climate/{device_id_sanitized}/state"
        
        # Convert device state to MQTT payload
        state_payload = device.to_mqtt_state()
        
        # DEBUG: Log the payload being published
        self._logger.debug(
            f"Publishing state to MQTT for {device.device_name}",
            extra={
                "device_id": device.device_id,
                "topic": state_topic,
                "payload_keys": list(state_payload.keys()),
                "power": state_payload.get("power"),
                "temperature": state_payload.get("temperature"),
                "current_temperature": state_payload.get("current_temperature"),
                "available": state_payload.get("available")
            }
        )
        
        payload_json = json.dumps(state_payload)
        self._logger.debug(
            f"MQTT payload JSON for {device.device_name}: {payload_json}",
            extra={
                "device_id": device.device_id,
                "topic": state_topic,
                "payload_size": len(payload_json)
            }
        )
        
        # Publish state (not retained - changes frequently)
        await self.publish(
            state_topic,
            payload_json,
            retain=False
        )
        
        self._logger.debug(f"Published state for {device.device_name}")
    
    async def publish_availability(self, device: ClimateDevice, available: bool) -> None:
        """
        Publish device availability status.
        
        Args:
            device: ClimateDevice instance
            available: Whether device is online/available
        """
        device_id_sanitized = sanitize_mqtt_topic(device.device_id)
        availability_topic = f"{self.base_topic}/climate/{device_id_sanitized}/availability"
        
        payload = "online" if available else "offline"
        
        # Publish availability (retained)
        await self.publish(
            availability_topic,
            payload,
            retain=True
        )
        
        self._logger.debug(f"Published availability for {device.device_name}: {payload}")
    
    async def publish(self, topic: str, payload: str, retain: bool = False) -> None:
        """
        Publish a message to MQTT broker.
        
        If disconnected, queues the message for delivery after reconnection.
        
        Args:
            topic: MQTT topic
            payload: Message payload (string or JSON)
            retain: Whether to retain the message
        """
        if not self._client or not self._connected:
            # Queue message for later delivery
            if len(self._message_queue) < self._max_queue_size:
                self._message_queue.append((topic, payload, retain))
                self._logger.debug(
                    f"Queued message for {topic} (queue size: {len(self._message_queue)})",
                    extra={
                        "operation": "mqtt_publish",
                        "topic": topic,
                        "queued": True,
                        "queue_size": len(self._message_queue)
                    }
                )
            else:
                self._logger.warning(
                    f"Message queue full ({self._max_queue_size}), dropping message for {topic}",
                    extra={
                        "operation": "mqtt_publish",
                        "topic": topic,
                        "queue_full": True,
                        "resolution": "Check MQTT connection status and reconnection attempts"
                    }
                )
            return
        
        assert self._client is not None, "MQTT client should be initialized"
        
        try:
            import time
            start_time = time.time()
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self._client.publish(topic, payload, qos=1, retain=retain)  # type: ignore[union-attr]
            )
            
            duration = time.time() - start_time
            
            self._logger.debug(
                f"Published to {topic}",
                extra={
                    "operation": "mqtt_publish",
                    "topic": topic,
                    "payload_length": len(payload),
                    "retain": retain,
                    "duration_seconds": f"{duration:.3f}"
                }
            )
        except Exception as e:
            self._logger.error(
                f"Failed to publish to {topic}: {e}",
                extra={
                    "operation": "mqtt_publish",
                    "topic": topic,
                    "error_type": type(e).__name__,
                    "resolution": "Check MQTT broker connectivity"
                }
            )
    
    async def subscribe_to_commands(self, device: ClimateDevice, callback: Callable) -> None:
        """
        Subscribe to command topics for a device.
        
        Args:
            device: ClimateDevice to subscribe commands for
            callback: Callback function(topic, payload) to handle commands
        """
        device_id_sanitized = sanitize_mqtt_topic(device.device_id)
        base_topic = f"{self.base_topic}/climate/{device_id_sanitized}"
        
        # Subscribe to standard climate entity commands
        await self._subscribe(f"{base_topic}/set_temperature", callback)
        await self._subscribe(f"{base_topic}/set_mode", callback)
        
        # Subscribe to ATW-specific control commands
        if device.device_type == "atwunit":
            # Power control
            await self._subscribe(f"{base_topic}/set_power", callback)
            
            # Zone 1 controls
            await self._subscribe(f"{base_topic}/set_zone1_temperature", callback)
            await self._subscribe(f"{base_topic}/set_zone1_operation_mode", callback)
            await self._subscribe(f"{base_topic}/set_zone1_heat_flow_temperature", callback)
            await self._subscribe(f"{base_topic}/set_zone1_cool_flow_temperature", callback)
            
            # Hot water controls (if supported)
            capabilities = device.state.get("capabilities", {})
            if isinstance(capabilities, dict) and capabilities.get("hasHotWater", False):
                await self._subscribe(f"{base_topic}/set_tank_temperature", callback)
                await self._subscribe(f"{base_topic}/set_forced_hot_water", callback)
            
            # Zone 2 controls (if supported)
            if isinstance(capabilities, dict) and capabilities.get("hasZone2", False):
                await self._subscribe(f"{base_topic}/set_zone2_temperature", callback)
                await self._subscribe(f"{base_topic}/set_zone2_operation_mode", callback)
                await self._subscribe(f"{base_topic}/set_zone2_heat_flow_temperature", callback)
                await self._subscribe(f"{base_topic}/set_zone2_cool_flow_temperature", callback)
        
        self._logger.info(f"Subscribed to commands for {device.device_name}")
    
    async def _subscribe(self, topic: str, callback: Callable) -> None:
        """Subscribe to an MQTT topic with callback."""
        if not self._client or not self._connected:
            self._logger.warning(f"Cannot subscribe to {topic}: not connected")
            return
        
        assert self._client is not None, "MQTT client should be initialized"
        
        try:
            # Register callback
            self._command_callbacks[topic] = callback
            
            # Subscribe
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self._client.subscribe(topic, qos=1)  # type: ignore[union-attr]
            )
            
            self._logger.debug(f"Subscribed to MQTT topic: {topic}")
        except Exception as e:
            self._logger.error(f"Failed to subscribe to {topic}: {e}")
    
    @property
    def is_connected(self) -> bool:
        """Check if MQTT client is connected."""
        return self._connected
