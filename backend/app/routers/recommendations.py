"""Recommendation endpoints."""

from fastapi import APIRouter

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.post("/generate")
async def generate_recommendation():
    """
    Generates one recommendation for the user.
    
    Fetches profile, fetches latest positions, generates, and then stores in DB.
    
    TODO: Implement recommendation generation logic.
    """
    return {"message": "Not implemented yet"}


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

