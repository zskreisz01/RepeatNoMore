"""Unit tests for retriever module."""

import pytest
from unittest.mock import Mock, patch
from app.rag.retriever import Retriever, RetrievalResult, get_retriever


class TestRetrievalResult:
    """Test cases for RetrievalResult class."""

    def test_initialization(self):
        """Test RetrievalResult initialization."""
        result = RetrievalResult(
            document="Test document",
            metadata={"source": "test.md"},
            score=0.95,
            doc_id="doc_1"
        )

        assert result.document == "Test document"
        assert result.metadata == {"source": "test.md"}
        assert result.score == 0.95
        assert result.doc_id == "doc_1"

    def test_repr(self):
        """Test string representation."""
        result = RetrievalResult(
            document="Test",
            metadata={},
            score=0.85,
            doc_id="doc_1"
        )

        repr_str = repr(result)

        assert "RetrievalResult" in repr_str
        assert "doc_1" in repr_str
        assert "0.850" in repr_str

    def test_to_dict(self):
        """Test conversion to dictionary."""
        result = RetrievalResult(
            document="Test document",
            metadata={"source": "test.md", "topic": "testing"},
            score=0.92,
            doc_id="doc_123"
        )

        result_dict = result.to_dict()

        assert result_dict["document"] == "Test document"
        assert result_dict["metadata"]["source"] == "test.md"
        assert result_dict["metadata"]["topic"] == "testing"
        assert result_dict["score"] == 0.92
        assert result_dict["doc_id"] == "doc_123"


class TestRetriever:
    """Test cases for Retriever class."""

    @pytest.fixture
    def mock_vector_store(self):
        """Create mock vector store."""
        store = Mock()
        store.query.return_value = {
            "ids": [["doc_1", "doc_2", "doc_3"]],
            "documents": [["Document 1", "Document 2", "Document 3"]],
            "metadatas": [[
                {"source": "file1.md"},
                {"source": "file2.md"},
                {"source": "file3.md"}
            ]],
            "distances": [[0.1, 0.2, 0.3]]
        }
        store.get_document.return_value = {
            "id": "doc_1",
            "document": "Reference document",
            "metadata": {"source": "ref.md"}
        }
        return store

    @pytest.fixture
    def retriever(self, mock_vector_store):
        """Create retriever with mock vector store."""
        return Retriever(vector_store=mock_vector_store, top_k=5, min_score=0.7)

    def test_initialization(self, retriever, mock_vector_store):
        """Test retriever initialization."""
        assert retriever.vector_store is mock_vector_store
        assert retriever.top_k == 5
        assert retriever.min_score == 0.7

    def test_initialization_with_defaults(self):
        """Test retriever initialization with default settings."""
        with patch("app.rag.retriever.get_vector_store") as mock_get_store:
            mock_store = Mock()
            mock_get_store.return_value = mock_store

            retriever = Retriever()

            assert retriever.vector_store is mock_store
            assert retriever.top_k > 0
            assert retriever.min_score >= 0

    def test_retrieve_success(self, retriever, mock_vector_store):
        """Test successful document retrieval."""
        query = "test query"

        results = retriever.retrieve(query)

        assert isinstance(results, list)
        assert len(results) == 3
        assert all(isinstance(r, RetrievalResult) for r in results)

        # Verify results are sorted by score (highest first)
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

        # Verify vector store was called correctly
        mock_vector_store.query.assert_called_once()
        call_kwargs = mock_vector_store.query.call_args[1]
        assert call_kwargs["query_text"] == query

    def test_retrieve_empty_query(self, retriever):
        """Test that empty query raises ValueError."""
        with pytest.raises(ValueError, match="Query cannot be empty"):
            retriever.retrieve("")

        with pytest.raises(ValueError, match="Query cannot be empty"):
            retriever.retrieve("   ")

    def test_retrieve_with_custom_top_k(self, retriever, mock_vector_store):
        """Test retrieval with custom top_k."""
        results = retriever.retrieve("test query", top_k=10)

        call_kwargs = mock_vector_store.query.call_args[1]
        assert call_kwargs["n_results"] == 10

    def test_retrieve_with_custom_min_score(self, retriever, mock_vector_store):
        """Test retrieval with custom min_score."""
        results = retriever.retrieve("test query", min_score=0.8)

        call_kwargs = mock_vector_store.query.call_args[1]
        assert call_kwargs["min_score"] == 0.8

    def test_retrieve_with_metadata_filter(self, retriever, mock_vector_store):
        """Test retrieval with metadata filtering."""
        metadata_filter = {"topic": "python"}

        results = retriever.retrieve("test query", metadata_filter=metadata_filter)

        call_kwargs = mock_vector_store.query.call_args[1]
        assert call_kwargs["where"] == metadata_filter

    def test_retrieve_score_conversion(self, retriever, mock_vector_store):
        """Test that distances are properly converted to scores."""
        results = retriever.retrieve("test query")

        # Using formula: score = 1 - (distance / 2)
        # Cosine distance ranges from 0 (identical) to 2 (opposite)
        # Distance 0.1 -> score = 1 - 0.05 = 0.95
        assert results[0].score == pytest.approx(0.95, rel=0.01)
        # Distance 0.2 -> score = 1 - 0.1 = 0.9
        assert results[1].score == pytest.approx(0.9, rel=0.01)
        # Distance 0.3 -> score = 1 - 0.15 = 0.85
        assert results[2].score == pytest.approx(0.85, rel=0.01)

    def test_retrieve_failure(self, retriever, mock_vector_store):
        """Test handling of retrieval failure."""
        mock_vector_store.query.side_effect = Exception("Query failed")

        with pytest.raises(RuntimeError, match="Retrieval failed"):
            retriever.retrieve("test query")

    def test_retrieve_with_context_success(self, retriever, mock_vector_store):
        """Test retrieval with context formatting."""
        result = retriever.retrieve_with_context("test query")

        assert "context" in result
        assert "sources" in result
        assert "num_documents" in result

        assert isinstance(result["context"], str)
        assert isinstance(result["sources"], list)
        assert result["num_documents"] == 3

        # Verify context contains document info
        context = result["context"]
        assert "Document 1" in context
        assert "file1.md" in context

    def test_retrieve_with_context_no_results(self, retriever, mock_vector_store):
        """Test retrieve_with_context when no documents found."""
        mock_vector_store.query.return_value = {
            "ids": [[]],
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]]
        }

        result = retriever.retrieve_with_context("test query")

        assert result["context"] == "No relevant information found."
        assert result["sources"] == []
        assert result["num_documents"] == 0

    def test_retrieve_with_context_max_length(self, retriever, mock_vector_store):
        """Test context length limiting."""
        # Mock with a very long document
        long_doc = "x" * 5000
        mock_vector_store.query.return_value = {
            "ids": [["doc_1"]],
            "documents": [[long_doc]],
            "metadatas": [[{"source": "long.md"}]],
            "distances": [[0.1]]
        }

        result = retriever.retrieve_with_context("test query", max_context_length=100)

        # Context should be truncated
        assert len(result["context"]) <= 150  # With some overhead for formatting

    def test_retrieve_with_context_source_formatting(self, retriever, mock_vector_store):
        """Test that sources are properly formatted in context."""
        result = retriever.retrieve_with_context("test query")

        context = result["context"]

        # Should include document numbers
        assert "[Document 1]" in context
        assert "[Document 2]" in context
        assert "[Document 3]" in context

        # Should include sources
        assert "file1.md" in context
        assert "file2.md" in context
        assert "file3.md" in context

    def test_retrieve_with_context_sources_list(self, retriever, mock_vector_store):
        """Test that sources list is properly populated."""
        result = retriever.retrieve_with_context("test query")

        sources = result["sources"]

        assert len(sources) == 3
        assert all("doc_id" in s for s in sources)
        assert all("document" in s for s in sources)
        assert all("metadata" in s for s in sources)
        assert all("score" in s for s in sources)

    def test_get_similar_documents_success(self, retriever, mock_vector_store):
        """Test finding similar documents."""
        # Mock the query to return multiple results including self
        mock_vector_store.query.return_value = {
            "ids": [["doc_1", "doc_2", "doc_3"]],
            "documents": [["Ref doc", "Similar 1", "Similar 2"]],
            "metadatas": [[{}, {}, {}]],
            "distances": [[0.0, 0.1, 0.2]]
        }

        results = retriever.get_similar_documents("doc_1", top_k=2)

        # Should exclude self (doc_1)
        assert len(results) == 2
        assert all(r.doc_id != "doc_1" for r in results)
        assert results[0].doc_id == "doc_2"
        assert results[1].doc_id == "doc_3"

    def test_get_similar_documents_not_found(self, retriever, mock_vector_store):
        """Test error when reference document not found."""
        mock_vector_store.get_document.return_value = None

        with pytest.raises(ValueError, match="Document not found"):
            retriever.get_similar_documents("nonexistent")

    def test_get_retriever_singleton(self):
        """Test that get_retriever returns same instance."""
        # Clear global instance
        import app.rag.retriever
        app.rag.retriever._retriever = None

        with patch("app.rag.retriever.get_vector_store"):
            retriever1 = get_retriever()
            retriever2 = get_retriever()

            assert retriever1 is retriever2


