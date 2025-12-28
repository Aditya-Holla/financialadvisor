"""Common response models used across the API."""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class StatusResponse(BaseModel):
    """Standard status response."""
    status: str


class HealthResponse(StatusResponse):
    """Health check response."""
    pass


class APIError(BaseModel):
    """Standardized API error response."""
    code: str
    message: str
    details: Optional[str] = None


class ErrorResponse(BaseModel):
    """Standard error response (legacy, use APIError for new code)."""
    error: str
    detail: Optional[str] = None


class MeResponse(BaseModel):
    """User identity response for /me endpoint."""
    user_id: str
    email: Optional[str] = None
    broker_linked: bool
    last_sync: Optional[datetime] = None


class RecommendationResponse(BaseModel):
    """Response for recommendation generation."""
    recommendation_id: str
    decision: str
    status: str
    created_at: str

