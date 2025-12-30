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
env_example_file = backend_dir / ".env.example"

# Explicitly check and load ONLY .env (not .env.example)
if env_file.exists():
    # Load .env file with explicit path and override
    result = load_dotenv(dotenv_path=str(env_file.resolve()), override=True)
    print(f"✓ Loaded .env from: {env_file.resolve()}")
    print(f"  File exists: {env_file.exists()}")
    print(f"  Absolute path: {env_file.resolve()}")
    
    # Read file directly to verify contents
    try:
        with open(env_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            print(f"  File has {len(lines)} lines")
            # Check for placeholder values
            for i, line in enumerate(lines, 1):
                line_stripped = line.rstrip('\n\r')
                if 'LLM_API_KEY' in line and ('your-' in line.lower() or 'placeholder' in line.lower()):
                    print(f"  ⚠ WARNING: Line {i} appears to have placeholder value!")
                    preview = line_stripped[:60] + ('...' if len(line_stripped) > 60 else '')
                    print(f"    {preview}")
    except Exception as e:
        print(f"  Error reading .env file: {e}")
else:
    print(f"⚠ .env file not found at {env_file.resolve()}")
    if env_example_file.exists():
        print(f"⚠ .env.example exists - copy it to .env and add your values")

# Debug: Check what's actually in the environment after loading
llm_key = os.getenv("LLM_API_KEY")
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

print(f"After load_dotenv:")
print(f"  SUPABASE_URL: {'✓' if supabase_url else '✗'}")
if supabase_url:
    print(f"    Value: {supabase_url[:50]}...")
print(f"  SUPABASE_KEY: {'✓' if supabase_key else '✗'}")
if supabase_key:
    print(f"    Starts with: {supabase_key[:20]}...")
print(f"  LLM_API_KEY: {'✓' if llm_key else '✗'}")
if llm_key:
    print(f"    Starts with: {llm_key[:20]}...")
    # Check if it's a placeholder
    if llm_key.startswith("your-") or "placeholder" in llm_key.lower():
        print(f"    ⚠ WARNING: LLM_API_KEY appears to be a placeholder!")
print(f"  LLM_MODEL: {os.getenv('LLM_MODEL', 'NOT SET')}")


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

