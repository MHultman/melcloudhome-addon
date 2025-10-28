"""Logging configuration using Loguru for structured, human-readable logs."""

import sys
import re
from typing import Any
from loguru import logger


# Fields that contain sensitive data (case-insensitive matching)
SENSITIVE_FIELDS = {
    'password', 'pass', 'pwd', 'passwd',
    'email', 'mail',
    'token', 'access_token', 'refresh_token',
    'api_key', 'apikey', 'api-key',
    'secret', 'secret_key',
    'auth', 'authorization',
    'credential', 'credentials'
}


def sanitize_for_logging(data: Any) -> Any:
    """
    Recursively sanitize sensitive data in dictionaries and lists.
    
    Args:
        data: Data structure to sanitize (dict, list, or primitive)
        
    Returns:
        Sanitized copy of data with sensitive fields redacted
    """
    if isinstance(data, dict):
        sanitized = {}
        for key, value in data.items():
            # Check if key is sensitive (case-insensitive)
            if key.lower() in SENSITIVE_FIELDS:
                sanitized[key] = "***REDACTED***"
            else:
                # Recursively sanitize nested structures
                sanitized[key] = sanitize_for_logging(value)
        return sanitized
    
    elif isinstance(data, list):
        # Recursively sanitize list items
        return [sanitize_for_logging(item) for item in data]
    
    else:
        # Primitive type - return as-is
        return data


def sanitize_log_message(message: str) -> str:
    """
    Remove credentials from log messages.
    
    Redacts:
    - Email addresses
    - Passwords in key=value patterns
    - Bearer tokens
    - API keys
    """
    # Redact email-like patterns
    message = re.sub(
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        '***EMAIL***',
        message
    )
    
    # Redact password values
    message = re.sub(
        r'(password["\']?\s*[:=]\s*["\']?)([^"\'\s,}]+)',
        r'\1***REDACTED***',
        message,
        flags=re.IGNORECASE
    )
    
    # Redact bearer tokens
    message = re.sub(
        r'(Bearer\s+)[\w\-\.]+',
        r'\1***TOKEN***',
        message,
        flags=re.IGNORECASE
    )
    
    # Redact API keys
    message = re.sub(
        r'(api[_-]?key["\']?\s*[:=]\s*["\']?)([^"\'\s,}]+)',
        r'\1***REDACTED***',
        message,
        flags=re.IGNORECASE
    )
    
    return message


def setup_logging(log_level: str = "INFO") -> None:
    """
    Configure Loguru logging with human-readable format and credential sanitization.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    # Remove default handler
    logger.remove()
    
    # Custom format with color and structure
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
    
    # Add handler with sanitization
    logger.add(
        sys.stdout,
        format=log_format,
        level=log_level,
        colorize=True,
        backtrace=True,
        diagnose=False,  # Disable variable display for security
        filter=lambda record: _sanitize_record(record)
    )
    
    logger.info(f"Logging initialized at {log_level} level")


def _sanitize_record(record: Any) -> bool:
    """
    Sanitize log record message before output.
    
    Args:
        record: Loguru log record (Record type from loguru)
        
    Returns:
        True to emit the record, False to filter it out
    """
    # Sanitize the message
    if "message" in record:
        record["message"] = sanitize_log_message(record["message"])
    
    # Sanitize extra fields if present
    if "extra" in record:
        for key, value in record["extra"].items():
            if isinstance(value, str):
                record["extra"][key] = sanitize_log_message(value)
    
    return True  # Always emit (don't filter)


def get_logger(name: str):
    """
    Get a logger instance with the specified name.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Loguru logger instance
    """
    return logger.bind(name=name)
