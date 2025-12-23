"""Portfolio endpoints."""

from fastapi import APIRouter

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.post("/refresh")
async def refresh_portfolio():
    """
    Pulls latest positions/cash from Alpaca, stores snapshot.
    
    TODO: Implement portfolio refresh from broker integration.
    """
    return {"message": "Not implemented yet"}


@router.get("/latest")
async def get_latest_portfolio():
    """
    Returns most recent positions snapshot.
    
    TODO: Implement latest portfolio retrieval from database.
    """
    return {"message": "Not implemented yet"}

