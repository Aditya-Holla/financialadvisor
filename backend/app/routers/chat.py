"""Chat endpoints for explaining recommendations.

Rules of Engagement:
- Agents are separate from FastAPI routers and services
- Business logic lives in services, agents orchestrate and coordinate
- LLM agents must never change numbers or decide trades
- Guardrails must be deterministic code, not LLM decisions
- All model outputs must be structured JSON (Pydantic models)
- Agents coordinate between integrations, services, and repositories
"""

from fastapi import APIRouter, Depends, Body
from typing import Optional
from pydantic import BaseModel
from app.auth import get_current_user
from app.models.user import UserContext
from app.models.errors import NotFoundError
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    recommendation_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    explanation: str


@router.post("", response_model=ChatResponse)
async def chat(
    user: UserContext = Depends(get_current_user),
    request: ChatRequest = Body(...)
):
    """
    Get explanation for a recommendation.
    
    If recommendation_id is provided, explains that specific recommendation.
    Otherwise, explains the latest recommendation for the user.
    
    Requires: Authorization: Bearer <token>
    
    Request Body:
    {
      "recommendation_id": "rec-123"  // Optional: specific recommendation ID
    }
    // If recommendation_id is null/omitted, uses latest recommendation
    
    Response Contract:
    - explanation: string (required) - Human-readable explanation text
    
    Example Response:
    {
      "explanation": "This recommendation has been approved and is ready for your review. The proposed portfolio allocation is: 60.0% stocks, 30.0% bonds, 10.0% cash. This involves 1 trade(s) to achieve this allocation."
    }
    
    Example Response (with warnings):
    {
      "explanation": "This recommendation has been modified with additional considerations. Please review the changes carefully. This recommendation has warnings that require your attention. Reasons: Your emergency fund (2.0 months) is below recommended minimum. Consider building emergency fund first. The proposed portfolio allocation is: 60.0% stocks, 30.0% bonds, 10.0% cash."
    }
    
    Example Response (blocked):
    {
      "explanation": "This recommendation has been rejected based on safety guardrails. See below for details. This recommendation was blocked by safety guardrails. Reasons: You have negative cash flow, so investing now is not recommended."
    }
    
    Error Responses:
    - 404 NotFoundError: No recommendations found or recommendation not found
      {
        "code": "NO_RECOMMENDATIONS_FOUND",
        "message": "No recommendations found",
        "details": null
      }
    """
    service = ChatService()
    
    explanation = await service.explain_recommendation(
        user_id=user.user_id,
        recommendation_id=request.recommendation_id
    )
    
    return ChatResponse(explanation=explanation)

