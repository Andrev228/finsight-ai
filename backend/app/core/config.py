"""Application configuration loaded from environment variables."""

from pathlib import Path
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(BACKEND_DIR / ".env", PROJECT_DIR / ".env"),
        extra="ignore",
    )

    app_env: str = "local"
    log_level: str = "info"
    frontend_origin: str = "http://localhost:3000"

    database_url: str = "postgresql+asyncpg://finsight:finsight@db:5432/finsight"
    redis_url: str = "redis://redis:6379/0"

    plaid_client_id: str = ""
    plaid_secret: str = ""
    plaid_env: Literal["sandbox"] = "sandbox"
    plaid_client_user_id: str = "local-development-user"
    plaid_token_encryption_key: SecretStr = SecretStr("")

    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_api_version: str = "2024-10-21"
    azure_openai_deployment: str = "gpt-4o-mini"

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.database_url.startswith("postgresql://"):
            return self.database_url.replace(
                "postgresql://",
                "postgresql+psycopg://",
                1,
            )
        return self.database_url


settings = Settings()
