"""Error handling models and exceptions."""

from typing import Optional
from fastapi import HTTPException, status


class AppError(Exception):
    """Base application error."""
    def __init__(self, message: str, code: Optional[str] = None):
        self.message = message
        self.code = code or self.__class__.__name__
        super().__init__(self.message)


class AuthError(AppError):
    """Authentication/authorization error."""
    pass


class NotFoundError(AppError):
    """Resource not found error."""
    pass


class ValidationError(AppError):
    """Validation error."""
    pass


class ExternalServiceError(AppError):
    """Error from external service (Alpaca, Supabase, LLM, etc.)."""
    pass


def create_error_response(error: str, detail: Optional[str] = None) -> dict:
    """Create a standardized error response dictionary (legacy)."""
    return {"error": error, "detail": detail}


def create_api_error_response(code: str, message: str, details: Optional[str] = None) -> dict:
    """Create a standardized APIError response dictionary."""
    return {"code": code, "message": message, "details": details}

