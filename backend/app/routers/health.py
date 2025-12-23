"""Health check endpoint."""

from fastapi import APIRouter
from app.models.common import HealthResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthResponse)
async def health_check():
    """Simple uptime check, returns 'ok'."""
    return {"status": "ok"}

