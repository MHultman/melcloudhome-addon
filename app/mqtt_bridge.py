"""MQTT Bridge for Home Assistant integration."""

import asyncio
import json
from typing import Optional, Dict, Any, Callable
from loguru import logger
import paho.mqtt.client as mqtt

from app.models import ClimateDevice
from app.utils import sanitize_mqtt_topic


class MQTTBridge:
    """
    MQTT Bridge for publishing device discovery and state updates.
    
    Handles:
    - Connection management with auto-reconnect
    - Home Assistant MQTT Discovery
    - State publishing
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
    
    async def connect(self) -> None:
        """
        Connect to MQTT broker with error handling.
        
        Raises:
            ConnectionError: If connection fails
        """
        self._logger.info(f"Connecting to MQTT broker at {self.host}:{self.port}")
        
        try:
            # Create MQTT client
            self._client = mqtt.Client(
                client_id="melcloud_home_bridge",
                protocol=mqtt.MQTTv311
            )
            
            # Configure authentication
            if self.username and self.password:
                self._client.username_pw_set(self.username, self.password)
            
            # Configure last will and testament (availability)
            self._client.will_set(
                f"{self.base_topic}/bridge/status",
                payload="offline",
                qos=1,
                retain=True
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
            for _ in range(50):  # 5 seconds max
                if self._connected:
                    break
                await asyncio.sleep(0.1)
            
            if not self._connected:
                raise ConnectionError("Failed to establish MQTT connection within timeout")
            
            self._logger.info("MQTT connection established")
            
            # Publish bridge status as online
            await self.publish(
                f"{self.base_topic}/bridge/status",
                "online",
                retain=True
            )
            
        except Exception as e:
            self._logger.error(f"MQTT connection failed: {e}")
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
        self._connected = False
        
        if rc != 0:
            self._logger.warning(f"Unexpected MQTT disconnection (code {rc}), will auto-reconnect")
        else:
            self._logger.info("MQTT disconnected cleanly")
    
    def _on_message(self, client, userdata, msg):
        """Callback when message received from MQTT broker."""
        topic = msg.topic
        payload = msg.payload.decode('utf-8')
        
        self._logger.debug(f"MQTT message received: {topic} = {payload}")
        
        # Dispatch to registered callback if exists
        if topic in self._command_callbacks:
            try:
                self._command_callbacks[topic](topic, payload)
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
            "temperature_command_topic": f"{self.base_topic}/climate/{device_id_sanitized}/set_temperature",
            "mode_state_topic": f"{self.base_topic}/climate/{device_id_sanitized}/state",
            "mode_command_topic": f"{self.base_topic}/climate/{device_id_sanitized}/set_mode",
            "availability_topic": f"{self.base_topic}/climate/{device_id_sanitized}/availability",
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
        
        # Publish state (not retained - changes frequently)
        await self.publish(
            state_topic,
            json.dumps(state_payload),
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
        
        Args:
            topic: MQTT topic
            payload: Message payload (string or JSON)
            retain: Whether to retain the message
        """
        if not self._client or not self._connected:
            self._logger.warning(f"Cannot publish to {topic}: not connected")
            return
        
        assert self._client is not None, "MQTT client should be initialized"
        
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self._client.publish(topic, payload, qos=1, retain=retain)  # type: ignore[union-attr]
            )
        except Exception as e:
            self._logger.error(f"Failed to publish to {topic}: {e}")
    
    async def subscribe_to_commands(self, device: ClimateDevice, callback: Callable) -> None:
        """
        Subscribe to command topics for a device.
        
        Args:
            device: ClimateDevice to subscribe commands for
            callback: Callback function(topic, payload) to handle commands
        """
        device_id_sanitized = sanitize_mqtt_topic(device.device_id)
        
        # Subscribe to temperature commands
        temp_topic = f"{self.base_topic}/climate/{device_id_sanitized}/set_temperature"
        await self._subscribe(temp_topic, callback)
        
        # Subscribe to mode commands
        mode_topic = f"{self.base_topic}/climate/{device_id_sanitized}/set_mode"
        await self._subscribe(mode_topic, callback)
        
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
