"""Repository for portfolio position snapshots."""

from typing import Optional, Dict, Any, List
from datetime import datetime
from supabase import Client
from app.db import get_supabase
from app.models.errors import NotFoundError, ExternalServiceError


def create_snapshot(user_id: str, snapshot_data: Dict[str, Any], supabase: Optional[Client] = None) -> Dict[str, Any]:
    """
    Create a portfolio position snapshot.
    
    Args:
        user_id: User ID
        snapshot_data: Snapshot data (positions_json, cash, as_of timestamp)
        supabase: Optional Supabase client
        
    Returns:
        Created snapshot dictionary
    """
    # TODO: Implement snapshot creation
    raise NotImplementedError("Snapshot creation not yet implemented")


def get_latest_snapshot(user_id: str, supabase: Optional[Client] = None) -> Optional[Dict[str, Any]]:
    """
    Get the most recent snapshot for user.
    
    Args:
        user_id: User ID
        supabase: Optional Supabase client
        
    Returns:
        Latest snapshot dictionary or None if not found
        
    Raises:
        ExternalServiceError: If database query fails
    """
    if supabase is None:
        supabase = get_supabase()
    
    try:
        response = (
            supabase.table("snapshots")
            .select("*")
            .eq("user_id", user_id)
            .order("as_of", desc=True)
            .limit(1)
            .execute()
        )
        
        if not response.data or len(response.data) == 0:
            return None
        
        return response.data[0]
    except Exception as e:
        raise ExternalServiceError(
            f"Failed to get latest snapshot: {str(e)}",
            "SNAPSHOT_QUERY_ERROR"
        )


def get_snapshot_history(user_id: str, days: int = 30, supabase: Optional[Client] = None) -> List[Dict[str, Any]]:
    """
    Get snapshot history for user.
    
    Args:
        user_id: User ID
        days: Number of days of history to retrieve
        supabase: Optional Supabase client
        
    Returns:
        List of snapshot dictionaries
    """
    # TODO: Implement snapshot history retrieval
    raise NotImplementedError("Snapshot history retrieval not yet implemented")

