from functools import cache

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: SecretStr
    database_url: SecretStr
    auth_database_url: SecretStr
    llm_model: str = "claude-sonnet-4-6"
    log_level: str = "INFO"
    app_env: str = "production"

    @field_validator("database_url", "auth_database_url", mode="before")
    @classmethod
    def use_psycopg_driver(cls, url: str) -> str:
        # Supabase gives postgresql://, SQLAlchemy needs the driver name to pick psycopg 3
        if url.startswith("postgresql://"):
            return "postgresql+psycopg://" + url.removeprefix("postgresql://")
        return url


@cache
def get_settings() -> Settings:
    return Settings()
