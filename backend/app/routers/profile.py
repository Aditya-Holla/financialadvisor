"""Profile management endpoints."""

from fastapi import APIRouter

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("")
async def get_profile():
    """
    Fetch user profile.
    
    TODO: Implement profile retrieval from database.
    """
    return {"message": "Not implemented yet"}


@router.put("")
async def update_profile():
    """
    Create/update risk, horizon, goals, and constraints.
    
    TODO: Implement profile creation/update logic.
    """
    return {"message": "Not implemented yet"}

