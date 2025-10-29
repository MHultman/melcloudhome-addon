"""Credentials entity for MELCloud authentication."""

from pydantic import BaseModel, EmailStr, Field, ConfigDict


class Credentials(BaseModel):
    """MELCloud account credentials."""
    model_config = ConfigDict(frozen=True)  # Credentials are immutable
    
    email: EmailStr = Field(
        ...,
        description="MELCloud account email address"
    )
    password: str = Field(
        ...,
        min_length=1,
        description="MELCloud account password"
    )