class TestRetrieverEdgeCases:
    """Test edge cases for retriever."""

    @pytest.fixture
    def mock_vector_store(self):
        """Create mock vector store."""
        return Mock()

    @pytest.fixture
    def retriever(self, mock_vector_store):
        """Create retriever."""
        return Retriever(vector_store=mock_vector_store)

    def test_retrieve_single_document(self, retriever, mock_vector_store):
        """Test retrieval with single document result."""
        mock_vector_store.query.return_value = {
            "ids": [["doc_1"]],
            "documents": [["Single document"]],
            "metadatas": [[{"source": "single.md"}]],
            "distances": [[0.05]]
        }

        results = retriever.retrieve("query")

        assert len(results) == 1
        assert results[0].doc_id == "doc_1"

    def test_retrieve_score_clamping(self, retriever, mock_vector_store):
        """Test that scores are properly bounded between 0 and 1."""
        # Mock with various distances including > 1
        mock_vector_store.query.return_value = {
            "ids": [["doc_1", "doc_2"]],
            "documents": [["Doc 1", "Doc 2"]],
            "metadatas": [[{}, {}]],
            "distances": [[0.05, 1.5]]
        }

        results = retriever.retrieve("query")

        # Using formula: score = 1 - (distance / 2), all scores in (0, 1]
        assert all(0 < r.score <= 1 for r in results)
        # Distance 0.05 -> score = 1 - 0.025 = 0.975
        assert results[0].score == pytest.approx(0.975, rel=0.01)
        # Distance 1.5 -> score = 1 - 0.75 = 0.25
        assert results[1].score == pytest.approx(0.25, rel=0.01)
