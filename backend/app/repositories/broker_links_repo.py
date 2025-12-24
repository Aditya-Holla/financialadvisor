"""Repository for broker account links."""

from typing import Optional, Dict, Any
from supabase import Client
from app.db import get_supabase
from app.models.errors import NotFoundError, ExternalServiceError


def get_broker_link(user_id: str, supabase: Optional[Client] = None) -> Optional[Dict[str, Any]]:
    """
    Get broker link for user.
    
    Args:
        user_id: User ID
        supabase: Optional Supabase client
        
    Returns:
        Broker link dictionary or None if not found
    """
    # TODO: Implement broker link retrieval
    raise NotImplementedError("Broker link retrieval not yet implemented")


def create_broker_link(user_id: str, link_data: Dict[str, Any], supabase: Optional[Client] = None) -> Dict[str, Any]:
    """
    Create broker link for user.
    
    Args:
        user_id: User ID
        link_data: Broker link data
        supabase: Optional Supabase client
        
    Returns:
        Created broker link dictionary
    """
    # TODO: Implement broker link creation
    raise NotImplementedError("Broker link creation not yet implemented")


def delete_broker_link(user_id: str, supabase: Optional[Client] = None) -> None:
    """
    Delete broker link for user.
    
    Args:
        user_id: User ID
        supabase: Optional Supabase client
    """
    # TODO: Implement broker link deletion
    raise NotImplementedError("Broker link deletion not yet implemented")

