"""Main application entry point for MELCloud Home Bridge."""

import asyncio
import signal
import sys
import time
from typing import Optional, List, Dict
from loguru import logger

from app import __version__
from app.config import load_configuration, Configuration
from app.logging_conf import setup_logging
from app.melcloud_client import MelCloudClient, LoginError, ApiError
from app.models import Credentials, ClimateDevice
from app.utils import ExponentialBackoff
from app.mqtt_bridge import MQTTBridge


class Application:
    """Main application orchestrator."""
    
    def __init__(self):
        """Initialize application."""
        self.config: Optional[Configuration] = None
        self.running = False
        self._shutdown_event = asyncio.Event()
        self.melcloud_client: Optional[MelCloudClient] = None
        self.mqtt_bridge: Optional[MQTTBridge] = None
        self.devices: List[ClimateDevice] = []
        self.device_states: Dict[str, Dict] = {}  # device_id -> last known state
        self.backoff = ExponentialBackoff()
    
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
            logger.info("Configuration:")
            for key, value in self.config.get_safe_summary().items():
                logger.info(f"  {key}: {value}")
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
                    
                    discovered = True
                    
                    # Initialize device states
                    for device in self.devices:
                        self.device_states[device.device_id] = device.state.copy()
                
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
        """Perform graceful shutdown."""
        if not self.running:
            return
        
        logger.info("Shutting down...")
        self.running = False
        
        # Close MQTT connection
        if self.mqtt_bridge:
            await self.mqtt_bridge.disconnect()
        
        # Close MELCloud client
        if self.melcloud_client:
            await self.melcloud_client.close()
        
        # TODO: Close health server (Phase 8)
        
        logger.info("Shutdown complete")


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
