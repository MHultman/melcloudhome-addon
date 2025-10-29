"""Health check HTTP server for monitoring add-on status."""

import time
from typing import Optional
from aiohttp import web
from loguru import logger


class HealthServer:
    """
    HTTP server providing health check endpoint.
    
    Exposes /healthz endpoint returning JSON status:
    - 200 OK when all systems healthy
    - 503 Service Unavailable when critical services down
    """
    
    def __init__(self, port: int = 8099):
        """
        Initialize health server.
        
        Args:
            port: HTTP server port (default 8099)
        """
        self.port = port
        self.app: Optional[web.Application] = None
        self.runner: Optional[web.AppRunner] = None
        self.site: Optional[web.TCPSite] = None
        
        # Health status tracking
        self.melcloud_authenticated = False
        self.mqtt_connected = False
        self.last_poll_time: Optional[float] = None
        self.device_count = 0
        self.start_time = time.time()
        
        self._logger = logger.bind(component="health_server")
    
    async def start(self) -> None:
        """Start the health server."""
        self.app = web.Application()
        self.app.router.add_get("/healthz", self._handle_health)
        
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        
        self.site = web.TCPSite(self.runner, "0.0.0.0", self.port)
        await self.site.start()
        
        self._logger.info(f"Health server started on port {self.port}")
    
    async def stop(self) -> None:
        """Stop the health server gracefully."""
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()
        
        self._logger.info("Health server stopped")
    
    async def _handle_health(self, request: web.Request) -> web.Response:
        """
        Handle GET /healthz requests.
        
        Returns:
            JSON response with health status and metrics
        """
        # Calculate uptime
        uptime_seconds = int(time.time() - self.start_time)
        
        # Check if last poll was recent (within 5 minutes)
        last_poll_ok = False
        if self.last_poll_time:
            time_since_poll = time.time() - self.last_poll_time
            last_poll_ok = time_since_poll < 300  # 5 minutes
        
        # Determine overall health
        is_healthy = (
            self.melcloud_authenticated and
            self.mqtt_connected and
            last_poll_ok
        )
        
        # Build response
        status_data = {
            "status": "healthy" if is_healthy else "unhealthy",
            "timestamp": time.time(),
            "uptime_seconds": uptime_seconds,
            "melcloud": {
                "authenticated": self.melcloud_authenticated,
                "status": "connected" if self.melcloud_authenticated else "disconnected"
            },
            "mqtt": {
                "connected": self.mqtt_connected,
                "status": "connected" if self.mqtt_connected else "disconnected"
            },
            "polling": {
                "last_poll_time": self.last_poll_time,
                "time_since_last_poll": time.time() - self.last_poll_time if self.last_poll_time else None,
                "status": "ok" if last_poll_ok else "stale"
            },
            "devices": {
                "count": self.device_count
            }
        }
        
        # Return 200 if healthy, 503 if unhealthy
        status_code = 200 if is_healthy else 503
        
        return web.json_response(status_data, status=status_code)
    
    def update_melcloud_status(self, authenticated: bool) -> None:
        """Update MELCloud authentication status."""
        self.melcloud_authenticated = authenticated
    
    def update_mqtt_status(self, connected: bool) -> None:
        """Update MQTT connection status."""
        self.mqtt_connected = connected
    
    def update_poll_status(self, device_count: int) -> None:
        """Update polling status after successful poll cycle."""
        self.last_poll_time = time.time()
        self.device_count = device_count
