"""User identity endpoint.

Frontend Response Contract:
GET /me

Response: MeResponse
{
  "user_id": "user-123",
  "email": "user@example.com",
  "broker_linked": false,
  "last_sync": "2024-01-15T10:30:00"  // ISO datetime or null
}

Example Response:
{
  "user_id": "user-123",
  "email": "user@example.com",
  "broker_linked": true,
  "last_sync": "2024-01-15T10:30:00"
}
"""

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
    
    Response Contract:
    - user_id: string (required) - User's unique identifier
    - email: string | null - User's email address
    - broker_linked: boolean (required) - Whether broker account is linked
    - last_sync: ISO datetime string | null - Last portfolio sync timestamp
    
    Example Response:
    {
      "user_id": "user-123",
      "email": "user@example.com",
      "broker_linked": true,
      "last_sync": "2024-01-15T10:30:00"
    }
    """
    # TODO: Check broker_linked status from database
    # TODO: Get last_sync from database
    
    return MeResponse(
        user_id=user.user_id,
        email=user.email,
        broker_linked=False,  # TODO: Implement broker link check
        last_sync=None  # TODO: Implement last sync retrieval
    )

