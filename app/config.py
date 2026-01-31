"""Configuration management for RepeatNoMore application."""

from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # Application Settings
    app_name: str = Field(default="RepeatNoMore")
    log_level: str = Field(default="INFO")
    environment: str = Field(default="development")

    # PostgreSQL Vector Database (pgvector)
    postgres_host: str = Field(default="localhost")
    postgres_port: int = Field(default=5432)
    postgres_db: str = Field(default="repeatnomore")
    postgres_user: str = Field(default="repeatnomore")
    postgres_password: str = Field(default="repeatnomore")
    postgres_vector_table: str = Field(default="documents")

    # LLM Provider Selection
    llm_provider: str = Field(default="anthropic")  # anthropic | openai | cursor

    # Anthropic/Claude Settings
    anthropic_api_key: str = Field(default="")
    anthropic_model: str = Field(default="claude-sonnet-4-20250514")
    anthropic_max_tokens: int = Field(default=4096)

    # OpenAI/ChatGPT Settings
    openai_api_key: str = Field(default="")
    openai_model: str = Field(default="gpt-4-turbo-preview")
    openai_base_url: str = Field(default="")  # Optional: for Azure OpenAI

    # Cursor Settings
    cursor_api_key: str = Field(default="")
    cursor_model: str = Field(default="cursor-small")
    cursor_base_url: str = Field(default="https://api.cursor.sh/v1")

    # Embedding Settings (API-based)
    # Uses OpenAI-compatible API (OpenAI or Cursor)
    # Common models:
    #   - text-embedding-3-small (1536 dims, OpenAI)
    #   - text-embedding-3-large (3072 dims, OpenAI)
    #   - text-embedding-ada-002 (1536 dims, OpenAI legacy)
    embedding_model: str = Field(default="text-embedding-3-small")
    embedding_dimension: int = Field(default=1536)

    # RAG Settings
    chunk_size: int = Field(default=1000)
    chunk_overlap: int = Field(default=200)
    top_k_retrieval: int = Field(default=5)
    min_similarity_score: float = Field(default=0.3)

    # Azure Bot Framework (for Teams integration)
    microsoft_app_id: str = Field(default="")
    microsoft_app_password: str = Field(default="")
    bot_endpoint: str = Field(default="/api/messages")

    # Azure AD (for permissions)
    azure_ad_tenant_id: str = Field(default="")
    azure_ad_client_id: str = Field(default="")
    azure_ad_client_secret: str = Field(default="")

    # Permission Groups (Azure AD Group IDs)
    admin_group_id: str = Field(default="")
    contributor_group_id: str = Field(default="")

    # Discord Bot Settings
    discord_bot_token: str = Field(default="")
    discord_application_id: str = Field(default="")
    discord_guild_ids: List[str] = Field(default_factory=list)
    discord_command_prefix: str = Field(default="!")
    discord_enable_mentions: bool = Field(default=True)
    discord_admin_usernames: str = Field(
        default=""
    )  # Comma-separated Discord usernames

    # API Settings
    api_prefix: str = Field(default="/api")
    cors_origins: List[str] = Field(default=["*"])
    rate_limit_per_minute: int = Field(default=60)

    # Documentation Repository
    docs_repo_path: str = Field(default="./knowledge_base/docs")
    docs_git_enabled: bool = Field(default=False)
    docs_git_branch: str = Field(default="main")
    git_action_log_path: str = Field(default="./logs/git_actions.log")

    # Azure DevOps SSH Settings (preferred for git sync)
    azure_devops_ssh_url: str = Field(default="")
    azure_devops_ssh_key_path: str = Field(default="")

    # Azure DevOps PAT Settings (fallback for git sync)
    azure_devops_organization: str = Field(default="")
    azure_devops_project: str = Field(default="")
    azure_devops_repo: str = Field(default="")
    azure_devops_pat: str = Field(default="")

    # Monitoring
    prometheus_enabled: bool = Field(default=True)
    prometheus_port: int = Field(default=9090)

    # Security
    secret_key: str = Field(default="dev-secret-key-change-in-production")
    session_timeout_minutes: int = Field(default=30)

    # Budget Settings
    budget_monthly_limit: float = Field(default=50.0)
    budget_data_path: str = Field(default="./data/budget_tracking.json")
    budget_cost_per_llm_request: float = Field(default=0.0063)

    # Startup Indexing Settings
    reindex_on_startup: bool = Field(default=True)
    reindex_reset: bool = Field(default=False)  # If true, clears existing index before reindexing

    @field_validator("postgres_port", "prometheus_port")
    @classmethod
    def validate_port(cls, v: int) -> int:
        """Validate that port numbers are in valid range."""
        if v < 1 or v > 65535:
            raise ValueError(f"Port must be between 1 and 65535, got {v}")
        return v

    @field_validator("llm_provider")
    @classmethod
    def validate_llm_provider(cls, v: str) -> str:
        """Validate LLM provider name."""
        valid_providers = {"anthropic", "openai", "cursor"}
        if v.lower() not in valid_providers:
            raise ValueError(f"LLM provider must be one of: {valid_providers}")
        return v.lower()

    @property
    def postgres_url(self) -> str:
        """Get the PostgreSQL connection URL."""
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() == "development"

    @property
    def discord_enabled(self) -> bool:
        """Check if Discord integration is configured."""
        return bool(self.discord_bot_token)

    @property
    def budget_enabled(self) -> bool:
        """Check if budget tracking is enabled."""
        return self.budget_monthly_limit > 0

    @property
    def uses_cloud_llm(self) -> bool:
        """Check if using a cloud-based LLM provider (always true now)."""
        return True

    @property
    def llm_requires_api_key(self) -> bool:
        """Check if the configured LLM provider requires an API key (always true now)."""
        return True


@lru_cache()
def get_settings() -> Settings:
    """
    Get application settings (cached).

    Returns:
        Settings: Application configuration
    """
    return Settings()
