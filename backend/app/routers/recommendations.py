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
from app.services.recommendation_service import RecommendationService
from app.services.approval_service import ApprovalService

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.post("/generate", response_model=RecommendationResponse)
async def generate_recommendation(
    user: UserContext = Depends(get_current_user),
    intent_data: Optional[Dict[str, Any]] = Body(None, description="Optional user intent data")
):
    """
    Generates one recommendation for the user.
    
    Fetches profile, fetches latest positions, generates, and then stores in DB.
    
    Requires: Authorization: Bearer <token>
    
    Request Body (optional):
    {
      "type": "invest",  // "invest", "withdraw", "rebalance", "change_risk", etc.
      "amount": 1000.0,  // Optional: dollar amount
      "risk_change": 0.1,  // Optional: risk change (-1.0 to 1.0)
      "target": "AAPL",  // Optional: target symbol or goal
      "timeframe": "immediate"  // Optional: timeframe string
    }
    
    Response Contract:
    - recommendation_id: string (required) - Unique recommendation identifier
    - decision: string (required) - Decision type: "approve", "modify", "reject", "request_info", "defer"
    - status: string (required) - Recommendation status: "pending"
    - created_at: ISO datetime string (required) - When recommendation was created
    
    Example Response:
    {
      "recommendation_id": "rec-123",
      "decision": "approve",
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
    """
    service = RecommendationService()
    
    recommendation = await service.generate_recommendation(
        user_id=user.user_id,
        user_intent_data=intent_data
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
    Fetches most recent recommendation for the user.
    
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
    User approves recommendation, backend places trade w/ Alpaca.
    
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
async def reject_recommendation(recommendation_id: str):
    """
    User rejects the recommendation, no trade executed.
    
    TODO: Implement rejection logic.
    """
    return {"message": "Not implemented yet", "recommendation_id": recommendation_id}

