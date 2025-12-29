"""Repository for investment recommendations."""

from typing import Optional, Dict, Any, List
from supabase import Client
from app.db import get_supabase
from app.models.errors import NotFoundError, ExternalServiceError


def create_recommendation(user_id: str, rec_data: Dict[str, Any], supabase: Optional[Client] = None) -> Dict[str, Any]:
    """
    Create a new recommendation.
    
    Args:
        user_id: User ID
        rec_data: Recommendation data (decision, proposal_json, status, etc.)
        supabase: Optional Supabase client
        
    Returns:
        Created recommendation dictionary
        
    Raises:
        ExternalServiceError: If database operation fails
    """
    if supabase is None:
        supabase = get_supabase()
    
    # Ensure user_id is in the recommendation data
    rec_data["user_id"] = user_id
    
    try:
        response = supabase.table("recommendations").insert(rec_data).execute()
        
        if not response.data or len(response.data) == 0:
            raise ExternalServiceError(
                "Recommendation creation returned no data",
                "RECOMMENDATION_CREATE_ERROR"
            )
        
        return response.data[0]
    except ExternalServiceError:
        raise
    except Exception as e:
        raise ExternalServiceError(
            f"Failed to create recommendation: {str(e)}",
            "RECOMMENDATION_CREATE_ERROR"
        )


def get_recommendation(recommendation_id: str, supabase: Optional[Client] = None) -> Optional[Dict[str, Any]]:
    """
    Get a specific recommendation by ID.
    
    Args:
        recommendation_id: Recommendation ID
        supabase: Optional Supabase client
        
    Returns:
        Recommendation dictionary or None if not found
        
    Raises:
        ExternalServiceError: If database query fails
    """
    if supabase is None:
        supabase = get_supabase()
    
    try:
        response = (
            supabase.table("recommendations")
            .select("*")
            .eq("id", recommendation_id)
            .execute()
        )
        
        if not response.data or len(response.data) == 0:
            return None
        
        return response.data[0]
    except Exception as e:
        raise ExternalServiceError(
            f"Failed to get recommendation: {str(e)}",
            "RECOMMENDATION_QUERY_ERROR"
        )


def get_latest_recommendation(user_id: str, supabase: Optional[Client] = None) -> Optional[Dict[str, Any]]:
    """
    Get the most recent recommendation for user.
    
    Args:
        user_id: User ID
        supabase: Optional Supabase client
        
    Returns:
        Latest recommendation dictionary or None if not found
        
    Raises:
        ExternalServiceError: If database query fails
    """
    if supabase is None:
        supabase = get_supabase()
    
    try:
        response = (
            supabase.table("recommendations")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        
        if not response.data or len(response.data) == 0:
            return None
        
        return response.data[0]
    except Exception as e:
        raise ExternalServiceError(
            f"Failed to get latest recommendation: {str(e)}",
            "RECOMMENDATION_QUERY_ERROR"
        )


def get_recommendation_history(user_id: str, limit: int = 20, supabase: Optional[Client] = None) -> List[Dict[str, Any]]:
    """
    Get recommendation history for user.
    
    Args:
        user_id: User ID
        limit: Maximum number of recommendations to return
        supabase: Optional Supabase client
        
    Returns:
        List of recommendation dictionaries
    """
    # TODO: Implement recommendation history retrieval
    raise NotImplementedError("Recommendation history retrieval not yet implemented")

