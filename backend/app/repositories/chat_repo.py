"""Repository for tutor chat messages."""

from typing import Optional, Dict, Any, List
from supabase import Client
from app.db import get_supabase
from app.models.errors import NotFoundError, ExternalServiceError


def create_chat_message(user_id: str, message_data: Dict[str, Any], supabase: Optional[Client] = None) -> Dict[str, Any]:
    """
    Create a chat message.
    
    Args:
        user_id: User ID
        message_data: Message data (recommendation_id, role, content, etc.)
        supabase: Optional Supabase client
        
    Returns:
        Created chat message dictionary
    """
    # TODO: Implement chat message creation
    raise NotImplementedError("Chat message creation not yet implemented")


def get_chat_history(user_id: str, recommendation_id: Optional[str] = None, supabase: Optional[Client] = None) -> List[Dict[str, Any]]:
    """
    Get chat history for user.
    
    Args:
        user_id: User ID
        recommendation_id: Optional recommendation ID to filter by
        supabase: Optional Supabase client
        
    Returns:
        List of chat message dictionaries
    """
    # TODO: Implement chat history retrieval
    raise NotImplementedError("Chat history retrieval not yet implemented")

