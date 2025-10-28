"""Main application entry point for MELCloud Home Bridge."""

import asyncio
import signal
import sys
from typing import Optional
from loguru import logger

from app import __version__
from app.config import load_configuration, Configuration
from app.logging_conf import setup_logging


class Application:
    """Main application orchestrator."""
    
    def __init__(self):
        """Initialize application."""
        self.config: Optional[Configuration] = None
        self.running = False
        self._shutdown_event = asyncio.Event()
    
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
            
            # Mark as running
            self.running = True
            logger.info("Application started successfully")
            
            # Main event loop - wait for shutdown signal
            await self._shutdown_event.wait()
            
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
    
    async def shutdown(self) -> None:
        """Perform graceful shutdown."""
        if not self.running:
            return
        
        logger.info("Shutting down...")
        self.running = False
        
        # TODO: Close connections (MQTT, MELCloud, health server) in future phases
        
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
