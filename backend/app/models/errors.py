"""Error handling models and exceptions."""

from typing import Optional
from fastapi import HTTPException, status


class AppError(Exception):
    """Base application error."""
    pass


class NotFoundError(AppError):
    """Resource not found error."""
    pass


class ValidationError(AppError):
    """Validation error."""
    pass


def create_error_response(error: str, detail: Optional[str] = None) -> dict:
    """Create a standardized error response dictionary."""
    return {"error": error, "detail": detail}

