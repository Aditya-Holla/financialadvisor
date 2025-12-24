"""Authentication and user identity dependencies."""

import base64
import json
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.models.user import UserContext
from app.models.errors import AuthError

# HTTPBearer security scheme for extracting Bearer tokens
security = HTTPBearer()


def decode_jwt_payload(token: str) -> dict:
    """
    Decode JWT payload without verification (MVP approach).
    
    For MVP, we just extract the payload. In production, you should
    verify the signature using Supabase's JWT secret.
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded payload as dictionary
    """
    try:
        # JWT format: header.payload.signature
        parts = token.split('.')
        if len(parts) != 3:
            raise ValueError("Invalid JWT format")
        
        # Decode payload (second part)
        payload = parts[1]
        # Add padding if needed (base64 requires padding)
        payload += '=' * (4 - len(payload) % 4)
        decoded = base64.urlsafe_b64decode(payload)
        return json.loads(decoded)
    except Exception as e:
        raise AuthError(f"Invalid token format: {str(e)}", "INVALID_TOKEN")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UserContext:
    """
    Get current authenticated user from Bearer token.
    
    MVP approach: Extracts user_id and email from Supabase JWT token
    without full signature verification.
    
    Args:
        credentials: HTTP Bearer token credentials from Authorization header
        
    Returns:
        UserContext with user_id and optional email
        
    Raises:
        AuthError: If token is missing, invalid, or user_id not found
    """
    token = credentials.credentials
    
    try:
        # Decode JWT payload
        payload = decode_jwt_payload(token)
        
        # Extract user_id (Supabase uses 'sub' or 'user_id' in JWT)
        user_id = payload.get('sub') or payload.get('user_id')
        if not user_id:
            raise AuthError("Token missing user_id", "MISSING_USER_ID")
        
        # Extract email (optional)
        email = payload.get('email') or payload.get('user_email')
        
        return UserContext(user_id=str(user_id), email=email)
        
    except AuthError:
        # Re-raise AuthError as-is
        raise
    except Exception as e:
        # Wrap other errors as AuthError
        raise AuthError(f"Authentication failed: {str(e)}", "AUTH_FAILED")

