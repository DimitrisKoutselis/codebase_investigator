from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API Keys
    gemini_api_key: str = Field(default="", validation_alias="GEMINI_API_KEY")
    mistral_api_key: str | None = Field(
        default=None, validation_alias="MISTRAL_API_KEY"
    )

    # LangSmith (optional tracing)
    langchain_tracing_v2: bool = Field(
        default=False, validation_alias="LANGCHAIN_TRACING_V2"
    )
    langsmith_api_key: str | None = Field(
        default=None, validation_alias="LANGSMITH_API_KEY"
    )
    langchain_project: str = Field(
        default="Codebase Investigator", validation_alias="LANGCHAIN_PROJECT"
    )

    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379", validation_alias="REDIS_URL"
    )
    redis_ttl_seconds: int = Field(default=3600, validation_alias="REDIS_TTL_SECONDS")

    # FAISS
    faiss_index_path: str = Field(
        default="./data/faiss_indexes", validation_alias="FAISS_INDEX_PATH"
    )

    # Git
    repos_base_path: str = Field(default="./repos", validation_alias="REPOS_BASE_PATH")

    # MCP Servers
    mcp_filesystem_enabled: bool = Field(
        default=True, validation_alias="MCP_FILESYSTEM_ENABLED"
    )
    mcp_github_enabled: bool = Field(
        default=True, validation_alias="MCP_GITHUB_ENABLED"
    )
    github_token: str | None = Field(default=None, validation_alias="GITHUB_TOKEN")

    # Server
    host: str = Field(default="0.0.0.0", validation_alias="HOST")
    port: int = Field(default=8000, validation_alias="PORT")
    debug: bool = Field(default=False, validation_alias="DEBUG")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
