"""
Unit tests for logging configuration.

Tests credential sanitization and log format configuration.
"""

from app.logging_conf import sanitize_for_logging


class TestCredentialSanitization:
    """Test that credentials are properly masked in log messages."""
    
    def test_sanitize_email_in_dict(self):
        """Test email sanitization in dictionary."""
        data = {
            "email": "user@example.com",
            "password": "secret123",
            "other": "value"
        }
        sanitized = sanitize_for_logging(data)
        
        assert sanitized["email"] == "***REDACTED***"
        assert sanitized["password"] == "***REDACTED***"
        assert sanitized["other"] == "value"
    
    def test_sanitize_password_variations(self):
        """Test various password field names are sanitized."""
        data = {
            "password": "secret",
            "pass": "secret",
            "pwd": "secret",
            "passwd": "secret"
        }
        sanitized = sanitize_for_logging(data)
        
        assert all(v == "***REDACTED***" for v in sanitized.values())
    
    def test_sanitize_token_fields(self):
        """Test token fields are sanitized."""
        data = {
            "token": "abc123",
            "access_token": "xyz789",
            "api_key": "key123",
            "secret": "mysecret"
        }
        sanitized = sanitize_for_logging(data)
        
        assert all(v == "***REDACTED***" for v in sanitized.values())
    
    def test_sanitize_nested_dict(self):
        """Test sanitization works in nested dictionaries."""
        data = {
            "user": {
                "email": "user@example.com",
                "password": "secret"
            },
            "config": {
                "mqtt_host": "localhost",
                "api_key": "key123"
            }
        }
        sanitized = sanitize_for_logging(data)
        
        assert sanitized["user"]["email"] == "***REDACTED***"
        assert sanitized["user"]["password"] == "***REDACTED***"
        assert sanitized["config"]["mqtt_host"] == "localhost"
        assert sanitized["config"]["api_key"] == "***REDACTED***"
    
    def test_sanitize_list_of_dicts(self):
        """Test sanitization works in lists containing dictionaries."""
        data = {
            "users": [
                {"email": "user1@example.com", "name": "User 1"},
                {"email": "user2@example.com", "name": "User 2"}
            ]
        }
        sanitized = sanitize_for_logging(data)
        
        assert sanitized["users"][0]["email"] == "***REDACTED***"
        assert sanitized["users"][0]["name"] == "User 1"
        assert sanitized["users"][1]["email"] == "***REDACTED***"
        assert sanitized["users"][1]["name"] == "User 2"
    
    def test_sanitize_preserves_non_sensitive_data(self):
        """Test non-sensitive data is not modified."""
        data = {
            "username": "john_doe",  # username is not sensitive, only email
            "host": "localhost",
            "port": 1883,
            "enabled": True,
            "items": [1, 2, 3]
        }
        sanitized = sanitize_for_logging(data)
        
        assert sanitized == data  # Should be unchanged
    
    def test_sanitize_handles_none_values(self):
        """Test sanitization handles None values gracefully."""
        data = {
            "email": None,
            "password": None,
            "host": "localhost"
        }
        sanitized = sanitize_for_logging(data)
        
        assert sanitized["email"] == "***REDACTED***"  # Still redacts even if None
        assert sanitized["password"] == "***REDACTED***"
        assert sanitized["host"] == "localhost"
    
    def test_sanitize_handles_empty_dict(self):
        """Test sanitization handles empty dictionary."""
        data = {}
        sanitized = sanitize_for_logging(data)
        
        assert sanitized == {}
    
    def test_sanitize_case_insensitive(self):
        """Test field names are matched case-insensitively."""
        data = {
            "EMAIL": "user@example.com",
            "Password": "secret",
            "API_KEY": "key123"
        }
        sanitized = sanitize_for_logging(data)
        
        assert sanitized["EMAIL"] == "***REDACTED***"
        assert sanitized["Password"] == "***REDACTED***"
        assert sanitized["API_KEY"] == "***REDACTED***"
