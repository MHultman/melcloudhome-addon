"""Configuration loading and validation for MELCloud Home Bridge."""

from typing import Optional
from pydantic import Field, field_validator, EmailStr
from pydantic_settings import BaseSettings, SettingsConfigDict  # type: ignore


class Configuration(BaseSettings):
    """Add-on configuration loaded from Home Assistant Supervisor."""
    
    model_config = SettingsConfigDict(
        env_prefix="",
        case_sensitive=False,
        validate_default=True
    )
    
    # MELCloud credentials (required)
    melcloud_email: EmailStr = Field(
        ...,
        description="MELCloud account email address"
    )
    melcloud_password: str = Field(
        ...,
        min_length=1,
        description="MELCloud account password"
    )
    
    # MQTT broker settings
    mqtt_host: str = Field(
        default="core-mosquitto",
        description="MQTT broker hostname or IP address"
    )
    mqtt_port: int = Field(
        default=1883,
        ge=1,
        le=65535,
        description="MQTT broker port"
    )
    mqtt_username: Optional[str] = Field(
        default=None,
        description="MQTT username (optional)"
    )
    mqtt_password: Optional[str] = Field(
        default=None,
        description="MQTT password (optional)"
    )
    mqtt_base_topic: str = Field(
        default="homeassistant",
        description="MQTT base topic for Home Assistant Discovery"
    )
    
    # Operational settings
    poll_interval: int = Field(
        default=60,
        ge=10,
        le=600,
        description="Polling interval in seconds (10-600)"
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)"
    )
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is one of the allowed values."""
        allowed_levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
        v_upper = v.upper()
        if v_upper not in allowed_levels:
            raise ValueError(f"log_level must be one of {allowed_levels}, got '{v}'")
        return v_upper
    
    @field_validator("mqtt_base_topic")
    @classmethod
    def validate_mqtt_base_topic(cls, v: str) -> str:
        """Ensure MQTT base topic doesn't have trailing slash."""
        return v.rstrip("/")
    
    def get_safe_summary(self) -> dict:
        """Return configuration summary with credentials masked."""
        return {
            "melcloud_email": self.melcloud_email,
            "melcloud_password": "***REDACTED***",
            "mqtt_host": self.mqtt_host,
            "mqtt_port": self.mqtt_port,
            "mqtt_username": self.mqtt_username or "(none)",
            "mqtt_password": "***REDACTED***" if self.mqtt_password else "(none)",
            "mqtt_base_topic": self.mqtt_base_topic,
            "poll_interval": f"{self.poll_interval}s",
            "log_level": self.log_level,
        }


def load_configuration() -> Configuration:
    """
    Load configuration from environment variables (set by run.sh from Supervisor options).
    
    Raises:
        ValueError: If required configuration is missing or invalid
        pydantic.ValidationError: If configuration validation fails
    """
    try:
        config = Configuration()  # type: ignore[call-arg]
        return config
    except Exception as e:
        # Re-raise with clear error message
        raise ValueError(f"Configuration validation failed: {str(e)}") from e
