"""Health check endpoint."""

from fastapi import APIRouter, Depends
from app.models.common import HealthResponse
from app.config import Settings, get_settings

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthResponse)
async def health_check(settings: Settings = Depends(get_settings)):
    """
    Simple uptime check, returns 'ok'.
    
    Example of using settings as a dependency.
    """
    return {"status": "ok"}


@router.get("/llm-status")
async def llm_status():
    """
    Check LLM integration status.
    
    Useful for debugging LLM configuration.
    """
    import os
    import re
    from pathlib import Path
    from app.integrations.llm import LLMIntegration
    from app.config import get_settings, clear_settings_cache
    
    # Debug: Check .env file directly
    # From app/routers/health.py: go up to app/, then to backend/
    backend_dir = Path(__file__).parent.parent.parent
    env_file = backend_dir / ".env"
    env_file_exists = env_file.exists()
    env_has_key = False
    env_key_value = None
    env_file_content_preview = None
    
    if env_file_exists:
        try:
            with open(env_file, 'r') as f:
                content = f.read()
                env_file_content_preview = content[:200]  # First 200 chars for debugging
                # Check for LLM_API_KEY with various formats
                env_has_key = bool(re.search(r'LLM_API_KEY\s*=', content, re.IGNORECASE))
                # Try to extract the value
                match = re.search(r'LLM_API_KEY\s*=\s*([^\s#\n]+)', content, re.IGNORECASE)
                if match:
                    env_key_value = match.group(1)
                    # Remove quotes if present
                    env_key_value = env_key_value.strip('"\'')
        except Exception as e:
            env_file_content_preview = f"Error reading file: {str(e)}"
    
    # Check environment variable directly (after load_dotenv)
    os_env_has_key = os.getenv("LLM_API_KEY") is not None
    os_env_value_preview = None
    if os.getenv("LLM_API_KEY"):
        os_env_value = os.getenv("LLM_API_KEY")
        os_env_value_preview = os_env_value[:10] + "..." if len(os_env_value) > 10 else os_env_value
    
    # Get settings
    settings = get_settings()
    llm = LLMIntegration()
    
    return {
        "has_api_key": settings.LLM_API_KEY is not None,
        "api_key_preview": settings.LLM_API_KEY[:10] + "..." if settings.LLM_API_KEY and len(settings.LLM_API_KEY) > 10 else None,
        "model": settings.LLM_MODEL,
        "is_available": llm.is_available(),
        "client_initialized": llm.client is not None,
        "debug": {
            "env_file_exists": env_file_exists,
            "env_file_path": str(env_file),
            "env_file_has_key": env_has_key,
            "env_key_value_preview": env_key_value[:10] + "..." if env_key_value and len(env_key_value) > 10 else env_key_value,
            "os_env_has_key": os_env_has_key,
            "os_env_value_preview": os_env_value_preview,
            "settings_has_key": settings.LLM_API_KEY is not None,
            "env_file_content_preview": env_file_content_preview
        }
    }

