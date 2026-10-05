from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/shopmate"
    jwt_secret: str = "replace-this-development-jwt-secret"
    secret_key: str = "replace-this-development-secret-key"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    catalog_cache_ttl_seconds: int = 60
    groq_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "GROQ_API_KEY",
            "GROK_API_KEY",
            "SHOPMATE_GROQ_API_KEY",
        ),
    )
    groq_model: str = Field(
        default="openai/gpt-oss-20b",
        validation_alias=AliasChoices("GROQ_MODEL", "SHOPMATE_GROQ_MODEL"),
    )
    mcp_url: str = Field(
        default="http://127.0.0.1:8000/mcp",
        validation_alias=AliasChoices("MCP_URL", "SHOPMATE_MCP_URL"),
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="SHOPMATE_",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()