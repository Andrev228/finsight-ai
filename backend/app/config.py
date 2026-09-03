"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "local"
    log_level: str = "info"

    database_url: str = "postgresql+asyncpg://finsight:finsight@db:5432/finsight"
    redis_url: str = "redis://redis:6379/0"

    plaid_client_id: str = ""
    plaid_secret: str = ""
    plaid_env: str = "sandbox"

    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_api_version: str = "2024-10-21"
    azure_openai_deployment: str = "gpt-4o-mini"


settings = Settings()
