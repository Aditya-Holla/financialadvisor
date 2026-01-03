"""Application configuration from environment variables."""

from functools import lru_cache
from typing import Optional
from pathlib import Path
import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load .env file from backend directory
backend_dir = Path(__file__).parent.parent
env_file = backend_dir / ".env"

# Debug: Check if .env file exists
if env_file.exists():
    # Read file directly to debug
    try:
        with open(env_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            print(f"Reading .env file ({len(lines)} lines):")
            for i, line in enumerate(lines, 1):
                line_stripped = line.rstrip('\n\r')
                if 'LLM' in line or 'SUPABASE' in line:
                    # Show first 50 chars to avoid printing full keys
                    preview = line_stripped[:50] + ('...' if len(line_stripped) > 50 else '')
                    print(f"  Line {i}: {repr(preview)}")
    except Exception as e:
        print(f"Error reading .env file: {e}")
    
    # Load .env file
    result = load_dotenv(dotenv_path=env_file, override=True)
    print(f"load_dotenv result: {result}, env_file: {env_file}")
    
    # Debug: Check what's actually in the environment after loading
    llm_key = os.getenv("LLM_API_KEY")
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    print(f"After load_dotenv:")
    print(f"  SUPABASE_URL: {'✓' if supabase_url else '✗'}")
    print(f"  SUPABASE_KEY: {'✓' if supabase_key else '✗'} ({'first 10: ' + supabase_key[:10] + '...' if supabase_key else ''})")
    print(f"  LLM_API_KEY: {'✓' if llm_key else '✗'} ({'first 10: ' + llm_key[:10] + '...' if llm_key else ''})")
    print(f"  LLM_MODEL: {os.getenv('LLM_MODEL', 'NOT SET')}")
else:
    print(f"⚠ .env file not found at {env_file}")


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Environment
    ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    
    # Supabase
    SUPABASE_URL: Optional[str] = None
    SUPABASE_KEY: Optional[str] = None
    
    # Alpaca (Paper Trading)
    ALPACA_KEY: Optional[str] = None
    ALPACA_SECRET: Optional[str] = None
    ALPACA_BASE_URL: str = "https://paper-api.alpaca.markets"  # Default to paper trading
    
    # LLM Provider
    LLM_API_KEY: Optional[str] = None
    LLM_MODEL: str = "gpt-4"  # Default model
    
    model_config = SettingsConfigDict(
        env_file=str(env_file) if env_file.exists() else None,
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",  # Ignore extra environment variables (e.g., SUPABASE_ANON_KEY, SUPABASE_JWT_SECRET)
    )


_settings_cache = None

def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    This function is cached so settings are only loaded once.
    Use this as a FastAPI dependency: `settings: Settings = Depends(get_settings)`
    """
    global _settings_cache
    if _settings_cache is None:
        _settings_cache = Settings()
    return _settings_cache

def clear_settings_cache():
    """Clear the settings cache (useful for testing/reloading)."""
    global _settings_cache
    _settings_cache = None

