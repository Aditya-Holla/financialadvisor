"""User identity endpoint."""

from fastapi import APIRouter

router = APIRouter(prefix="/me", tags=["identity"])


@router.get("")
async def get_me():
    """
    Returns who you are + account state.
    
    TODO: Implement user authentication and return user info.
    """
    return {"message": "Not implemented yet"}

