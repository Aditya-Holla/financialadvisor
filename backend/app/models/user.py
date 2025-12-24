"""User-related models."""

from typing import Optional
from pydantic import BaseModel


class UserContext(BaseModel):
    """User context attached to authenticated requests."""
    user_id: str
    email: Optional[str] = None

