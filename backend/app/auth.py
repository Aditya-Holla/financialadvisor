"""Authentication and user identity dependencies."""

import base64
import json
import logging
from typing import Optional, Dict
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.models.user import UserContext
from app.models.errors import AuthError
from app.config import get_settings
import jwt
from jwt import PyJWKClient

# Set up logger
logger = logging.getLogger(__name__)

# HTTPBearer security scheme for extracting Bearer tokens
security = HTTPBearer()

# Cache JWKS clients per Supabase URL
_jwks_clients: Dict[str, PyJWKClient] = {}


def get_jwks_client(supabase_url: str) -> PyJWKClient:
    """
    Get or create JWKS client for Supabase URL.
    
    JWKS (JSON Web Key Set) is used to fetch public keys for verifying
    JWT tokens signed with the new ECC P-256 signing keys.
    
    Args:
        supabase_url: Supabase project URL
        
    Returns:
        PyJWKClient instance for fetching signing keys
    """
    if supabase_url not in _jwks_clients:
        # Construct JWKS endpoint URL
        # Supabase JWKS endpoint is at: https://<project>.supabase.co/auth/v1/.well-known/jwks.json
        base_url = supabase_url.rstrip('/')
        jwks_url = f"{base_url}/auth/v1/.well-known/jwks.json"
        logger.debug(f"Constructed JWKS URL: {jwks_url}")
        _jwks_clients[supabase_url] = PyJWKClient(jwks_url, cache_keys=True)
    return _jwks_clients[supabase_url]


