"""Supabase database client wrapper."""

from functools import lru_cache
from typing import Optional
from supabase import create_client, Client
from app.config import Settings, get_settings
from app.models.errors import ExternalServiceError


@lru_cache()
def get_supabase() -> Client:
    """
    Get Supabase client instance (cached singleton).
    
    Returns:
        Supabase Client instance
        
    Raises:
        ExternalServiceError: If Supabase URL or key is not configured
    """
    settings = get_settings()
    
    if not settings.SUPABASE_URL:
        raise ExternalServiceError(
            "SUPABASE_URL not configured",
            "MISSING_SUPABASE_URL"
        )
    
    if not settings.SUPABASE_KEY:
        raise ExternalServiceError(
            "SUPABASE_KEY not configured",
            "MISSING_SUPABASE_KEY"
        )
    
    try:
        client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        return client
    except Exception as e:
        raise ExternalServiceError(
            f"Failed to create Supabase client: {str(e)}",
            "SUPABASE_CONNECTION_ERROR"
        )

