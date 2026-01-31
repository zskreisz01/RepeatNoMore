"""Unit tests for embeddings module."""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from app.rag.embeddings import EmbeddingGenerator, get_embedding_generator


class TestEmbeddingGenerator:
    """Test cases for EmbeddingGenerator class."""

    @pytest.fixture
    def mock_sentence_transformer(self):
        """Mock SentenceTransformer for testing."""
        with patch('app.rag.embeddings.SentenceTransformer') as mock:
            # Create mock model instance
            mock_model = MagicMock()
            mock.return_value = mock_model

            # Mock encode() to return realistic embeddings
            # Use hash of text to generate different but deterministic embeddings
            def encode_text(text, convert_to_numpy=False, batch_size=32, show_progress_bar=True):
                if isinstance(text, str):
                    # Single text - use hash to generate different embeddings
                    seed = hash(text) % 1000
                    embedding = np.array([(seed + i) / 1000.0 for i in range(384)])
                    return embedding
                else:
                    # Batch of texts
                    embeddings = []
                    for t in text:
                        seed = hash(t) % 1000
                        embedding = np.array([(seed + i) / 1000.0 for i in range(384)])
                        embeddings.append(embedding)
                    return np.array(embeddings)

            mock_model.encode = Mock(side_effect=encode_text)
            yield mock_model

    @pytest.fixture
    def generator(self, mock_sentence_transformer):
        """Create an embedding generator for testing."""
        return EmbeddingGenerator()

    def test_initialization(self, generator):
        """Test that generator initializes correctly."""
        assert generator is not None
        assert generator.model_name is not None
        assert generator.embedding_dimension > 0
        assert generator.model is not None

    def test_embed_text_success(self, generator):
        """Test embedding generation for valid text."""
        text = "This is a test sentence for embedding generation."
        embedding = generator.embed_text(text)

        assert isinstance(embedding, list)
        assert len(embedding) > 0  # Embedding should not be empty
        assert all(isinstance(x, float) for x in embedding)

    def test_embed_text_empty_string(self, generator):
        """Test that empty string raises ValueError."""
        with pytest.raises(ValueError, match="Cannot generate embedding for empty text"):
            generator.embed_text("")

    def test_embed_text_whitespace_only(self, generator):
        """Test that whitespace-only string raises ValueError."""
        with pytest.raises(ValueError, match="Cannot generate embedding for empty text"):
            generator.embed_text("   ")

    def test_embed_batch_success(self, generator):
        """Test batch embedding generation."""
        texts = [
            "First test sentence.",
            "Second test sentence.",
            "Third test sentence."
        ]

        embeddings = generator.embed_batch(texts)

        assert isinstance(embeddings, list)
        assert len(embeddings) == len(texts)
        assert all(len(emb) > 0 for emb in embeddings)  # All embeddings should be non-empty

    def test_embed_batch_empty_list(self, generator):
        """Test that empty list raises ValueError."""
        with pytest.raises(ValueError, match="Cannot generate embeddings for empty text list"):
            generator.embed_batch([])

    def test_embed_batch_with_empty_texts(self, generator):
        """Test batch embedding with some empty texts."""
        texts = [
            "Valid text",
            "",
            "Another valid text",
            "   "
        ]

        embeddings = generator.embed_batch(texts)

        # New implementation filters out empty texts, so we get only 2 embeddings
        assert len(embeddings) == 2
        # Both should be valid embeddings (non-empty)
        assert all(len(emb) > 0 for emb in embeddings)

    def test_get_embedding_dimension(self, generator):
        """Test getting embedding dimension."""
        dimension = generator.get_embedding_dimension()
        assert isinstance(dimension, int)
        assert dimension > 0

    def test_embedding_consistency(self, generator):
        """Test that same text produces same embedding."""
        text = "Test consistency"
        emb1 = generator.embed_text(text)
        emb2 = generator.embed_text(text)

        # Embeddings should be identical for same input
        assert len(emb1) == len(emb2)
        assert emb1 == emb2

    def test_different_texts_different_embeddings(self, generator):
        """Test that different texts produce different embeddings."""
        text1 = "This is the first text."
        text2 = "This is completely different content."

        emb1 = generator.embed_text(text1)
        emb2 = generator.embed_text(text2)

        # Embeddings should be significantly different
        assert emb1 != emb2

    def test_get_embedding_generator_singleton(self, mock_sentence_transformer):
        """Test that get_embedding_generator returns same instance."""
        # Reset global singleton before test
        import app.rag.embeddings
        app.rag.embeddings._embedding_generator = None

        gen1 = get_embedding_generator()
        gen2 = get_embedding_generator()

        assert gen1 is gen2

        # Clean up - reset global state after test
        app.rag.embeddings._embedding_generator = None


@pytest.mark.slow
class TestEmbeddingPerformance:
    """Performance tests for embeddings."""

    @pytest.fixture
    def mock_sentence_transformer(self):
        """Mock SentenceTransformer for testing."""
        with patch('app.rag.embeddings.SentenceTransformer') as mock:
            # Create mock model instance
            mock_model = MagicMock()
            mock.return_value = mock_model

            # Mock encode() to return realistic embeddings
            def encode_text(text, convert_to_numpy=False, batch_size=32, show_progress_bar=True):
                if isinstance(text, str):
                    seed = hash(text) % 1000
                    embedding = np.array([(seed + i) / 1000.0 for i in range(384)])
                    return embedding
                else:
                    # Batch of texts
                    embeddings = []
                    for t in text:
                        seed = hash(t) % 1000
                        embedding = np.array([(seed + i) / 1000.0 for i in range(384)])
                        embeddings.append(embedding)
                    return np.array(embeddings)

            mock_model.encode = Mock(side_effect=encode_text)
            yield mock_model

    @pytest.fixture
    def generator(self, mock_sentence_transformer):
        """Create an embedding generator for testing."""
        return EmbeddingGenerator()

    def test_batch_performance(self, generator):
        """Test batch embedding generation performance."""
        import time

        texts = ["Test sentence number {}.".format(i) for i in range(100)]

        start_time = time.time()
        result = generator.embed_batch(texts, batch_size=32)
        elapsed_time = time.time() - start_time

        assert len(result) == 100
        # Ensure it completes in reasonable time (less than 60 seconds)
        assert elapsed_time < 60, f"Batch embedding took too long: {elapsed_time:.2f}s"
