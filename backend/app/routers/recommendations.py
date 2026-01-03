"""Recommendation endpoints.

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
from app.models.common import RecommendationResponse, LatestRecommendationResponse, ApprovalResponse
from app.models.errors import NotFoundError, ValidationError
from app.services.chat_service import ChatService
from app.services.approval_service import ApprovalService

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


class IntentDataRequest(BaseModel):
    """Optional user intent data for recommendation generation."""
    type: Optional[str] = None
    amount: Optional[float] = None
    risk_change: Optional[float] = None
    target: Optional[str] = None
    timeframe: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@router.post("/generate", response_model=RecommendationResponse)
async def generate_recommendation(
    user: UserContext = Depends(get_current_user),
    intent_data: Optional[IntentDataRequest] = Body(default=None, embed=False)
):
    """
    Generates portfolio allocation example through orchestrator/chat flow.
    
    This endpoint routes through ChatService.handle_user_request() which:
    1. Calls orchestrator (which calls guardrail agent FIRST)
    2. Routes based on guardrail decision
    3. Only generates recommendations if guardrail returns ALLOW
    
    Constraints:
    - Routes through orchestrator/chat flow (cannot bypass)
    - Guardrail agent is called FIRST by orchestrator
    - Only generates if guardrail returns ALLOW
    - Returns educational examples, not personalized financial advice
    
    Requires: Authorization: Bearer <token>
    
    Request Body (optional - can be empty {} or omitted):
    {
      "type": "invest",  // REQUIRED for recommendations: "invest" or "get_advice"
                         // If omitted or "other", routes to educational mode
      "amount": 1000.0,  // Optional: dollar amount
      "risk_change": 0.1,  // Optional: risk change (-1.0 to 1.0)
      "target": "AAPL",  // Optional: target symbol or goal
      "timeframe": "immediate"  // Optional: timeframe string
    }
    
    Note: Education precedes examples. If intent type is missing, ambiguous, or "other",
    the system defaults to educational mode (tutor agent) and does NOT generate recommendations.
    Only explicit "invest" or "get_advice" intents trigger recommendation flows.
    
    Response Contract:
    - recommendation_id: string (required) - Unique recommendation identifier
    - decision: string (required) - Decision type: "approve", "modify", "reject", "request_info", "defer"
    - status: string (required) - Recommendation status: "pending"
    - created_at: ISO datetime string (required) - When recommendation was created
    
    Example Response (ALLOW):
    {
      "recommendation_id": "rec-123",
      "decision": "approve",
      "status": "pending",
      "created_at": "2024-01-15T10:30:00"
    }
    
    Example Response (BLOCK - no recommendation generated):
    {
      "recommendation_id": "",
      "decision": "reject",
      "status": "pending",
      "created_at": "2024-01-15T10:30:00"
    }
    
    Error Responses:
    - 404 NotFoundError: Profile or snapshot not found
      {
        "code": "PROFILE_NOT_FOUND",
        "message": "User profile not found",
        "details": null
      }
    - 400 ExternalServiceError: Guardrail blocked request
      {
        "code": "GUARDRAIL_NOT_ALLOW",
        "message": "Cannot generate portfolio allocation example. Guardrail status: BLOCK",
        "details": null
      }
    """
    from app.services.chat_service import ChatService
    from datetime import datetime, timezone
    
    # Convert Pydantic model to dict
    # Education precedes examples: do NOT default to recommendation intent
    user_intent_data = intent_data.model_dump(exclude_none=True) if intent_data else {}
    
    # Only trigger recommendation flows with explicit intent
    # Missing or ambiguous intent defaults to educational mode (handled by ChatService)
    # ChatService._build_user_intent() defaults to UserIntentType.OTHER if type is missing/invalid
    # Recommendation service only executes for GET_ADVICE or INVEST intents
    
    # Route through ChatService (which calls orchestrator, which calls guardrail FIRST)
    chat_service = ChatService()
    response = await chat_service.handle_user_request(
        user_id=user.user_id,
        user_intent_data=user_intent_data
    )
    
    # Extract recommendation_id if one was generated
    recommendation_id = response.get("recommendation_id", "")
    
    # If no recommendation was generated (e.g., BLOCK or WARN), return decision info
    if not recommendation_id:
        return RecommendationResponse(
            recommendation_id="",
            decision=response.get("decision", "reject"),
            status="pending",
            created_at=datetime.now(timezone.utc).isoformat()
        )
    
    # Load the recommendation to get full details
    from app.repositories import recommendations_repo
    recommendation = recommendations_repo.get_recommendation(recommendation_id)
    
    if not recommendation:
        # Recommendation was created but not found (shouldn't happen)
        return RecommendationResponse(
            recommendation_id=recommendation_id,
            decision=response.get("decision", "approve"),
            status="pending",
            created_at=datetime.now(timezone.utc).isoformat()
        )
    
    return RecommendationResponse(
        recommendation_id=str(recommendation.get("id", "")),
        decision=recommendation.get("decision", ""),
        status=recommendation.get("status", "pending"),
        created_at=recommendation.get("created_at", "")
    )


@router.get("/latest", response_model=LatestRecommendationResponse)
async def get_latest_recommendation(
    user: UserContext = Depends(get_current_user)
):
    """
    Fetches most recent recommendation for the user (read-only).
    
    Constraints:
    - Read-only endpoint (does not generate new recommendations)
    - Does not return financial advice (returns stored decision data only)
    - Does not bypass orchestrator (no generation happens here)
    
    This endpoint only retrieves existing stored recommendations.
    To generate new recommendations, use POST /recommendations/generate.
    
    Requires: Authorization: Bearer <token>
    
    Response Contract:
    - recommendation_id: string (required) - Unique recommendation identifier
    - decision: string (required) - Decision type: "approve", "modify", "reject", "request_info", "defer"
    - status: string (required) - Recommendation status: "pending", "approved", "rejected"
    - created_at: ISO datetime string (required) - When recommendation was created
    - guardrail_status: string | null - Guardrail result: "ALLOW", "WARN", "BLOCK", or null
    - has_proposal: boolean (required) - Whether recommendation includes a portfolio proposal
    
    Example Response (with proposal):
    {
      "recommendation_id": "rec-123",
      "decision": "approve",
      "status": "pending",
      "created_at": "2024-01-15T10:30:00",
      "guardrail_status": "ALLOW",
      "has_proposal": true
    }
    
    Example Response (blocked):
    {
      "recommendation_id": "rec-456",
      "decision": "reject",
      "status": "pending",
      "created_at": "2024-01-15T10:30:00",
      "guardrail_status": "BLOCK",
      "has_proposal": false
    }
    
    Error Responses:
    - 404 NotFoundError: No recommendations found
      {
        "code": "NO_RECOMMENDATIONS_FOUND",
        "message": "No recommendations found",
        "details": null
      }
    """
    from app.repositories import recommendations_repo
    from app.models.errors import NotFoundError
    
    recommendation = recommendations_repo.get_latest_recommendation(user.user_id)
    if not recommendation:
        raise NotFoundError("No recommendations found", "NO_RECOMMENDATIONS_FOUND")
    
    # Parse decision to check for proposal
    import json
    decision_data = json.loads(recommendation.get("decision_json", "{}"))
    has_proposal = decision_data.get("proposal") is not None
    
    return LatestRecommendationResponse(
        recommendation_id=str(recommendation.get("id", "")),
        decision=recommendation.get("decision", ""),
        status=recommendation.get("status", "pending"),
        created_at=recommendation.get("created_at", ""),
        guardrail_status=recommendation.get("guardrail_status"),
        has_proposal=has_proposal
    )


class ApprovalRequest(BaseModel):
    """Request model for approval endpoint."""
    confirmations: Optional[Dict[str, str]] = None  # confirmation_id -> confirmation_text/acknowledgement


@router.post("/{recommendation_id}/approve", response_model=ApprovalResponse)
async def approve_recommendation(
    recommendation_id: str,
    user: UserContext = Depends(get_current_user),
    request: ApprovalRequest = Body(...)
):
    """
    User approves existing recommendation (does not generate new recommendations).
    
    Constraints:
    - Only approves existing stored recommendations
    - Does not generate new recommendations or financial advice
    - Does not bypass orchestrator (no generation happens here)
    - Validates required confirmations before approval
    
    Requires all confirmations if the recommendation has warnings or blocks.
    - WARN: Requires checkbox confirmations (confirmation_text must match exactly)
    - BLOCK: Requires explicit override acknowledgements (override_acknowledgement must match exactly)
    
    Requires: Authorization: Bearer <token>
    
    Request Body:
    {
      "confirmations": {
        "conf_low_emergency_fund_investment": "I understand my emergency fund is below recommended levels and want to proceed"
      }
    }
    
    Response Contract:
    - recommendation_id: string (required) - Recommendation identifier
    - status: string (required) - Updated status: "approved"
    - message: string (required) - Success message
    
    Example Response (success):
    {
      "recommendation_id": "rec-123",
      "status": "approved",
      "message": "Recommendation approved successfully"
    }
    
    Error Responses:
    - 400 ValidationError: Missing or invalid confirmations
      {
        "code": "MISSING_CONFIRMATIONS",
        "message": "Required confirmations not provided",
        "details": null
      }
    - 404 NotFoundError: Recommendation not found
      {
        "code": "RECOMMENDATION_NOT_FOUND",
        "message": "Recommendation rec-123 not found",
        "details": null
      }
    """
    service = ApprovalService()
    
    try:
        recommendation = service.approve_recommendation(
            user_id=user.user_id,
            recommendation_id=recommendation_id,
            confirmations=request.confirmations
        )
        
        return ApprovalResponse(
            recommendation_id=recommendation_id,
            status=recommendation.get("status", "approved"),
            message="Recommendation approved successfully"
        )
    except ValidationError as e:
        raise
    except NotFoundError as e:
        raise


@router.post("/{recommendation_id}/reject")
async def reject_recommendation(
    recommendation_id: str,
    user: UserContext = Depends(get_current_user)
):
    """
    User rejects existing recommendation (removed for MVP).
    
    This endpoint is removed for MVP as it does not generate recommendations
    and is not critical for the core flow.
    
    Constraints:
    - Removed for MVP (not critical functionality)
    - Does not generate recommendations or financial advice
    - Can be re-implemented later if needed
    
    For MVP, users can simply not approve recommendations they don't want.
    """
    from app.models.errors import NotFoundError
    raise NotFoundError(
        "Rejection endpoint removed for MVP. Recommendations can be ignored if not approved.",
        "ENDPOINT_REMOVED_MVP"
    )

