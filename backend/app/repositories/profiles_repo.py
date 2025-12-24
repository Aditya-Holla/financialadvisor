"""Repository for user profiles."""

from typing import Optional, Dict, Any
from supabase import Client
from app.db import get_supabase
from app.models.errors import NotFoundError, ExternalServiceError


def get_profile(user_id: str, supabase: Optional[Client] = None) -> Optional[Dict[str, Any]]:
    """
    Get user profile by user_id.
    
    Args:
        user_id: User ID
        supabase: Optional Supabase client (will use get_supabase() if not provided)
        
    Returns:
        Profile dictionary or None if not found
        
    Raises:
        ExternalServiceError: If database query fails
    """
    if supabase is None:
        supabase = get_supabase()
    
    try:
        response = supabase.table("profiles").select("*").eq("user_id", user_id).execute()
        
        if not response.data or len(response.data) == 0:
            return None
        
        return response.data[0]
    except Exception as e:
        raise ExternalServiceError(
            f"Failed to get profile: {str(e)}",
            "PROFILE_QUERY_ERROR"
        )


def upsert_profile(user_id: str, profile_data: Dict[str, Any], supabase: Optional[Client] = None) -> Dict[str, Any]:
    """
    Create or update user profile.
    
    Args:
        user_id: User ID
        profile_data: Profile data dictionary (risk_level, horizon, goal, constraints, etc.)
        supabase: Optional Supabase client (will use get_supabase() if not provided)
        
    Returns:
        Updated profile dictionary
        
    Raises:
        ExternalServiceError: If database operation fails
    """
    if supabase is None:
        supabase = get_supabase()
    
    # Ensure user_id is in the profile data
    profile_data["user_id"] = user_id
    
    try:
        response = supabase.table("profiles").upsert(profile_data).execute()
        
        if not response.data or len(response.data) == 0:
            raise ExternalServiceError(
                "Profile upsert returned no data",
                "PROFILE_UPSERT_ERROR"
            )
        
        return response.data[0]
    except ExternalServiceError:
        raise
    except Exception as e:
        raise ExternalServiceError(
            f"Failed to upsert profile: {str(e)}",
            "PROFILE_UPSERT_ERROR"
        )

