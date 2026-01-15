import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Field names must match your environment variable names (case-insensitive by default)
    # or you can provide a default value as seen below.
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-fallback-secret-key-for-dev")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Configuration for loading from a .env file
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore"  # Ignore extra variables in .env that aren't defined here
    )

# Instantiate the settings object to be imported elsewhere
settings = Settings()
