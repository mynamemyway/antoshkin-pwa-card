# app/config.py

"""
Application configuration module.

Loads settings from environment variables using pydantic-settings.
All sensitive data (API keys, secrets) should be stored in .env file.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Attributes:
        DATABASE_URL: Database connection string (default: SQLite)
        SMS_API_KEY: API key for SMS gateway service
        SMS_SENDER_NAME: Sender name for SMS messages
        SMS_TEST_MODE: Test mode flag for SMS (True = stub, False = real SMS)
        SECRET_KEY: Secret key for session management
        DEBUG: Debug mode flag (True for development)
    """

    # Database
    DATABASE_URL: str = "sqlite:///./loyalty.db"

    # SMS Service
    SMS_API_KEY: str = ""
    SMS_SENDER_NAME: str = "Antoshkin"
    SMS_TEST_MODE: bool = True

    # Security
    SECRET_KEY: str = "change-me-in-production"

    # App Settings
    DEBUG: bool = True

    class Config:
        """Pydantic config for environment variable loading."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()
