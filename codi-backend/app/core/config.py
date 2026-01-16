"""Application configuration using Pydantic Settings."""
from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application Settings
    app_env: str = "development"
    debug: bool = True
    secret_key: str = "change-me-in-production"
    api_base_url: str = "http://localhost:8000"

    # Database
    database_url: str = "postgresql+asyncpg://codi:codi_password@localhost:5432/codi_db"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # GitHub OAuth App
    github_client_id: str = ""
    github_client_secret: str = ""
    github_redirect_uri: str = "http://localhost:8000/api/auth/github/callback"

    # GitHub App (for repo operations)
    github_app_id: str = ""
    github_app_private_key_path: str = ""

    # =========================================================================
    # AI Configuration - Simplified to use Gemini 3 Flash
    # =========================================================================
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3-flash-preview"  # Primary model for all agent tasks

    # Encryption
    encryption_key: str = ""

    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # CORS
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:8080"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: any) -> List[str]:
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            import json
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [origin.strip() for origin in v.split(",")]
        return v

    # WebSocket
    ws_heartbeat_interval: int = 30

    # Deployment Settings
    github_pages_enabled: bool = True
    
    # GitHub Webhook
    github_webhook_secret: str = ""

    # Vercel OAuth
    vercel_client_id: str = ""
    vercel_client_secret: str = ""
    vercel_integration_slug: str = "codi"

    # Flutter Starter Template
    flutter_starter_template_repo: str = "https://github.com/codi-app/flutter-starter-template.git"

    # JWT Settings
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.app_env == "production"

    @property
    def sync_database_url(self) -> str:
        """Get synchronous database URL for Alembic."""
        return self.database_url.replace("+asyncpg", "")


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
