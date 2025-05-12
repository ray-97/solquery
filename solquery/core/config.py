# solquery/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    HELIUS_API_KEY: str = "YOUR_HELIUS_API_KEY_FALLBACK" # Fallback if not in .env
    BITQUERY_API_KEY: str | None = None # Optional
    GOOGLE_GEMINI_API_KEY: str = "YOUR_GEMINI_API_KEY_FALLBACK"
    # Add other settings as needed, e.g., default Solana network

    # This allows loading from a .env file
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding='utf-8', extra='ignore')

settings = Settings()