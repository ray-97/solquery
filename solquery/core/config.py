# solquery/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # Core API Keys needed by SolQuery backend
    HELIUS_API_KEY: str = "YOUR_HELIUS_API_KEY_FALLBACK"
    GOOGLE_GEMINI_API_KEY: str = "YOUR_GEMINI_API_KEY_FALLBACK"
    
    # Optional API Key for fetching text for sentiment analysis
    NEWS_API_KEY: Optional[str] = None 

    # Application settings
    DEFAULT_SOLANA_NETWORK: str = "mainnet-beta"
    LOG_LEVEL: str = "INFO"
    SOLQUERY_FASTAPI_PORT: int = 8000

    # Pydantic-settings configuration to load from .env file
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding='utf-8', extra='ignore')

settings = Settings()

# Optional: Startup checks/warnings for essential keys
if "FALLBACK" in settings.HELIUS_API_KEY or not settings.HELIUS_API_KEY:
    print("WARNING: CORE_CONFIG: HELIUS_API_KEY is using fallback or not set correctly in .env")
if "FALLBACK" in settings.GOOGLE_GEMINI_API_KEY or not settings.GOOGLE_GEMINI_API_KEY:
    print("WARNING: CORE_CONFIG: GOOGLE_GEMINI_API_KEY is using fallback or not set correctly in .env")
if not settings.NEWS_API_KEY:
    print("INFO: CORE_CONFIG: NEWS_API_KEY is not set in .env (optional, for sentiment text gathering).")