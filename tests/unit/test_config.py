"""Unit tests for configuration module."""

import pytest
from app.config import Settings, get_settings


class TestSettings:
    """Test cases for Settings configuration."""

    def test_default_settings(self):
        """Test default settings values."""
        settings = Settings()

        assert settings.app_name == "RepeatNoMore"
        assert settings.log_level == "INFO"
        assert settings.environment == "development"
        assert settings.postgres_host == "localhost"
        assert settings.postgres_port == 5432
        assert settings.postgres_db == "repeatnomore"
        assert settings.postgres_user == "repeatnomore"

    def test_custom_settings(self):
        """Test creating settings with custom values."""
        settings = Settings(
            app_name="TestApp",
            log_level="DEBUG",
            environment="testing",
            postgres_host="test-postgres",
            postgres_port=5433
        )

        assert settings.app_name == "TestApp"
        assert settings.log_level == "DEBUG"
        assert settings.environment == "testing"
        assert settings.postgres_host == "test-postgres"
        assert settings.postgres_port == 5433

    def test_postgres_url_property(self):
        """Test postgres_url property construction."""
        settings = Settings(
            postgres_host="pg-server",
            postgres_port=5432,
            postgres_user="testuser",
            postgres_password="testpass",
            postgres_db="testdb"
        )

        assert settings.postgres_url == "postgresql://testuser:testpass@pg-server:5432/testdb"

    def test_is_production_property(self):
        """Test is_production property."""
        prod_settings = Settings(environment="production")
        dev_settings = Settings(environment="development")
        test_settings = Settings(environment="testing")

        assert prod_settings.is_production is True
        assert dev_settings.is_production is False
        assert test_settings.is_production is False

    def test_is_development_property(self):
        """Test is_development property."""
        prod_settings = Settings(environment="production")
        dev_settings = Settings(environment="development")
        test_settings = Settings(environment="testing")

        assert prod_settings.is_development is False
        assert dev_settings.is_development is True
        assert test_settings.is_development is False

    def test_environment_case_insensitive(self):
        """Test that environment checks are case-insensitive."""
        settings = Settings(environment="PRODUCTION")
        assert settings.is_production is True

        settings = Settings(environment="Development")
        assert settings.is_development is True

    def test_rag_settings(self):
        """Test RAG-specific settings."""
        settings = Settings(
            chunk_size=500,
            chunk_overlap=100,
            top_k_retrieval=3,
            min_similarity_score=0.8
        )

        assert settings.chunk_size == 500
        assert settings.chunk_overlap == 100
        assert settings.top_k_retrieval == 3
        assert settings.min_similarity_score == 0.8

    def test_embedding_settings(self):
        """Test embedding model settings."""
        settings = Settings(
            embedding_model="custom-model",
            embedding_dimension=512
        )

        assert settings.embedding_model == "custom-model"
        assert settings.embedding_dimension == 512

    def test_api_settings(self):
        """Test API configuration settings."""
        settings = Settings(
            api_prefix="/custom-api",
            cors_origins=["http://localhost:3000"],
            rate_limit_per_minute=120
        )

        assert settings.api_prefix == "/custom-api"
        assert settings.cors_origins == ["http://localhost:3000"]
        assert settings.rate_limit_per_minute == 120

    def test_docs_repo_settings(self):
        """Test documentation repository settings."""
        settings = Settings(
            docs_repo_path="/custom/docs",
            docs_git_enabled=True,
            docs_git_branch="develop"
        )

        assert settings.docs_repo_path == "/custom/docs"
        assert settings.docs_git_enabled is True
        assert settings.docs_git_branch == "develop"

    def test_get_settings_singleton(self):
        """Test that get_settings returns cached instance."""
        # Clear cache first
        get_settings.cache_clear()

        settings1 = get_settings()
        settings2 = get_settings()

        # Should be the same instance due to caching
        assert settings1 is settings2

    def test_postgres_vector_table(self):
        """Test PostgreSQL vector table name setting."""
        settings = Settings(postgres_vector_table="custom_documents")

        assert settings.postgres_vector_table == "custom_documents"

    def test_llm_provider_setting(self):
        """Test LLM provider configuration."""
        settings = Settings(llm_provider="anthropic")

        assert settings.llm_provider == "anthropic"

    def test_security_settings(self):
        """Test security-related settings."""
        settings = Settings(
            secret_key="test-secret-key-12345",
            session_timeout_minutes=60
        )

        assert settings.secret_key == "test-secret-key-12345"
        assert settings.session_timeout_minutes == 60

    def test_prometheus_settings(self):
        """Test monitoring/Prometheus settings."""
        settings = Settings(
            prometheus_enabled=False,
            prometheus_port=9091
        )

        assert settings.prometheus_enabled is False
        assert settings.prometheus_port == 9091


class TestSettingsValidation:
    """Test cases for settings validation."""

    def test_invalid_port_number(self):
        """Test that invalid port numbers are handled."""
        # Pydantic should handle validation
        with pytest.raises(Exception):
            Settings(postgres_port=-1)

    def test_cors_origins_type(self):
        """Test CORS origins accepts list."""
        settings = Settings(cors_origins=["*"])
        assert isinstance(settings.cors_origins, list)

    def test_embedding_dimension_positive(self):
        """Test that embedding dimension is positive."""
        settings = Settings(embedding_dimension=768)
        assert settings.embedding_dimension > 0
