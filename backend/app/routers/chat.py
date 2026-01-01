"""Chat endpoints for conversational interactions and explanations.

Rules of Engagement:
- Agents are separate from FastAPI routers and services
- Business logic lives in services, agents orchestrate and coordinate
- LLM agents must never change numbers or decide trades
- Guardrails must be deterministic code, not LLM decisions
- All model outputs must be structured JSON (Pydantic models)
- Agents coordinate between integrations, services, and repositories
"""

from fastapi import APIRouter, Depends, Body
from typing import Optional, Dict, Any
from pydantic import BaseModel
from app.auth import get_current_user
from app.models.user import UserContext
from app.models.errors import NotFoundError
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    message: Optional[str] = None  # Conversational message
    recommendation_id: Optional[str] = None  # Legacy: specific recommendation ID for explanation


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    type: str  # "explanation", "recommendation", or "error"
    message: str  # Response message
    recommendation_id: Optional[str] = None  # Recommendation ID if one was generated
    data: Optional[Dict[str, Any]] = None  # Additional data


@router.post("", response_model=ChatResponse)
async def chat(
    user: UserContext = Depends(get_current_user),
    request: ChatRequest = Body(...)
):
    """
    Handle conversational input or get explanation for a recommendation.
    
    **Two modes:**
    1. **Conversational mode** (new): Send a message, get intelligent response
       - If message contains investment intent → generates recommendation
       - If message is a question → provides explanation/advice
    2. **Explanation mode** (legacy): Get explanation for specific recommendation
       - If recommendation_id provided → explains that recommendation
       - If neither message nor recommendation_id → explains latest recommendation
    
    Requires: Authorization: Bearer <token>
    
    **Request Body (conversational mode):**
    {
      "message": "I want to invest $1000"  // Conversational message
    }
    
    **Request Body (explanation mode - legacy):**
    {
      "recommendation_id": "rec-123"  // Optional: specific recommendation ID
    }
    // If recommendation_id is null/omitted, uses latest recommendation
    
    **Response Contract:**
    - type: string - "explanation", "recommendation", or "error"
    - message: string - Human-readable response message
    - recommendation_id: Optional[string] - Recommendation ID if one was generated
    - data: Optional[object] - Additional data (intent, recommendation details, etc.)
    
    **Example Response (conversational - action):**
    {
      "type": "recommendation",
      "message": "I've generated an investment recommendation for you...",
      "recommendation_id": "rec-123",
      "data": {
        "recommendation": {
          "id": "rec-123",
          "decision": "approve",
          "status": "pending"
        },
        "intent": {
          "type": "invest",
          "amount": 1000.0
        }
      }
    }
    
    **Example Response (conversational - question):**
    {
      "type": "explanation",
      "message": "This recommendation has been approved...",
      "recommendation_id": "rec-123",
      "data": {
        "intent": {
          "type": "get_advice"
        }
      }
    }
    
    **Example Response (explanation mode - legacy):**
    {
      "type": "explanation",
      "message": "This recommendation has been approved and is ready for your review...",
      "recommendation_id": "rec-123",
      "data": null
    }
    
    **Error Responses:**
    - 400 ValidationError: Invalid request
      {
        "code": "EMPTY_MESSAGE",
        "message": "Message cannot be empty",
        "details": null
      }
    - 404 NotFoundError: No recommendations found
      {
        "code": "NO_RECOMMENDATIONS_FOUND",
        "message": "No recommendations found",
        "details": null
      }
    """
    service = ChatService()
    
    # Determine mode: conversational or explanation
    if request.message:
        # Conversational mode - handle message
        result = await service.handle_conversational_input(
            user_id=user.user_id,
            message=request.message
        )
        return ChatResponse(
            type=result["type"],
            message=result["message"],
            recommendation_id=result.get("recommendation_id"),
            data=result.get("data")
        )
    else:
        # Explanation mode (legacy) - explain recommendation
        explanation = await service.explain_recommendation(
            user_id=user.user_id,
            recommendation_id=request.recommendation_id
        )
        return ChatResponse(
            type="explanation",
            message=explanation,
            recommendation_id=request.recommendation_id,
            data=None
        )

