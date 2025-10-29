"""MELCloud API client wrapper for pymelcloudhome library."""

import asyncio
from typing import List, Dict, Any, Optional
from enum import Enum
from loguru import logger

from pymelcloudhome import MelCloudHomeClient  # type: ignore[import-untyped]

from app.models import ClimateDevice, Credentials
from app.utils import ExponentialBackoff


class NetworkErrorType(Enum):
    """Classification of network errors for resilience handling."""
    TIMEOUT = "timeout"
    CONNECTION = "connection"
    RATE_LIMIT = "rate_limit"
    UNAUTHORIZED = "unauthorized"
    SERVER_ERROR = "server_error"
    UNKNOWN = "unknown"


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
    Async wrapper for pymelcloudhome MelCloudHomeClient.
    
    Handles authentication, device discovery, state polling, and command execution.
    Includes network resilience with exponential backoff and retry logic.
    """
    
    # Configuration constants for resilience
    MAX_RETRIES = 3
    API_TIMEOUT_SECONDS = 30
    
    def __init__(self, credentials: Credentials):
        """
        Initialize MELCloud client.
        
        Args:
            credentials: MELCloud account credentials
        """
        self.credentials = credentials
        self._client: Optional[MelCloudHomeClient] = None
        self._session_token: Optional[str] = None
        self._devices: List[Any] = []
        self._device_types: Dict[str, str] = {}  # device_id -> device_type mapping
        self._authenticated = False
        self._logger = logger.bind(component="melcloud_client")
        self._backoff = ExponentialBackoff(
            initial_delay=1.0,
            max_delay=60.0,
            multiplier=2.0
        )
        self._auth_retry_count = 0
        self._max_auth_retries = 3
    
    async def authenticate(self) -> None:
        """
        Authenticate with MELCloud and obtain session token.
        
        Uses pymelcloudhome's MelCloudHomeClient.login() which handles Pyppeteer-based
        web authentication for JavaScript-heavy MELCloud login flow.
        
        Raises:
            LoginError: If authentication fails after max retries
        """
        self._logger.info("Authenticating with MELCloud...", extra={"operation": "authenticate"})
        self._logger.debug(
            f"Using credentials for {self.credentials.email}",
            extra={"operation": "authenticate", "email": self.credentials.email}
        )
        
        # Check if we've exceeded max auth retries
        if self._auth_retry_count >= self._max_auth_retries:
            error_msg = (
                f"Authentication failed after {self._max_auth_retries} attempts. "
                "Please check your credentials and try again later."
            )
            self._logger.error(
                error_msg,
                extra={
                    "operation": "authenticate",
                    "attempts": self._auth_retry_count,
                    "resolution": "Verify MELCloud email/password in configuration"
                }
            )
            raise LoginError(error_msg)
        
        try:
            import time
            start_time = time.time()
            
            # Create client with system Chromium path for Alpine Linux
            # pymelcloudhome v0.3.0+ supports chromium_executable_path for ARM64/Alpine
            # Alpine Linux uses /usr/bin/chromium as the executable path
            self._client = MelCloudHomeClient(
                chromium_executable_path='/usr/bin/chromium'  # type: ignore[call-arg]
            )
            await self._client.login(
                email=self.credentials.email,
                password=self.credentials.password
            )
            
            duration = time.time() - start_time
            
            self._authenticated = True
            self._auth_retry_count = 0  # Reset counter on success
            self._logger.info(
                "Successfully authenticated with MELCloud",
                extra={"operation": "authenticate", "duration_seconds": f"{duration:.2f}"}
            )
            
        except Exception as e:
            duration = time.time() - start_time if 'start_time' in locals() else 0
            self._authenticated = False
            self._auth_retry_count += 1
            error_msg = (
                f"MELCloud authentication failed: {str(e)} "
                f"(attempt {self._auth_retry_count}/{self._max_auth_retries})"
            )
            self._logger.error(
                error_msg,
                extra={
                    "operation": "authenticate",
                    "attempts": self._auth_retry_count,
                    "duration_seconds": f"{duration:.2f}",
                    "error_type": type(e).__name__,
                    "resolution": "Check credentials, network connectivity, and MELCloud service status"
                }
            )
            raise LoginError(error_msg) from e
    
    async def list_devices(self) -> List[ClimateDevice]:
        """
        Discover all climate devices from MELCloud account.
        
        Returns:
            List of ClimateDevice instances
            
        Raises:
            ApiError: If device list request fails
        """
        if not self._authenticated or not self._client:
            raise ApiError("Not authenticated - call authenticate() first")
        
        self._logger.debug("Fetching device list from MELCloud...")
        
        try:
            # Get devices from client
            raw_devices = await self._client.list_devices()
            
            if raw_devices is None:
                raw_devices = []
            
            # Cache raw devices for later use
            self._devices = raw_devices
            
            # Store device types for set_device_state calls
            for device in raw_devices:
                device_id = getattr(device, 'id', None) or getattr(device, 'device_id', None)
                device_type = getattr(device, 'type', None) or getattr(device, 'device_type', 'unknown')
                if device_id:
                    self._device_types[str(device_id)] = str(device_type)
                    self._logger.debug(
                        f"Cached device type for {device_id}: {device_type}",
                        extra={
                            "operation": "list_devices",
                            "device_id": device_id,
                            "device_type": device_type
                        }
                    )
            
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
        if not self._authenticated or not self._client:
            raise ApiError("Not authenticated - call authenticate() first")
        
        self._logger.debug(
            f"Fetching state for device {device_id}",
            extra={"operation": "get_device_state", "device_id": device_id}
        )
        
        try:
            import time
            start_time = time.time()
            
            # Get device state from client
            state = await self._client.get_device_state(device_id)
            
            duration = time.time() - start_time
            
            if state is None:
                raise DeviceNotFoundError(f"Device {device_id} not found")
            
            # DEBUG: Log the raw state response
            self._logger.debug(
                f"Raw state for device {device_id}: {state}",
                extra={
                    "operation": "get_device_state",
                    "device_id": device_id,
                    "duration_seconds": round(duration, 3),
                    "state_keys": list(state.keys()) if isinstance(state, dict) else "not_a_dict",
                    "state_type": type(state).__name__
                }
            )
            
            # If state is a dict with 'settings' array (ATW devices), log that too
            if isinstance(state, dict) and "settings" in state:
                settings = state.get("settings", [])
                self._logger.debug(
                    f"Device {device_id} has {len(settings)} settings",
                    extra={
                        "operation": "get_device_state",
                        "device_id": device_id,
                        "settings_count": len(settings),
                        "sample_settings": settings[:3] if len(settings) > 0 else []
                    }
                )
            
            # Log capabilities if present
            if isinstance(state, dict) and "capabilities" in state:
                capabilities = state.get("capabilities", {})
                self._logger.debug(
                    f"Device {device_id} capabilities: hasHotWater={capabilities.get('hasHotWater')}, "
                    f"hasZone2={capabilities.get('hasZone2')}, "
                    f"tempRange={capabilities.get('minSetTemperature')}-{capabilities.get('maxSetTemperature')}",
                    extra={
                        "operation": "get_device_state",
                        "device_id": device_id,
                        "capabilities": capabilities
                    }
                )
            
            self._logger.debug(
                f"Retrieved state for device {device_id}",
                extra={
                    "operation": "get_device_state",
                    "device_id": device_id,
                    "duration_seconds": f"{duration:.2f}",
                    "state_keys": list(state.keys()) if state else []
                }
            )
            
            return state
            
        except DeviceNotFoundError:
            raise
        except Exception as e:
            # Check for 401 Unauthorized
            if "401" in str(e) or "unauthorized" in str(e).lower():
                self._logger.warning(
                    "Session expired, attempting re-authentication...",
                    extra={"operation": "get_device_state", "device_id": device_id}
                )
                await self._handle_401_error()
                # Retry once after re-auth
                return await self.get_device_state(device_id)
            
            error_msg = f"Failed to get device state: {str(e)}"
            self._logger.error(
                error_msg,
                extra={
                    "operation": "get_device_state",
                    "device_id": device_id,
                    "error_type": type(e).__name__,
                    "resolution": "Check network connectivity and MELCloud service status"
                }
            )
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
        if not self._authenticated or not self._client:
            raise ApiError("Not authenticated - call authenticate() first")
        
        # Get device type from cache
        device_type = self._device_types.get(device_id)
        if not device_type:
            raise DeviceNotFoundError(
                f"Device {device_id} not found in cache. "
                "Call list_devices() first to populate device cache."
            )
        
        self._logger.info(
            f"Updating device {device_id} state: {state_changes}",
            extra={
                "operation": "set_device_state",
                "device_id": device_id,
                "device_type": device_type,
                "state_changes": state_changes
            }
        )
        self._logger.debug(
            f"State changes detail: {state_changes}",
            extra={"operation": "set_device_state", "device_id": device_id}
        )
        
        try:
            import time
            start_time = time.time()
            
            # Update device state via client (requires device_id, device_type, state_data)
            await self._client.set_device_state(device_id, device_type, state_changes)
            
            duration = time.time() - start_time
            
            self._logger.info(
                f"Successfully updated device {device_id}",
                extra={
                    "operation": "set_device_state",
                    "device_id": device_id,
                    "duration_seconds": f"{duration:.2f}"
                }
            )
            
        except Exception as e:
            # Check for 401 Unauthorized
            if "401" in str(e) or "unauthorized" in str(e).lower():
                self._logger.warning(
                    "Session expired, attempting re-authentication...",
                    extra={"operation": "set_device_state", "device_id": device_id}
                )
                await self._handle_401_error()
                # Retry once after re-auth
                return await self.set_device_state(device_id, state_changes)
            
            error_msg = f"Failed to update device state: {str(e)}"
            self._logger.error(
                error_msg,
                extra={
                    "operation": "set_device_state",
                    "device_id": device_id,
                    "device_type": device_type,
                    "state_changes": state_changes,
                    "error_type": type(e).__name__,
                    "resolution": "Check device availability and network connectivity"
                }
            )
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
    
    def _classify_network_error(self, error: Exception) -> NetworkErrorType:
        """
        Classify network error for appropriate resilience handling.
        
        Args:
            error: Exception to classify
            
        Returns:
            NetworkErrorType enum value
        """
        error_str = str(error).lower()
        
        # Check for timeout errors
        if "timeout" in error_str or "timed out" in error_str:
            return NetworkErrorType.TIMEOUT
        
        # Check for connection errors
        if any(term in error_str for term in [
            "connection", "refused", "reset", "closed",
            "network", "unreachable", "dns"
        ]):
            return NetworkErrorType.CONNECTION
        
        # Check for rate limiting (HTTP 429)
        if "429" in error_str or "rate limit" in error_str or "too many" in error_str:
            return NetworkErrorType.RATE_LIMIT
        
        # Check for unauthorized (HTTP 401)
        if "401" in error_str or "unauthorized" in error_str:
            return NetworkErrorType.UNAUTHORIZED
        
        # Check for server errors (5xx)
        if any(code in error_str for code in ["500", "502", "503", "504"]):
            return NetworkErrorType.SERVER_ERROR
        
        return NetworkErrorType.UNKNOWN
    
    async def _execute_with_retry(
        self,
        operation_name: str,
        func: Any,
        *args: Any,
        **kwargs: Any
    ) -> Any:
        """
        Execute API operation with exponential backoff retry logic.
        
        Args:
            operation_name: Human-readable operation name for logging
            func: Async function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func
            
        Returns:
            Result from func
            
        Raises:
            ApiError: If all retry attempts fail
        """
        last_error = None
        
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                # Execute with timeout
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=self.API_TIMEOUT_SECONDS
                )
            except asyncio.TimeoutError as e:
                last_error = e
                error_type = NetworkErrorType.TIMEOUT
                self._logger.warning(
                    f"{operation_name} timed out after {self.API_TIMEOUT_SECONDS}s "
                    f"(attempt {attempt}/{self.MAX_RETRIES})"
                )
            except Exception as e:
                last_error = e
                error_type = self._classify_network_error(e)
                
                # Handle 401 errors with re-auth (don't count as retry)
                if error_type == NetworkErrorType.UNAUTHORIZED:
                    self._logger.warning(
                        f"{operation_name} received 401, attempting re-authentication"
                    )
                    try:
                        await self._handle_401_error()
                        # Retry immediately after re-auth (don't count as retry)
                        continue
                    except LoginError:
                        # Re-auth failed, propagate error
                        raise
                
                # Handle rate limiting with longer backoff
                if error_type == NetworkErrorType.RATE_LIMIT:
                    backoff_delay = self._backoff.get_delay() * 3  # Triple delay for rate limits
                    self._logger.warning(
                        f"{operation_name} rate limited, backing off for {backoff_delay:.1f}s "
                        f"(attempt {attempt}/{self.MAX_RETRIES})"
                    )
                else:
                    backoff_delay = self._backoff.get_delay()
                    self._logger.warning(
                        f"{operation_name} failed with {error_type.value} error: {e} "
                        f"(attempt {attempt}/{self.MAX_RETRIES})"
                    )
            
            # If this wasn't the last attempt, wait before retrying
            if attempt < self.MAX_RETRIES:
                await asyncio.sleep(self._backoff.get_delay())
            else:
                # All retries exhausted
                error_msg = (
                    f"{operation_name} failed after {self.MAX_RETRIES} attempts. "
                    f"Last error: {last_error}"
                )
                self._logger.error(error_msg)
                raise ApiError(error_msg) from last_error
    
    async def close(self) -> None:
        """Clean up resources and close connections."""
        self._logger.debug("Closing MELCloud client")
        
        # Close the pymelcloudhome client if it exists
        if self._client:
            try:
                await self._client.close()
                self._logger.debug("Closed pymelcloudhome client connection")
            except Exception as e:
                self._logger.warning(f"Error closing pymelcloudhome client: {e}")
        
        self._authenticated = False
        self._session_token = None
        self._devices = []
        self._device_types = {}
        self._client = None
    
    @property
    def is_authenticated(self) -> bool:
        """Check if client is currently authenticated."""
        return self._authenticated
