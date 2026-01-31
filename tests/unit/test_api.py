"""Unit tests for API routes."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_vector_store():
    """Mock vector store."""
    with patch("app.api.routes.get_vector_store") as mock:
        store = Mock()
        store.count.return_value = 100
        store.query.return_value = {
            "ids": [["doc_1", "doc_2"]],
            "documents": [["Document 1 content", "Document 2 content"]],
            "metadatas": [[{"source": "test1.md"}, {"source": "test2.md"}]],
            "distances": [[0.1, 0.2]]
        }
        store.add_documents.return_value = ["doc_1", "doc_2"]
        mock.return_value = store
        yield store


@pytest.fixture
def mock_qa_service():
    """Mock QA service."""
    with patch("app.api.routes.process_question") as mock:
        from app.services.qa_service import QAResult
        mock.return_value = QAResult(
            answer="Test answer",
            sources=[
                {
                    "doc_id": "doc_1",
                    "document": "Test document",
                    "metadata": {"source": "test.md"},
                    "score": 0.9
                }
            ],
            confidence=0.85,
            processing_time=1.5,
            llm_duration=1.0,
            retrieval_time=0.5,
            model="test-model"
        )
        yield mock


@pytest.fixture
def mock_document_loader():
    """Mock document loader."""
    with patch("app.api.routes.get_document_loader") as mock:
        loader = Mock()
        # Return mock documents
        from app.rag.document_loader import Document
        mock_docs = [
            Document(doc_id="doc_1", content="Content 1", metadata={"source": "file1.md"}),
            Document(doc_id="doc_2", content="Content 2", metadata={"source": "file2.md"})
        ]
        loader.return_value.load_directory.return_value = mock_docs
        loader.return_value.load_file.return_value = mock_docs[:1]
        loader.return_value.load_text.return_value = mock_docs[:1]
        mock.return_value = loader.return_value
        yield loader.return_value


class TestHealthEndpoint:
    """Test cases for health check endpoint."""

    def test_health_check_healthy(self, client, mock_vector_store):
        """Test health check when all components are healthy."""
        with patch("app.api.routes.get_llm_provider") as mock_llm_provider:
            mock_provider = Mock()
            mock_provider.is_available.return_value = True
            mock_provider.provider_name = "ollama"
            mock_provider.model_name = "mistral:7b-instruct"
            mock_llm_provider.return_value = mock_provider

            response = client.get("/api/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] in ["healthy", "degraded"]
            assert "version" in data
            assert "components" in data
            assert "timestamp" in data

    def test_health_check_degraded(self, client):
        """Test health check when some components are unhealthy."""
        with patch("app.api.routes.get_vector_store") as mock_store:
            mock_store.side_effect = Exception("Connection failed")

            response = client.get("/api/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "degraded"
            assert "vector_store" in data["components"]


class TestAskEndpoint:
    """Test cases for ask question endpoint."""

    def test_ask_question_success(self, client, mock_vector_store, mock_qa_service):
        """Test successful question answering."""
        request_data = {
            "question": "What is Python?",
            "include_sources": True,
            "top_k": 3
        }

        response = client.post("/api/ask", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "sources" in data
        assert "confidence" in data
        assert "processing_time" in data
        assert data["answer"] == "Test answer"

    def test_ask_question_no_sources(self, client, mock_vector_store, mock_qa_service):
        """Test question answering without sources."""
        request_data = {
            "question": "What is Python?",
            "include_sources": False
        }

        response = client.post("/api/ask", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert len(data["sources"]) == 0

    def test_ask_question_empty_question(self, client):
        """Test that empty question returns validation error."""
        request_data = {"question": ""}

        response = client.post("/api/ask", json=request_data)

        assert response.status_code == 422  # Validation error

    def test_ask_question_invalid_top_k(self, client):
        """Test that invalid top_k returns validation error."""
        request_data = {
            "question": "Test?",
            "top_k": 0
        }

        response = client.post("/api/ask", json=request_data)

        assert response.status_code == 422

    def test_ask_question_agent_failure(self, client, mock_vector_store):
        """Test handling of agent failure."""
        with patch("app.api.routes.process_question") as mock_process:
            mock_process.side_effect = Exception("Agent error")

            request_data = {"question": "Test question"}
            response = client.post("/api/ask", json=request_data)

            assert response.status_code == 500


class TestIndexEndpoint:
    """Test cases for document indexing endpoint."""

    def test_index_default_knowledge_base(self, client, mock_vector_store, mock_document_loader):
        """Test indexing default knowledge base."""
        response = client.post("/api/index", json={})

        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "documents_indexed" in data
        assert "chunks_created" in data
        assert "processing_time" in data

    def test_index_text_content(self, client, mock_vector_store, mock_document_loader):
        """Test indexing text content."""
        request_data = {
            "text": "Sample text to index",
            "metadata": {"source": "manual"}
        }

        response = client.post("/api/index", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_index_file_path(self, client, mock_vector_store, mock_document_loader):
        """Test indexing from file path."""
        request_data = {"file_path": "/path/to/file.txt"}

        response = client.post("/api/index", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert "documents_indexed" in data

    def test_index_directory_path(self, client, mock_vector_store, mock_document_loader):
        """Test indexing from directory."""
        request_data = {"directory_path": "/path/to/docs"}

        response = client.post("/api/index", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert "documents_indexed" in data

    def test_index_with_reset(self, client, mock_vector_store, mock_document_loader):
        """Test indexing with collection reset."""
        request_data = {"reset": True}

        with patch("app.api.routes.get_vector_store") as mock_get_store:
            store = Mock()
            store.add_documents.return_value = ["doc_1"]
            mock_get_store.return_value = store

            response = client.post("/api/index", json=request_data)

            # Verify reset was called
            mock_get_store.assert_called_with(reset=True)
            assert response.status_code == 200

    def test_index_failure(self, client, mock_vector_store):
        """Test handling of indexing failure."""
        with patch("app.api.routes.get_document_loader") as mock_loader:
            mock_loader.side_effect = Exception("Loading failed")

            response = client.post("/api/index", json={})

            assert response.status_code == 500


class TestSearchEndpoint:
    """Test cases for search endpoint."""

    def test_search_success(self, client, mock_vector_store):
        """Test successful document search."""
        request_data = {
            "query": "Python programming",
            "top_k": 5,
            "min_score": 0.5
        }

        response = client.post("/api/search", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "total_results" in data
        assert "query" in data
        assert "processing_time" in data
        assert data["query"] == "Python programming"

    def test_search_with_metadata_filter(self, client, mock_vector_store):
        """Test search with metadata filtering."""
        request_data = {
            "query": "test",
            "metadata_filter": {"topic": "programming"}
        }

        response = client.post("/api/search", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert "results" in data

    def test_search_empty_query(self, client):
        """Test that empty query returns validation error."""
        request_data = {"query": ""}

        response = client.post("/api/search", json=request_data)

        assert response.status_code == 422

    def test_search_failure(self, client):
        """Test handling of search failure."""
        with patch("app.api.routes.get_vector_store") as mock_store:
            mock_store.return_value.query.side_effect = Exception("Search failed")

            request_data = {"query": "test"}
            response = client.post("/api/search", json=request_data)

            assert response.status_code == 500


class TestFeedbackEndpoint:
    """Test cases for feedback endpoint."""

    def test_submit_feedback_success(self, client):
        """Test successful feedback submission."""
        request_data = {
            "question": "What is Python?",
            "answer": "Python is a programming language.",
            "rating": 5,
            "comment": "Very helpful!",
            "session_id": "session-123"
        }

        response = client.post("/api/feedback", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "feedback_id" in data
        assert "message" in data

    def test_submit_feedback_minimal(self, client):
        """Test feedback submission with minimal fields."""
        request_data = {
            "question": "Test?",
            "answer": "Test answer.",
            "rating": 3
        }

        response = client.post("/api/feedback", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_submit_feedback_invalid_rating(self, client):
        """Test that invalid rating returns validation error."""
        request_data = {
            "question": "Test?",
            "answer": "Test.",
            "rating": 6  # Invalid: must be 1-5
        }

        response = client.post("/api/feedback", json=request_data)

        assert response.status_code == 422


class TestRootEndpoint:
    """Test cases for root endpoint."""

    def test_root_endpoint(self, client):
        """Test root endpoint returns API info."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "RepeatNoMore API"
        assert "version" in data
        assert "status" in data
        assert data["status"] == "running"