def verify_supabase_jwt(token: str) -> dict:
    """
    Verify and decode Supabase JWT token using JWKS (new system) or legacy secret.
    
    This function supports both:
    1. New JWKS system: Fetches public keys from Supabase's JWKS endpoint
    2. Legacy HS256 secret: Falls back to shared secret if JWKS fails
    
    Args:
        token: JWT token string from Supabase
        
    Returns:
        Decoded payload as dictionary
        
    Raises:
        AuthError: If token is invalid or verification fails
    """
    settings = get_settings()
    
    try:
        # Decode header to check algorithm and key ID
        try:
            header = jwt.get_unverified_header(token)
        except Exception as e:
            logger.error(f"Failed to decode token header: {str(e)}")
            raise AuthError(f"Invalid token header: {str(e)}", "INVALID_TOKEN_HEADER")
        
        algorithm = header.get('alg', 'HS256')
        kid = header.get('kid')  # Key ID for JWKS (present in new tokens)
        
        logger.debug(f"Token algorithm: {algorithm}, kid: {kid}, SUPABASE_URL configured: {bool(settings.SUPABASE_URL)}")
        
        # Try new JWKS system first (if kid is present and URL is configured)
        if kid and settings.SUPABASE_URL:
            try:
                logger.debug(f"Attempting JWKS verification with URL: {settings.SUPABASE_URL}")
                jwks_client = get_jwks_client(settings.SUPABASE_URL)
                signing_key = jwks_client.get_signing_key_from_jwt(token)
                
                # Verify with public key from JWKS
                # New tokens use ES256 (ECC P-256) or RS256 (RSA)
                payload = jwt.decode(
                    token,
                    signing_key.key,
                    algorithms=["ES256", "RS256", "ES384", "RS384"],  # Support ECC and RSA
                    options={
                        "verify_signature": True, 
                        "verify_exp": True,
                        "verify_aud": False  # Skip audience verification (Supabase tokens may have different audiences)
                    }
                )
                logger.debug("JWKS verification successful")
                return payload
            except jwt.ExpiredSignatureError:
                logger.warning("Token has expired (JWKS verification)")
                raise AuthError("Token has expired", "TOKEN_EXPIRED")
            except jwt.InvalidTokenError as e:
                logger.warning(f"JWKS verification failed: {str(e)}")
                # JWKS verification failed - try legacy secret as fallback ONLY if algorithm is HS256
                if settings.SUPABASE_JWT_SECRET and algorithm == "HS256":
                    logger.debug("Falling back to legacy HS256 secret")
                    # Fall through to legacy verification below
                    pass
                else:
                    raise AuthError(
                        f"JWKS verification failed: {str(e)}",
                        "TOKEN_VERIFICATION_FAILED"
                    )
            except Exception as jwks_error:
                logger.warning(f"JWKS fetch/parse error: {str(jwks_error)}")
                # JWKS fetch/parse error - try legacy secret as fallback ONLY if algorithm is HS256
                if not settings.SUPABASE_JWT_SECRET or algorithm != "HS256":
                    raise AuthError(
                        f"JWKS verification failed and no legacy secret configured or token is not HS256: {str(jwks_error)}",
                        "TOKEN_VERIFICATION_FAILED"
                    )
                logger.debug("Falling back to legacy HS256 secret after JWKS error")
                # Fall through to legacy verification below
        
        # Fallback to legacy HS256 secret (if configured)
        # This supports old tokens signed with the shared secret
        # Only try this if the token algorithm is HS256
        if settings.SUPABASE_JWT_SECRET and algorithm == "HS256":
            try:
                logger.debug("Attempting legacy HS256 verification")
                payload = jwt.decode(
                    token,
                    settings.SUPABASE_JWT_SECRET,
                    algorithms=["HS256"],
                    options={"verify_signature": True, "verify_exp": True}
                )
                logger.debug("Legacy HS256 verification successful")
                return payload
            except jwt.ExpiredSignatureError:
                logger.warning("Token has expired (legacy verification)")
                raise AuthError("Token has expired", "TOKEN_EXPIRED")
            except jwt.InvalidTokenError as e:
                logger.error(f"Legacy token verification failed: {str(e)}")
                raise AuthError(f"Invalid token: {str(e)}", "INVALID_TOKEN")
        
        # No verification configured - decode without verification (development only)
        # WARNING: This is insecure and should only be used in development
        logger.warning("No verification configured - decoding token without verification (INSECURE - development only)")
        parts = token.split('.')
        if len(parts) != 3:
            raise ValueError("Invalid JWT format")
        
        payload = parts[1]
        payload += '=' * (4 - len(payload) % 4)
        decoded = base64.urlsafe_b64decode(payload)
        return json.loads(decoded)
            
    except AuthError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in token verification: {str(e)}", exc_info=True)
        raise AuthError(f"Token verification failed: {str(e)}", "TOKEN_VERIFICATION_FAILED")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UserContext:
    """
    Get current authenticated user from Supabase JWT Bearer token.
    
    Verifies the Supabase JWT token and extracts user_id and email.
    
    Args:
        credentials: HTTP Bearer token credentials from Authorization header
        
    Returns:
        UserContext with user_id and optional email
        
    Raises:
        AuthError: If token is missing, invalid, expired, or user_id not found
    """
    token = credentials.credentials
    
    # Debug: Log token info (first 20 chars only for security)
    logger.debug(f"Received token (first 20 chars): {token[:20]}...")
    
    try:
        # Verify and decode JWT token
        payload = verify_supabase_jwt(token)
        
        # Extract user_id (Supabase uses 'sub' for user ID in JWT)
        user_id = payload.get('sub') or payload.get('user_id')
        if not user_id:
            logger.error("Token missing user_id. Payload keys: %s", list(payload.keys()))
            raise AuthError("Token missing user_id", "MISSING_USER_ID")
        
        # Extract email (Supabase stores it in 'email' field)
        email = payload.get('email') or payload.get('user_email')
        
        logger.debug(f"Successfully authenticated user: {user_id}, email: {email}")
        return UserContext(user_id=str(user_id), email=email)
        
    except AuthError as e:
        # Log auth errors for debugging
        logger.warning(f"Auth error: {e.message} (code: {e.code})")
        # Re-raise AuthError as-is (will be handled by exception handler in main.py)
        raise
    except Exception as e:
        # Log unexpected errors
        logger.error(f"Unexpected auth error: {str(e)}", exc_info=True)
        # Wrap other errors as AuthError
        raise AuthError(f"Authentication failed: {str(e)}", "AUTH_FAILED")

