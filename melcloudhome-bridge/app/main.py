"""Main application entry point for MELCloud Home Bridge."""

import asyncio
import signal
import sys
import gc
import psutil  # type: ignore[import-untyped]
from typing import Optional, List, Dict
from datetime import datetime
from loguru import logger

from app import __version__
from app.config import load_configuration, Configuration
from app.logging_conf import setup_logging
from app.melcloud_client import MelCloudClient, LoginError, ApiError
from app.models import Credentials, ClimateDevice
from app.utils import ExponentialBackoff
from app.mqtt_bridge import MQTTBridge
from app.command_handler import CommandHandler
from app.health_server import HealthServer


class Application:
    """Main application orchestrator."""
    
    # Memory monitoring configuration
    MEMORY_WARNING_THRESHOLD_MB = 150
    MEMORY_CRITICAL_THRESHOLD_MB = 200
    CONNECTION_REFRESH_INTERVAL_HOURS = 24
    
    def __init__(self):
        """Initialize application."""
        self.config: Optional[Configuration] = None
        self.running = False
        self._shutdown_event = asyncio.Event()
        self.melcloud_client: Optional[MelCloudClient] = None
        self.mqtt_bridge: Optional[MQTTBridge] = None
        self.command_handler: Optional[CommandHandler] = None
        self.health_server: Optional[HealthServer] = None
        self.devices: List[ClimateDevice] = []
        self.device_states: Dict[str, Dict] = {}  # device_id -> last known state
        self.backoff = ExponentialBackoff()
        self._last_connection_refresh = datetime.now()
        self._process = psutil.Process()
    
    async def start(self) -> int:
        """
        Start the application.
        
        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        try:
            # Load configuration
            logger.info("Loading configuration...")
            self.config = load_configuration()
            
            # Setup logging with configured level
            setup_logging(self.config.log_level)
            
            # Display startup banner
            logger.info("=" * 60)
            logger.info(f"MELCloud Home Bridge v{__version__}")
            logger.info("=" * 60)
            logger.info("Starting MELCloud to Home Assistant bridge...")
            logger.info("")
            logger.info("Configuration Summary:")
            for key, value in self.config.get_safe_summary().items():
                logger.info(f"  {key}: {value}")
            logger.info("")
            logger.info("Features:")
            logger.info("  ✓ Automatic device discovery")
            logger.info("  ✓ Real-time state monitoring")
            logger.info("  ✓ Bidirectional control (HA ↔ MELCloud)")
            logger.info("  ✓ Network resilience with auto-reconnect")
            logger.info("  ✓ Health monitoring endpoint (port 8099)")
            logger.info("=" * 60)
            
            # Setup signal handlers
            self._setup_signal_handlers()
            
            # Initialize MELCloud client
            logger.info("Initializing MELCloud client...")
            credentials = Credentials(
                email=self.config.melcloud_email,
                password=self.config.melcloud_password
            )
            self.melcloud_client = MelCloudClient(credentials)
            
            # Authenticate with MELCloud
            try:
                await self.melcloud_client.authenticate()
            except LoginError as e:
                logger.error(f"Failed to authenticate with MELCloud: {e}")
                logger.error("Please verify your MELCloud credentials in the add-on configuration")
                return 1
            
            # Initialize MQTT bridge
            logger.info("Initializing MQTT bridge...")
            self.mqtt_bridge = MQTTBridge(
                host=self.config.mqtt_host,
                port=self.config.mqtt_port,
                username=self.config.mqtt_username,
                password=self.config.mqtt_password,
                base_topic=self.config.mqtt_base_topic
            )
            
            # Connect to MQTT broker
            try:
                await self.mqtt_bridge.connect()
            except ConnectionError as e:
                logger.error(f"Failed to connect to MQTT broker: {e}")
                logger.error("Please verify your MQTT broker configuration")
                return 1
            
            # Create command handler
            self.command_handler = CommandHandler(self.melcloud_client)
            logger.debug("Command handler initialized")
            
            # Start health server
            self.health_server = HealthServer(port=8099)
            await self.health_server.start()
            # Update initial health status
            self.health_server.update_melcloud_status(True)  # Authenticated
            self.health_server.update_mqtt_status(self.mqtt_bridge.is_connected)
            
            # Mark as running
            self.running = True
            logger.info("Application started successfully")
            
            # Start polling loop
            polling_task = asyncio.create_task(self._polling_loop())
            
            # Main event loop - wait for shutdown signal
            await self._shutdown_event.wait()
            
            # Cancel polling loop
            polling_task.cancel()
            try:
                await polling_task
            except asyncio.CancelledError:
                pass
            
            logger.info("Shutdown signal received")
            return 0
            
        except ValueError as e:
            logger.error(f"Configuration error: {e}")
            return 1
        except Exception as e:
            logger.exception(f"Fatal error during startup: {e}")
            return 1
        finally:
            await self.shutdown()
    
    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            """Handle shutdown signals."""
            sig_name = signal.Signals(signum).name
            logger.info(f"Received {sig_name} signal, initiating graceful shutdown...")
            self._shutdown_event.set()
        
        # Register signal handlers
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        logger.debug("Signal handlers registered (SIGTERM, SIGINT)")
    
    def _check_memory_usage(self) -> None:
        """
        Monitor memory usage and log warnings if thresholds exceeded.
        
        Triggers garbage collection if memory usage is high.
        """
        try:
            # Get current memory usage in MB
            mem_info = self._process.memory_info()
            memory_mb = mem_info.rss / 1024 / 1024
            
            if memory_mb > self.MEMORY_CRITICAL_THRESHOLD_MB:
                logger.error(
                    f"CRITICAL: Memory usage is {memory_mb:.1f} MB "
                    f"(threshold: {self.MEMORY_CRITICAL_THRESHOLD_MB} MB)"
                )
                # Force garbage collection
                collected = gc.collect()
                logger.info(f"Forced garbage collection: {collected} objects collected")
                
                # Log memory usage after GC
                mem_info_after = self._process.memory_info()
                memory_mb_after = mem_info_after.rss / 1024 / 1024
                logger.info(f"Memory after GC: {memory_mb_after:.1f} MB")
                
            elif memory_mb > self.MEMORY_WARNING_THRESHOLD_MB:
                logger.warning(
                    f"Memory usage is {memory_mb:.1f} MB "
                    f"(warning threshold: {self.MEMORY_WARNING_THRESHOLD_MB} MB)"
                )
                # Suggest garbage collection
                gc.collect()
            else:
                logger.debug(f"Memory usage: {memory_mb:.1f} MB")
        
        except Exception as e:
            logger.error(f"Failed to check memory usage: {e}")
    
    async def _periodic_connection_refresh(self) -> None:
        """
        Periodically refresh connections to prevent stale sessions.
        
        Runs every 24 hours to refresh MELCloud and MQTT connections.
        """
        try:
            time_since_refresh = datetime.now() - self._last_connection_refresh
            
            if time_since_refresh.total_seconds() >= (self.CONNECTION_REFRESH_INTERVAL_HOURS * 3600):
                logger.info("Performing periodic connection refresh (24h interval)")
                
                # Refresh MELCloud authentication
                if self.melcloud_client:
                    try:
                        await self.melcloud_client.authenticate()
                        logger.info("MELCloud session refreshed successfully")
                    except LoginError as e:
                        logger.error(f"Failed to refresh MELCloud session: {e}")
                
                # MQTT client has auto-reconnect, just verify connection
                if self.mqtt_bridge and not self.mqtt_bridge.is_connected:
                    logger.warning("MQTT connection lost, reconnection should happen automatically")
                
                self._last_connection_refresh = datetime.now()
                logger.info("Connection refresh complete")
        
        except Exception as e:
            logger.error(f"Error during periodic connection refresh: {e}")
    
    async def _polling_loop(self) -> None:
        """
        Main polling loop for device state updates.
        
        - First cycle: Discover devices
        - Subsequent cycles: Poll device states
        - Detect state changes
        - Apply exponential backoff on errors
        """
        assert self.melcloud_client is not None, "MELCloud client not initialized"
        assert self.config is not None, "Configuration not loaded"
        assert self.mqtt_bridge is not None, "MQTT bridge not initialized"
        
        logger.info("Starting polling loop...")
        poll_count = 0
        discovered = False
        
        while self.running:
            poll_start = asyncio.get_event_loop().time()
            
            try:
                # First poll cycle: Device discovery
                if not discovered:
                    logger.info("Discovering MELCloud devices...")
                    self.devices = await self.melcloud_client.list_devices()
                    logger.info(f"Discovered {len(self.devices)} devices")
                    
                    # Log device summary
                    for device in self.devices:
                        logger.info(
                            f"  - {device.device_name} ({device.device_type}) "
                            f"[ID: {device.device_id}] "
                            f"[Online: {device.online}]"
                        )
                    
                    # Publish MQTT Discovery for all devices
                    logger.info("Publishing MQTT discovery messages...")
                    for device in self.devices:
                        await self.mqtt_bridge.publish_discovery(device)
                        await self.mqtt_bridge.publish_availability(device, device.online)
                    
                    # Subscribe to command topics
                    logger.info("Subscribing to command topics...")
                    for device in self.devices:
                        # Create async wrapper for each device
                        async def command_callback(topic: str, payload: str, dev=device):
                            await self._handle_command(dev, topic, payload)
                        
                        await self.mqtt_bridge.subscribe_to_commands(
                            device,
                            command_callback
                        )
                    
                    discovered = True
                    
                    # Initialize device states and publish initial state
                    for device in self.devices:
                        self.device_states[device.device_id] = device.state.copy()
                        # Publish initial state to MQTT
                        await self.mqtt_bridge.publish_state(device)
                        logger.debug(f"Published initial state for {device.device_name}")
                
                # Poll device states
                state_changes = 0
                for device in self.devices:
                    try:
                        # Get current state
                        new_state = await self.melcloud_client.get_device_state(
                            device.device_id
                        )
                        
                        if new_state:
                            # Check for state changes
                            old_state = self.device_states.get(device.device_id, {})
                            if new_state != old_state:
                                state_changes += 1
                                logger.debug(
                                    f"State changed for {device.device_name} "
                                    f"[ID: {device.device_id}]"
                                )
                                # Update stored state
                                self.device_states[device.device_id] = new_state
                                # Update device object
                                device.state = new_state
                                device.online = True
                                
                                # Publish state change to MQTT
                                await self.mqtt_bridge.publish_state(device)
                            
                        else:
                            # Device unreachable
                            if device.online:
                                logger.warning(
                                    f"Device {device.device_name} is now offline"
                                )
                                device.online = False
                                # Publish unavailable status to MQTT
                                await self.mqtt_bridge.publish_availability(device, False)
                    
                    except Exception as e:
                        logger.error(
                            f"Error polling device {device.device_name}: {e}"
                        )
                
                # Log poll cycle summary
                poll_duration = asyncio.get_event_loop().time() - poll_start
                poll_count += 1
                logger.info(
                    f"Poll cycle #{poll_count} complete: "
                    f"{len(self.devices)} devices, "
                    f"{state_changes} state changes, "
                    f"{poll_duration:.2f}s duration"
                )
                
                # Update health server status
                if self.health_server:
                    self.health_server.update_poll_status(len(self.devices))
                
                # Check memory usage periodically (every 10 polls)
                if poll_count % 10 == 0:
                    self._check_memory_usage()
                
                # Perform periodic connection refresh (every 24h)
                await self._periodic_connection_refresh()
                
                # Reset backoff on successful poll
                self.backoff.reset()
                
                # Wait for next poll interval
                await asyncio.sleep(self.config.poll_interval)
            
            except ApiError as e:
                logger.error(f"API error during polling: {e}")
                delay = self.backoff.get_delay()
                logger.warning(f"Applying exponential backoff: {delay:.1f}s delay")
                await asyncio.sleep(delay)
            
            except Exception as e:
                logger.exception(f"Unexpected error in polling loop: {e}")
                delay = self.backoff.get_delay()
                logger.warning(f"Applying exponential backoff: {delay:.1f}s delay")
                await asyncio.sleep(delay)
    
    async def shutdown(self) -> None:
        """Perform graceful shutdown with 30-second timeout."""
        if not self.running:
            return
        
        logger.info("Shutting down MELCloud Home Bridge...")
        logger.info("Cleaning up connections and flushing logs...")
        self.running = False
        
        shutdown_start = asyncio.get_event_loop().time()
        shutdown_timeout = 30  # seconds
        
        try:
            # Close health server
            if self.health_server:
                logger.info("Stopping health server...")
                try:
                    await asyncio.wait_for(
                        self.health_server.stop(),
                        timeout=5.0
                    )
                    logger.info("✓ Health server stopped")
                except asyncio.TimeoutError:
                    logger.warning("Health server stop timed out")
            
            # Close MQTT connection
            if self.mqtt_bridge:
                logger.info("Disconnecting from MQTT broker...")
                try:
                    await asyncio.wait_for(
                        self.mqtt_bridge.disconnect(),
                        timeout=10.0
                    )
                    logger.info("✓ MQTT disconnected")
                except asyncio.TimeoutError:
                    logger.warning("MQTT disconnect timed out")
            
            # Close MELCloud client
            if self.melcloud_client:
                logger.info("Closing MELCloud client...")
                try:
                    await asyncio.wait_for(
                        self.melcloud_client.close(),
                        timeout=5.0
                    )
                    logger.info("✓ MELCloud client closed")
                except asyncio.TimeoutError:
                    logger.warning("MELCloud client close timed out")
            
            # Flush logs
            logger.info("Flushing logs...")
            await asyncio.sleep(0.5)  # Allow log buffer to flush
            
            shutdown_duration = asyncio.get_event_loop().time() - shutdown_start
            
            if shutdown_duration > shutdown_timeout:
                logger.warning(
                    f"Shutdown took {shutdown_duration:.1f}s "
                    f"(exceeded {shutdown_timeout}s timeout)"
                )
            else:
                logger.info(
                    f"✓ Shutdown complete in {shutdown_duration:.1f}s"
                )
            
            logger.info("=" * 60)
            logger.info("MELCloud Home Bridge stopped")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
            logger.info("Forced shutdown after error")
    
    async def _handle_command(
        self,
        device: ClimateDevice,
        topic: str,
        payload: str
    ) -> None:
        """
        Handle command from MQTT (temperature, mode, tank temperature, switches).
        
        Args:
            device: Target device
            topic: MQTT topic that received the command
            payload: MQTT payload
        """
        assert self.command_handler is not None, "Command handler not initialized"
        assert self.mqtt_bridge is not None, "MQTT bridge not initialized"
        
        success = False
        
        # Route based on topic
        if "set_temperature" in topic:
            # Parse temperature from payload
            temperature = self.command_handler.parse_temperature_command(payload)
            if temperature is None:
                logger.warning(
                    f"Failed to parse temperature command for {device.device_name}: {payload}"
                )
                return
            
            # Execute command
            success = await self.command_handler.handle_temperature_command(
                device, temperature
            )
        
        elif "set_mode" in topic:
            # Parse mode from payload
            mode = self.command_handler.parse_mode_command(payload)
            if mode is None:
                logger.warning(
                    f"Failed to parse mode command for {device.device_name}: {payload}"
                )
                return
            
            # Execute command
            success = await self.command_handler.handle_mode_command(device, mode)
        
        elif "set_tank_temperature" in topic:
            # Parse tank temperature from payload
            temperature = self.command_handler.parse_temperature_command(payload)
            if temperature is None:
                logger.warning(
                    f"Failed to parse tank temperature command for {device.device_name}: {payload}"
                )
                return
            
            # Execute command
            success = await self.command_handler.handle_tank_temperature_command(
                device, temperature
            )
        
        elif "set_forced_hot_water" in topic:
            # Parse switch command (ON/OFF)
            enabled = self.command_handler.parse_switch_command(payload)
            if enabled is None:
                logger.warning(
                    f"Failed to parse forced hot water command for {device.device_name}: {payload}"
                )
                return
            
            # Execute command
            success = await self.command_handler.handle_forced_hot_water_command(
                device, enabled
            )
        
        elif "set_prohibit_hot_water" in topic:
            # Parse switch command (ON/OFF)
            enabled = self.command_handler.parse_switch_command(payload)
            if enabled is None:
                logger.warning(
                    f"Failed to parse prohibit hot water command for {device.device_name}: {payload}"
                )
                return
            
            # Execute command
            success = await self.command_handler.handle_prohibit_hot_water_command(
                device, enabled
            )
        
        else:
            logger.warning(f"Unknown command topic: {topic}")
            return
        
        # If command was successful, update stored state and publish to MQTT
        if success:
            # Update stored state
            self.device_states[device.device_id] = device.state.copy()
            # Publish updated state to MQTT
            await self.mqtt_bridge.publish_state(device)


async def main() -> int:
    """
    Main application entry point.
    
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    app = Application()
    return await app.start()


def run() -> None:
    """Run the application (synchronous entry point for __main__)."""
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run()
