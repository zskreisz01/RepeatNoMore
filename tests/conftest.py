"""Pytest configuration and fixtures."""

import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture(scope="session")
def test_data_dir():
    """Get test data directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def sample_docs_dir(test_data_dir):
    """Get sample documents directory."""
    return test_data_dir / "sample_docs"


@pytest.fixture
def mock_settings(monkeypatch):
    """Mock application settings for testing."""
    from app.config import Settings

    settings = Settings(
        postgres_host="localhost",
        postgres_port=5432,
        postgres_db="repeatnomore_test",
        postgres_user="repeatnomore",
        postgres_password="repeatnomore",
        postgres_vector_table="test_documents",
        llm_provider="anthropic",
        embedding_model="text-embedding-3-small",
        embedding_dimension=1536,
        environment="testing",
        log_level="DEBUG"
    )

    monkeypatch.setattr("app.config.get_settings", lambda: settings)
    return settings


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (may require services)"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "benchmark: mark test as benchmark test"
    )


@pytest.fixture(autouse=True, scope="module")
def reset_vector_store_singleton():
    """Reset vector store singleton between test modules to prevent state pollution."""
    # Reset before tests in the module
    try:
        import app.rag.vector_store as vs_module
        vs_module._vector_store = None
    except (ImportError, AttributeError):
        pass

    yield

    # Reset after tests in the module
    try:
        import app.rag.vector_store as vs_module
        vs_module._vector_store = None
    except (ImportError, AttributeError):
        pass
