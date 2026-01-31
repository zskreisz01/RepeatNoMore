"""Unit tests for API schemas."""

import pytest
from pydantic import ValidationError
from app.api.schemas import (
    QuestionRequest,
    QuestionResponse,
    Source,
    DocumentIndexRequest,
    DocumentIndexResponse,
    HealthResponse,
    FeedbackRequest,
    FeedbackResponse,
    SearchRequest,
    SearchResult,
    SearchResponse,
    ErrorResponse,
)


class TestQuestionSchemas:
    """Test cases for question-related schemas."""

    def test_question_request_valid(self):
        """Test valid question request."""
        data = {
            "question": "What is Python?",
            "top_k": 5,
            "include_sources": True,
            "session_id": "session-123"
        }
        request = QuestionRequest(**data)

        assert request.question == "What is Python?"
        assert request.top_k == 5
        assert request.include_sources is True
        assert request.session_id == "session-123"

    def test_question_request_minimal(self):
        """Test question request with minimal fields."""
        data = {"question": "What is Python?"}
        request = QuestionRequest(**data)

        assert request.question == "What is Python?"
        assert request.top_k is None
        assert request.include_sources is True
        assert request.session_id is None

    def test_question_request_empty_question(self):
        """Test that empty question raises validation error."""
        data = {"question": ""}

        with pytest.raises(ValidationError) as exc_info:
            QuestionRequest(**data)

        assert "at least 1 character" in str(exc_info.value).lower()

    def test_question_request_question_too_long(self):
        """Test that overly long question raises validation error."""
        data = {"question": "x" * 1001}

        with pytest.raises(ValidationError) as exc_info:
            QuestionRequest(**data)

        assert "at most 1000 characters" in str(exc_info.value).lower()

    def test_question_request_invalid_top_k(self):
        """Test that invalid top_k raises validation error."""
        with pytest.raises(ValidationError):
            QuestionRequest(question="Test", top_k=0)

        with pytest.raises(ValidationError):
            QuestionRequest(question="Test", top_k=21)

    def test_source_schema(self):
        """Test Source schema."""
        data = {
            "doc_id": "doc_1",
            "content": "Test content",
            "source": "test.md",
            "score": 0.95
        }
        source = Source(**data)

        assert source.doc_id == "doc_1"
        assert source.content == "Test content"
        assert source.source == "test.md"
        assert source.score == 0.95

    def test_source_invalid_score(self):
        """Test that invalid score raises validation error."""
        data = {
            "doc_id": "doc_1",
            "content": "Test",
            "source": "test.md",
            "score": 1.5
        }

        with pytest.raises(ValidationError) as exc_info:
            Source(**data)

        assert "less than or equal to 1" in str(exc_info.value).lower()

    def test_question_response_valid(self):
        """Test valid question response."""
        data = {
            "answer": "Python is a programming language.",
            "sources": [
                {
                    "doc_id": "doc_1",
                    "content": "Python documentation",
                    "source": "python.md",
                    "score": 0.95
                }
            ],
            "confidence": 0.9,
            "processing_time": 1.5
        }
        response = QuestionResponse(**data)

        assert response.answer == "Python is a programming language."
        assert len(response.sources) == 1
        assert response.confidence == 0.9
        assert response.processing_time == 1.5

    def test_question_response_no_sources(self):
        """Test question response without sources."""
        data = {
            "answer": "Test answer",
            "sources": [],
            "confidence": 0.5,
            "processing_time": 0.5
        }
        response = QuestionResponse(**data)

        assert response.answer == "Test answer"
        assert len(response.sources) == 0


class TestDocumentIndexingSchemas:
    """Test cases for document indexing schemas."""

    def test_document_index_request_text(self):
        """Test indexing text content."""
        data = {
            "text": "Sample text to index",
            "metadata": {"source": "manual"},
            "reset": False
        }
        request = DocumentIndexRequest(**data)

        assert request.text == "Sample text to index"
        assert request.metadata == {"source": "manual"}
        assert request.reset is False

    def test_document_index_request_file(self):
        """Test indexing from file path."""
        data = {"file_path": "/path/to/file.txt"}
        request = DocumentIndexRequest(**data)

        assert request.file_path == "/path/to/file.txt"
        assert request.text is None
        assert request.directory_path is None

    def test_document_index_request_directory(self):
        """Test indexing from directory."""
        data = {"directory_path": "/path/to/docs"}
        request = DocumentIndexRequest(**data)

        assert request.directory_path == "/path/to/docs"
        assert request.text is None
        assert request.file_path is None

    def test_document_index_request_empty(self):
        """Test empty document index request."""
        data = {}
        request = DocumentIndexRequest(**data)

        assert request.text is None
        assert request.file_path is None
        assert request.directory_path is None
        assert request.metadata is None
        assert request.reset is False

    def test_document_index_response(self):
        """Test document index response."""
        data = {
            "success": True,
            "documents_indexed": 5,
            "chunks_created": 25,
            "processing_time": 2.5,
            "errors": []
        }
        response = DocumentIndexResponse(**data)

        assert response.success is True
        assert response.documents_indexed == 5
        assert response.chunks_created == 25
        assert response.processing_time == 2.5
        assert len(response.errors) == 0

    def test_document_index_response_with_errors(self):
        """Test document index response with errors."""
        data = {
            "success": False,
            "documents_indexed": 0,
            "chunks_created": 0,
            "processing_time": 0.1,
            "errors": ["File not found", "Permission denied"]
        }
        response = DocumentIndexResponse(**data)

        assert response.success is False
        assert len(response.errors) == 2


