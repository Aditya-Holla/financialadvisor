"""Application configuration from environment variables."""

from functools import lru_cache
from typing import Optional
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load .env file if it exists
load_dotenv()


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
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    This function is cached so settings are only loaded once.
    Use this as a FastAPI dependency: `settings: Settings = Depends(get_settings)`
    """
    return Settings()

