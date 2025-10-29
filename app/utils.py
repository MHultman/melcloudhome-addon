"""Utility functions and classes for MELCloud Home Bridge."""

import re


class ExponentialBackoff:
    """
    Exponential backoff calculator for retry logic.
    
    Implements exponential backoff with jitter to avoid thundering herd.
    """
    
    def __init__(
        self,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        multiplier: float = 2.0,
        jitter: bool = True
    ):
        """
        Initialize exponential backoff.
        
        Args:
            initial_delay: Initial delay in seconds (default: 1.0)
            max_delay: Maximum delay in seconds (default: 60.0)
            multiplier: Delay multiplier for each retry (default: 2.0)
            jitter: Add random jitter to avoid synchronized retries (default: True)
        """
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.multiplier = multiplier
        self.jitter = jitter
        self._attempts = 0
    
    def reset(self) -> None:
        """Reset attempt counter to start over."""
        self._attempts = 0
    
    def get_delay(self) -> float:
        """
        Calculate delay for current attempt.
        
        Returns:
            Delay in seconds
        """
        # Calculate exponential delay
        delay = min(
            self.initial_delay * (self.multiplier ** self._attempts),
            self.max_delay
        )
        
        # Add jitter if enabled (random 0-50% of delay)
        if self.jitter:
            import random
            jitter_amount = delay * random.uniform(0, 0.5)
            delay += jitter_amount
        
        self._attempts += 1
        return delay
    
    @property
    def attempts(self) -> int:
        """Get current attempt count."""
        return self._attempts


def sanitize_mqtt_topic(text: str) -> str:
    """
    Sanitize text for use in MQTT topic.
    
    Removes or replaces characters not allowed in MQTT topics:
    - Removes leading/trailing whitespace
    - Replaces spaces with underscores
    - Removes special characters except underscore, dash, and period
    - Converts to lowercase
    
    Args:
        text: Text to sanitize
        
    Returns:
        Sanitized text safe for MQTT topics
    """
    # Remove leading/trailing whitespace
    text = text.strip()
    
    # Replace spaces with underscores
    text = text.replace(" ", "_")
    
    # Remove special characters (keep alphanumeric, underscore, dash, period)
    text = re.sub(r'[^a-zA-Z0-9_\-.]', '', text)
    
    # Convert to lowercase
    text = text.lower()
    
    # Remove consecutive underscores
    text = re.sub(r'_+', '_', text)
    
    return text


def format_uptime(seconds: float) -> str:
    """
    Format uptime in human-readable format.
    
    Args:
        seconds: Uptime in seconds
        
    Returns:
        Formatted uptime string (e.g., "2d 3h 45m")
    """
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    
    return " ".join(parts) if parts else "0m"
