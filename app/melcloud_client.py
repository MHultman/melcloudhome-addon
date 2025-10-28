"""MELCloud API client wrapper for pymelcloudhome library."""

import asyncio
from typing import List, Dict, Any, Optional
from loguru import logger

# pymelcloudhome imports
try:
    from pymelcloudhome import (  # type: ignore[import-untyped]
        melcloud_login,
        list_devices,
        get_device_state,
        set_device_state,
    )
except ImportError:
    # For type checking when pymelcloudhome not installed
    melcloud_login = None  # type: ignore
    list_devices = None  # type: ignore
    get_device_state = None  # type: ignore
    set_device_state = None  # type: ignore

from app.models import ClimateDevice, Credentials


class MelCloudError(Exception):
    """Base exception for MELCloud client errors."""
    pass


class LoginError(MelCloudError):
    """Authentication failed."""
    pass


class ApiError(MelCloudError):
    """API request failed."""
    pass


class DeviceNotFoundError(MelCloudError):
    """Requested device not found."""
    pass


class MelCloudClient:
    """
    Async wrapper for pymelcloudhome synchronous API.
    
    Handles authentication, device discovery, state polling, and command execution.
    """
    
    def __init__(self, credentials: Credentials):
        """
        Initialize MELCloud client.
        
        Args:
            credentials: MELCloud account credentials
        """
        self.credentials = credentials
        self._session_token: Optional[str] = None
        self._devices: List[Any] = []
        self._authenticated = False
        self._logger = logger.bind(component="melcloud_client")
    
    async def authenticate(self) -> None:
        """
        Authenticate with MELCloud and obtain session token.
        
        Uses pymelcloudhome's melcloud_login() which handles Playwright-based
        web authentication for JavaScript-heavy MELCloud login flow.
        
        Raises:
            LoginError: If authentication fails
        """
        self._logger.info("Authenticating with MELCloud...")
        
        try:
            # Run sync melcloud_login in thread pool
            loop = asyncio.get_event_loop()
            self._session_token = await loop.run_in_executor(
                None,
                melcloud_login,
                self.credentials.email,
                self.credentials.password
            )
            
            if not self._session_token:
                raise LoginError("Authentication returned empty token")
            
            self._authenticated = True
            self._logger.info("Successfully authenticated with MELCloud")
            
        except Exception as e:
            self._authenticated = False
            error_msg = f"MELCloud authentication failed: {str(e)}"
            self._logger.error(error_msg)
            raise LoginError(error_msg) from e
    
    async def list_devices(self) -> List[ClimateDevice]:
        """
        Discover all climate devices from MELCloud account.
        
        Returns:
            List of ClimateDevice instances
            
        Raises:
            ApiError: If device list request fails
        """
        if not self._authenticated:
            raise ApiError("Not authenticated - call authenticate() first")
        
        self._logger.debug("Fetching device list from MELCloud...")
        
        try:
            # Run sync list_devices in thread pool
            loop = asyncio.get_event_loop()
            raw_devices = await loop.run_in_executor(
                None,
                list_devices,
                self._session_token
            )
            
            if raw_devices is None:
                raw_devices = []
            
            # Cache raw devices for later use
            self._devices = raw_devices
            
            # Convert to ClimateDevice instances
            devices = []
            for device in raw_devices:
                try:
                    # Get initial state for each device
                    state = await self.get_device_state(device.id)
                    climate_device = ClimateDevice.from_pymelcloud_device(device, state)
                    devices.append(climate_device)
                except Exception as e:
                    self._logger.warning(
                        f"Failed to get state for device {device.id}: {e}"
                    )
                    # Create device without state
                    climate_device = ClimateDevice.from_pymelcloud_device(device)
                    devices.append(climate_device)
            
            self._logger.info(f"Discovered {len(devices)} climate devices")
            return devices
            
        except Exception as e:
            error_msg = f"Failed to list devices: {str(e)}"
            self._logger.error(error_msg)
            raise ApiError(error_msg) from e
    
    async def get_device_state(self, device_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current state for a specific device.
        
        Args:
            device_id: Device UUID
            
        Returns:
            Device state dictionary or None if unavailable
            
        Raises:
            DeviceNotFoundError: If device ID is invalid
            ApiError: If state request fails
        """
        if not self._authenticated:
            raise ApiError("Not authenticated - call authenticate() first")
        
        self._logger.debug(f"Fetching state for device {device_id}")
        
        try:
            # Run sync get_device_state in thread pool
            loop = asyncio.get_event_loop()
            state = await loop.run_in_executor(
                None,
                get_device_state,
                self._session_token,
                device_id
            )
            
            if state is None:
                raise DeviceNotFoundError(f"Device {device_id} not found")
            
            return state
            
        except DeviceNotFoundError:
            raise
        except Exception as e:
            # Check for 401 Unauthorized
            if "401" in str(e) or "unauthorized" in str(e).lower():
                self._logger.warning("Session expired, attempting re-authentication...")
                await self._handle_401_error()
                # Retry once after re-auth
                return await self.get_device_state(device_id)
            
            error_msg = f"Failed to get device state: {str(e)}"
            self._logger.error(error_msg)
            raise ApiError(error_msg) from e
    
    async def set_device_state(
        self,
        device_id: str,
        state_changes: Dict[str, Any]
    ) -> None:
        """
        Update device state (send command to MELCloud).
        
        Args:
            device_id: Device UUID
            state_changes: Dictionary of state changes to apply
            
        Raises:
            DeviceNotFoundError: If device ID is invalid
            ApiError: If state update fails
        """
        if not self._authenticated:
            raise ApiError("Not authenticated - call authenticate() first")
        
        self._logger.info(
            f"Updating device {device_id} state: {state_changes}"
        )
        
        try:
            # Run sync set_device_state in thread pool
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                set_device_state,
                self._session_token,
                device_id,
                state_changes
            )
            
            self._logger.debug(f"Successfully updated device {device_id}")
            
        except Exception as e:
            # Check for 401 Unauthorized
            if "401" in str(e) or "unauthorized" in str(e).lower():
                self._logger.warning("Session expired, attempting re-authentication...")
                await self._handle_401_error()
                # Retry once after re-auth
                return await self.set_device_state(device_id, state_changes)
            
            error_msg = f"Failed to update device state: {str(e)}"
            self._logger.error(error_msg)
            raise ApiError(error_msg) from e
    
    async def _handle_401_error(self) -> None:
        """
        Handle 401 Unauthorized errors with automatic re-authentication.
        
        Raises:
            LoginError: If re-authentication fails
        """
        self._authenticated = False
        self._session_token = None
        
        try:
            await self.authenticate()
        except LoginError as e:
            self._logger.error(f"Re-authentication failed: {e}")
            raise
    
    async def close(self) -> None:
        """Clean up resources and close connections."""
        self._logger.debug("Closing MELCloud client")
        self._authenticated = False
        self._session_token = None
        self._devices = []
    
    @property
    def is_authenticated(self) -> bool:
        """Check if client is currently authenticated."""
        return self._authenticated
