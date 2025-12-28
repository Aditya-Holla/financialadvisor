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
from app.auth import get_current_user
from app.models.user import UserContext
from app.models.common import RecommendationResponse
from app.models.errors import NotFoundError
from app.services.recommendation_service import RecommendationService

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


@router.get("/latest")
async def get_latest_recommendation():
    """
    Fetches most recent recommendation.
    
    TODO: Implement latest recommendation retrieval.
    """
    return {"message": "Not implemented yet"}


@router.post("/{recommendation_id}/approve")
async def approve_recommendation(recommendation_id: str):
    """
    User approves recommendation, backend places trade w/ Alpaca.
    
    TODO: Implement approval logic and trade execution.
    """
    return {"message": "Not implemented yet", "recommendation_id": recommendation_id}


@router.post("/{recommendation_id}/reject")
async def reject_recommendation(recommendation_id: str):
    """
    User rejects the recommendation, no trade executed.
    
    TODO: Implement rejection logic.
    """
    return {"message": "Not implemented yet", "recommendation_id": recommendation_id}

