"""Common response models used across the API."""

from typing import Optional
from pydantic import BaseModel


class StatusResponse(BaseModel):
    """Standard status response."""
    status: str


class HealthResponse(StatusResponse):
    """Health check response."""
    pass


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    detail: Optional[str] = None

