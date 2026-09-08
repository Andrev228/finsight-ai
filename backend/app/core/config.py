"""Application configuration loaded from environment variables."""

from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(BACKEND_DIR / ".env", PROJECT_DIR / ".env"),
        extra="ignore",
    )

    app_env: Literal["local", "test", "production"] = "production"
    log_level: str = "info"
    frontend_origin: str = "http://localhost:3000"
    admin_api_key: SecretStr = SecretStr("")
    auth_jwt_secret: SecretStr = SecretStr("")
    auth_jwt_issuer: str = "finsight-ai"
    auth_jwt_audience: str = "finsight-ai-api"
    allow_insecure_local_auth: bool = False
    allow_insecure_local_admin: bool = False
    ai_requests_per_minute: int = 10

    database_url: str = "postgresql+asyncpg://finsight:finsight@db:5432/finsight"
    redis_url: str = "redis://redis:6379/0"

    plaid_client_id: str = ""
    plaid_secret: SecretStr = SecretStr("")
    plaid_env: Literal["sandbox"] = "sandbox"
    plaid_client_user_id: str = "local-development-user"
    app_encryption_key: SecretStr = Field(
        default=SecretStr(""),
        validation_alias=AliasChoices(
            "APP_ENCRYPTION_KEY",
            "PLAID_TOKEN_ENCRYPTION_KEY",
        ),
    )

    gemini_api_key: SecretStr = SecretStr("")
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    gemini_model: str = "gemini-3.6-flash"
    gemini_embedding_model: str = "gemini-embedding-001"

    stripe_secret_key: SecretStr = SecretStr("")
    stripe_webhook_secret: SecretStr = SecretStr("")
    stripe_price_id: str = ""
    stripe_success_url: str = "http://localhost:3000/?billing=success"
    stripe_cancel_url: str = "http://localhost:3000/?billing=cancelled"

    mcp_user_id: str = ""

    @property
    def sqlalchemy_database_url(self) -> str:
        for scheme in ("postgresql://", "postgresql+asyncpg://"):
            if self.database_url.startswith(scheme):
                return self.database_url.replace(
                    scheme,
                    "postgresql+psycopg://",
                    1,
                )
        return self.database_url


settings = Settings()