class TestHealthSchema:
    """Test cases for health check schema."""

    def test_health_response(self):
        """Test health response."""
        data = {
            "status": "healthy",
            "version": "0.1.0",
            "components": {
                "vector_store": "healthy",
                "ollama": "healthy"
            },
            "timestamp": "2024-01-01T00:00:00"
        }
        response = HealthResponse(**data)

        assert response.status == "healthy"
        assert response.version == "0.1.0"
        assert response.components["vector_store"] == "healthy"
        assert response.timestamp == "2024-01-01T00:00:00"


class TestFeedbackSchemas:
    """Test cases for feedback schemas."""

    def test_feedback_request_valid(self):
        """Test valid feedback request."""
        data = {
            "question": "What is Python?",
            "answer": "Python is a programming language.",
            "rating": 5,
            "comment": "Very helpful!",
            "session_id": "session-123"
        }
        request = FeedbackRequest(**data)

        assert request.question == "What is Python?"
        assert request.answer == "Python is a programming language."
        assert request.rating == 5
        assert request.comment == "Very helpful!"
        assert request.session_id == "session-123"

    def test_feedback_request_minimal(self):
        """Test feedback request without optional fields."""
        data = {
            "question": "What is Python?",
            "answer": "Python is a language.",
            "rating": 4
        }
        request = FeedbackRequest(**data)

        assert request.rating == 4
        assert request.comment is None
        assert request.session_id is None

    def test_feedback_request_invalid_rating(self):
        """Test that invalid rating raises validation error."""
        data = {
            "question": "Test?",
            "answer": "Test answer",
            "rating": 0
        }

        with pytest.raises(ValidationError):
            FeedbackRequest(**data)

        data["rating"] = 6
        with pytest.raises(ValidationError):
            FeedbackRequest(**data)

    def test_feedback_response(self):
        """Test feedback response."""
        data = {
            "success": True,
            "feedback_id": "fb_12345",
            "message": "Thank you!"
        }
        response = FeedbackResponse(**data)

        assert response.success is True
        assert response.feedback_id == "fb_12345"
        assert response.message == "Thank you!"


class TestSearchSchemas:
    """Test cases for search schemas."""

    def test_search_request_valid(self):
        """Test valid search request."""
        data = {
            "query": "Python programming",
            "top_k": 10,
            "min_score": 0.7,
            "metadata_filter": {"topic": "programming"}
        }
        request = SearchRequest(**data)

        assert request.query == "Python programming"
        assert request.top_k == 10
        assert request.min_score == 0.7
        assert request.metadata_filter == {"topic": "programming"}

    def test_search_request_minimal(self):
        """Test search request with defaults."""
        data = {"query": "test"}
        request = SearchRequest(**data)

        assert request.query == "test"
        assert request.top_k == 5
        assert request.min_score is None
        assert request.metadata_filter is None

    def test_search_request_empty_query(self):
        """Test that empty query raises validation error."""
        data = {"query": ""}

        with pytest.raises(ValidationError):
            SearchRequest(**data)

    def test_search_request_invalid_top_k(self):
        """Test that invalid top_k raises validation error."""
        with pytest.raises(ValidationError):
            SearchRequest(query="test", top_k=0)

        with pytest.raises(ValidationError):
            SearchRequest(query="test", top_k=21)

    def test_search_result(self):
        """Test search result schema."""
        data = {
            "doc_id": "doc_1",
            "content": "Test content",
            "metadata": {"source": "test.md"},
            "score": 0.85
        }
        result = SearchResult(**data)

        assert result.doc_id == "doc_1"
        assert result.content == "Test content"
        assert result.metadata["source"] == "test.md"
        assert result.score == 0.85

    def test_search_response(self):
        """Test search response schema."""
        data = {
            "results": [
                {
                    "doc_id": "doc_1",
                    "content": "Content 1",
                    "metadata": {},
                    "score": 0.9
                },
                {
                    "doc_id": "doc_2",
                    "content": "Content 2",
                    "metadata": {},
                    "score": 0.8
                }
            ],
            "total_results": 2,
            "query": "test query",
            "processing_time": 0.5
        }
        response = SearchResponse(**data)

        assert len(response.results) == 2
        assert response.total_results == 2
        assert response.query == "test query"
        assert response.processing_time == 0.5


class TestErrorSchema:
    """Test cases for error schema."""

    def test_error_response_basic(self):
        """Test basic error response."""
        data = {
            "error": "ValueError",
            "message": "Invalid input"
        }
        error = ErrorResponse(**data)

        assert error.error == "ValueError"
        assert error.message == "Invalid input"
        assert error.details is None

    def test_error_response_with_details(self):
        """Test error response with details."""
        data = {
            "error": "ValidationError",
            "message": "Field validation failed",
            "details": {"field": "email", "issue": "invalid format"}
        }
        error = ErrorResponse(**data)

        assert error.error == "ValidationError"
        assert error.message == "Field validation failed"
        assert error.details["field"] == "email"
