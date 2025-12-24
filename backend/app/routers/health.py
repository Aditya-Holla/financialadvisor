"""Health check endpoint."""

from fastapi import APIRouter, Depends
from app.models.common import HealthResponse
from app.config import Settings, get_settings

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthResponse)
async def health_check(settings: Settings = Depends(get_settings)):
    """
    Simple uptime check, returns 'ok'.
    
    Example of using settings as a dependency.
    """
    return {"status": "ok"}

