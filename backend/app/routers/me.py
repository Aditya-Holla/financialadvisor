"""User identity endpoint."""

from fastapi import APIRouter, Depends
from app.models.common import MeResponse
from app.models.user import UserContext
from app.auth import get_current_user

router = APIRouter(prefix="/me", tags=["identity"])


@router.get("", response_model=MeResponse)
async def get_me(user: UserContext = Depends(get_current_user)):
    """
    Returns who you are + account state.
    
    Requires: Authorization: Bearer <token>
    """
    # TODO: Check broker_linked status from database
    # TODO: Get last_sync from database
    
    return MeResponse(
        user_id=user.user_id,
        email=user.email,
        broker_linked=False,  # TODO: Implement broker link check
        last_sync=None  # TODO: Implement last sync retrieval
    )

