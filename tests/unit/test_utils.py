"""Unit tests for utility functions."""

import pytest
from app.utils import ExponentialBackoff, sanitize_mqtt_topic, format_uptime


def test_exponential_backoff_calculates_delays_correctly():
    """Test that exponential backoff calculates correct delays."""
    backoff = ExponentialBackoff(initial_delay=1.0, max_delay=10.0, multiplier=2.0, jitter=False)
    
    # First attempt: 1.0 * 2^0 = 1.0
    assert backoff.get_delay() == 1.0
    assert backoff.attempts == 1
    
    # Second attempt: 1.0 * 2^1 = 2.0
    assert backoff.get_delay() == 2.0
    assert backoff.attempts == 2
    
    # Third attempt: 1.0 * 2^2 = 4.0
    assert backoff.get_delay() == 4.0
    assert backoff.attempts == 3
    
    # Fourth attempt: 1.0 * 2^3 = 8.0
    assert backoff.get_delay() == 8.0
    assert backoff.attempts == 4
    
    # Fifth attempt: 1.0 * 2^4 = 16.0, but capped at max_delay (10.0)
    assert backoff.get_delay() == 10.0
    assert backoff.attempts == 5


def test_exponential_backoff_reset():
    """Test that reset() resets attempt counter."""
    backoff = ExponentialBackoff(jitter=False)
    
    backoff.get_delay()
    backoff.get_delay()
    assert backoff.attempts == 2
    
    backoff.reset()
    assert backoff.attempts == 0
    
    # Next delay should be initial_delay again
    assert backoff.get_delay() == 1.0


def test_exponential_backoff_with_jitter():
    """Test that jitter adds randomness to delays."""
    backoff = ExponentialBackoff(initial_delay=1.0, multiplier=2.0, jitter=True)
    
    delays = [backoff.get_delay() for _ in range(10)]
    
    # All delays should be >= expected delay (jitter adds, not subtracts in our impl)
    assert delays[0] >= 1.0
    
    # With jitter, delays should not all be exactly the same
    # (small chance of collision, but unlikely with 10 samples)
    assert len(set(delays)) > 1


def test_sanitize_mqtt_topic_basic():
    """Test basic MQTT topic sanitization."""
    assert sanitize_mqtt_topic("Living Room AC") == "living_room_ac"
    assert sanitize_mqtt_topic("Bedroom #1") == "bedroom_1"
    assert sanitize_mqtt_topic("Test@Device!") == "testdevice"


def test_sanitize_mqtt_topic_special_characters():
    """Test removal of special characters."""
    assert sanitize_mqtt_topic("Device (Kitchen)") == "device_kitchen"
    assert sanitize_mqtt_topic("AC/Heater Unit") == "acheater_unit"
    assert sanitize_mqtt_topic("Test & Device") == "test_device"


def test_sanitize_mqtt_topic_whitespace():
    """Test whitespace handling."""
    assert sanitize_mqtt_topic("  Device  ") == "device"
    assert sanitize_mqtt_topic("Multi   Space  Device") == "multi_space_device"


def test_sanitize_mqtt_topic_consecutive_underscores():
    """Test that consecutive underscores are collapsed."""
    assert sanitize_mqtt_topic("Test__Device") == "test_device"
    assert sanitize_mqtt_topic("A___B___C") == "a_b_c"


def test_sanitize_mqtt_topic_preserves_allowed_characters():
    """Test that allowed characters are preserved."""
    assert sanitize_mqtt_topic("device-1.2") == "device-1.2"
    assert sanitize_mqtt_topic("test_device") == "test_device"


def test_format_uptime_seconds():
    """Test uptime formatting for seconds/minutes."""
    assert format_uptime(0) == "0m"
    assert format_uptime(30) == "0m"
    assert format_uptime(60) == "1m"
    assert format_uptime(300) == "5m"


def test_format_uptime_hours():
    """Test uptime formatting with hours."""
    assert format_uptime(3600) == "1h"
    assert format_uptime(3900) == "1h 5m"
    assert format_uptime(7380) == "2h 3m"


def test_format_uptime_days():
    """Test uptime formatting with days."""
    assert format_uptime(86400) == "1d"
    assert format_uptime(90000) == "1d 1h"
    assert format_uptime(176400) == "2d 1h"


def test_format_uptime_complex():
    """Test complex uptime formatting."""
    # 2 days, 3 hours, 45 minutes, 30 seconds
    uptime = (2 * 86400) + (3 * 3600) + (45 * 60) + 30
    assert format_uptime(uptime) == "2d 3h 45m"
