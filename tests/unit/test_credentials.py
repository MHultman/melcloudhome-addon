"""Unit tests for Credentials entity."""

import pytest
from pydantic import ValidationError

from app.models import Credentials


def test_valid_email_accepted():
    """Test that valid email addresses are accepted."""
    # Valid email formats
    valid_emails = [
        "user@example.com",
        "user.name@example.com",
        "user+tag@example.co.uk",
        "user123@subdomain.example.com",
    ]
    
    for email in valid_emails:
        creds = Credentials(email=email, password="test_password")
        assert creds.email == email
        assert creds.password == "test_password"


def test_invalid_email_rejected():
    """Test that invalid email addresses are rejected."""
    # Invalid email formats
    invalid_emails = [
        "not-an-email",
        "@example.com",
        "user@",
        "user @example.com",
        "",
    ]
    
    for email in invalid_emails:
        with pytest.raises(ValidationError) as exc_info:
            Credentials(email=email, password="test_password")
        
        # Verify error mentions email validation
        assert "email" in str(exc_info.value).lower()


def test_empty_password_rejected():
    """Test that empty passwords are rejected."""
    with pytest.raises(ValidationError) as exc_info:
        Credentials(email="user@example.com", password="")
    
    # Verify error mentions password length
    assert "password" in str(exc_info.value).lower()


def test_credentials_are_immutable():
    """Test that Credentials instances are frozen (immutable)."""
    creds = Credentials(email="user@example.com", password="test_password")
    
    # Attempt to modify should raise error
    with pytest.raises(ValidationError) as exc_info:
        creds.email = "new@example.com"  # type: ignore
    
    assert "frozen" in str(exc_info.value).lower() or "immutable" in str(exc_info.value).lower()


def test_missing_email_rejected():
    """Test that missing email field is rejected."""
    with pytest.raises(ValidationError) as exc_info:
        Credentials(password="test_password")  # type: ignore
    
    assert "email" in str(exc_info.value).lower()


def test_missing_password_rejected():
    """Test that missing password field is rejected."""
    with pytest.raises(ValidationError) as exc_info:
        Credentials(email="user@example.com")  # type: ignore
    
    assert "password" in str(exc_info.value).lower()
