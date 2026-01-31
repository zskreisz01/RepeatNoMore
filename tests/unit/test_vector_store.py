"""Unit tests for vector store module (PostgreSQL + pgvector)."""

import pytest
from unittest.mock import Mock, MagicMock, patch


class TestVectorStore:
    """Test cases for VectorStore class."""

    @pytest.fixture
    def mock_embedding_generator(self):
        """Create a mock embedding generator."""
        mock = Mock()
        # Return 3-dimensional embeddings for simplicity in tests
        mock.embed_text.return_value = [0.1, 0.2, 0.3]
        mock.embed_batch.return_value = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6], [0.7, 0.8, 0.9]]
        return mock

    @pytest.fixture
    def mock_cursor(self):
        """Create a mock cursor."""
        cursor = MagicMock()
        cursor.fetchone.return_value = [0]  # Default count
        cursor.fetchall.return_value = []
        cursor.__enter__ = Mock(return_value=cursor)
        cursor.__exit__ = Mock(return_value=False)
        return cursor

    @pytest.fixture
    def mock_connection(self, mock_cursor):
        """Create a mock connection."""
        conn = MagicMock()
        conn.cursor.return_value = mock_cursor
        conn.__enter__ = Mock(return_value=conn)
        conn.__exit__ = Mock(return_value=False)
        return conn

    @pytest.fixture
    def vector_store(self, mock_embedding_generator, mock_connection):
        """Create a test vector store with mocked dependencies."""
        with patch("app.rag.vector_store.psycopg2.connect", return_value=mock_connection):
            with patch("app.rag.vector_store.register_vector"):
                with patch(
                    "app.rag.vector_store.get_embedding_generator",
                    return_value=mock_embedding_generator
                ):
                    from app.rag.vector_store import VectorStore
                    store = VectorStore(table_name="test_documents", reset=True)
                    # Store the mocks for later access
                    store._mock_conn = mock_connection
                    store._mock_cursor = mock_connection.cursor.return_value
                    return store

    def test_initialization(self, vector_store):
        """Test that vector store initializes correctly."""
        assert vector_store is not None
        assert vector_store.table_name == "test_documents"

    def test_add_documents_empty_list(self, vector_store):
        """Test that adding empty list raises ValueError."""
        with pytest.raises(ValueError, match="Cannot add empty document list"):
            vector_store.add_documents([])

    def test_add_documents_mismatched_lengths(self, vector_store):
        """Test that mismatched lengths raise ValueError."""
        texts = ["Doc 1", "Doc 2"]
        metadatas = [{"source": "test.txt"}]  # Only one metadata

        with pytest.raises(ValueError, match="must have the same length"):
            vector_store.add_documents(texts, metadatas)

    def test_add_single_document(self, vector_store, mock_connection):
        """Test adding a single document."""
        with patch("app.rag.vector_store.psycopg2.connect", return_value=mock_connection):
            with patch("app.rag.vector_store.register_vector"):
                with patch("app.rag.vector_store.execute_values"):
                    texts = ["This is a test document."]
                    metadatas = [{"source": "test.txt"}]

                    ids = vector_store.add_documents(texts, metadatas)

                    assert len(ids) == 1
                    assert ids[0].startswith("doc_")

    def test_add_multiple_documents(self, vector_store, mock_connection):
        """Test adding multiple documents."""
        with patch("app.rag.vector_store.psycopg2.connect", return_value=mock_connection):
            with patch("app.rag.vector_store.register_vector"):
                with patch("app.rag.vector_store.execute_values"):
                    texts = [
                        "First document about Python.",
                        "Second document about JavaScript.",
                        "Third document about TypeScript."
                    ]
                    metadatas = [
                        {"source": "python.txt", "topic": "programming"},
                        {"source": "javascript.txt", "topic": "programming"},
                        {"source": "typescript.txt", "topic": "programming"}
                    ]

                    ids = vector_store.add_documents(texts, metadatas)

                    assert len(ids) == 3

    def test_add_documents_with_custom_ids(self, vector_store, mock_connection):
        """Test adding documents with custom IDs."""
        with patch("app.rag.vector_store.psycopg2.connect", return_value=mock_connection):
            with patch("app.rag.vector_store.register_vector"):
                with patch("app.rag.vector_store.execute_values"):
                    texts = ["Doc 1", "Doc 2"]
                    ids = vector_store.add_documents(texts, ids=["custom_1", "custom_2"])

                    assert ids == ["custom_1", "custom_2"]

    def test_query_empty_string(self, vector_store):
        """Test that empty query raises ValueError."""
        with pytest.raises(ValueError, match="Query text cannot be empty"):
            vector_store.query("")

    def test_query_basic(self, vector_store, mock_connection, mock_cursor):
        """Test basic query functionality."""
        # Set up mock cursor to return query results
        mock_cursor.fetchall.return_value = [
            {"id": "doc_0", "content": "Python is great", "metadata": {}, "distance": 0.1},
            {"id": "doc_1", "content": "JavaScript rocks", "metadata": {}, "distance": 0.2},
        ]

        with patch("app.rag.vector_store.psycopg2.connect", return_value=mock_connection):
            with patch("app.rag.vector_store.register_vector"):
                results = vector_store.query("Python programming", n_results=2)

                assert "ids" in results
                assert "documents" in results
                assert "metadatas" in results
                assert "distances" in results

                # Results should be nested lists (legacy compatibility)
                assert isinstance(results["ids"][0], list)
                assert len(results["ids"][0]) == 2

    def test_query_with_metadata_filter(self, vector_store, mock_connection, mock_cursor):
        """Test query with metadata filtering."""
        mock_cursor.fetchall.return_value = [
            {"id": "doc_0", "content": "Python doc", "metadata": {"topic": "python"}, "distance": 0.1}
        ]

        with patch("app.rag.vector_store.psycopg2.connect", return_value=mock_connection):
            with patch("app.rag.vector_store.register_vector"):
                results = vector_store.query(
                    "Python",
                    n_results=5,
                    where={"topic": "python"}
                )

                assert len(results["ids"][0]) == 1

    def test_get_document_found(self, vector_store, mock_connection, mock_cursor):
        """Test retrieving a specific document."""
        mock_cursor.fetchone.return_value = {
            "id": "doc_1",
            "content": "Test document content.",
            "metadata": {"source": "test.txt"}
        }

        with patch("app.rag.vector_store.psycopg2.connect", return_value=mock_connection):
            with patch("app.rag.vector_store.register_vector"):
                doc = vector_store.get_document("doc_1")

                assert doc is not None
                assert doc["id"] == "doc_1"
                assert doc["document"] == "Test document content."
                assert doc["metadata"]["source"] == "test.txt"

    def test_get_nonexistent_document(self, vector_store, mock_connection, mock_cursor):
        """Test retrieving a document that doesn't exist."""
        mock_cursor.fetchone.return_value = None

        with patch("app.rag.vector_store.psycopg2.connect", return_value=mock_connection):
            with patch("app.rag.vector_store.register_vector"):
                doc = vector_store.get_document("nonexistent_id")
                assert doc is None

    def test_delete_documents(self, vector_store, mock_connection):
        """Test deleting documents."""
        with patch("app.rag.vector_store.psycopg2.connect", return_value=mock_connection):
            with patch("app.rag.vector_store.register_vector"):
                success = vector_store.delete_documents(["id_1", "id_3"])
                assert success is True

    def test_update_document(self, vector_store, mock_connection):
        """Test updating a document."""
        with patch("app.rag.vector_store.psycopg2.connect", return_value=mock_connection):
            with patch("app.rag.vector_store.register_vector"):
                success = vector_store.update_document(
                    "doc_1",
                    text="Updated text",
                    metadata={"updated": True}
                )

                assert success is True

    def test_update_document_text_only(self, vector_store, mock_connection):
        """Test updating only the text of a document."""
        with patch("app.rag.vector_store.psycopg2.connect", return_value=mock_connection):
            with patch("app.rag.vector_store.register_vector"):
                success = vector_store.update_document(
                    "doc_1",
                    text="New text only"
                )

                assert success is True

    def test_update_document_metadata_only(self, vector_store, mock_connection):
        """Test updating only the metadata of a document."""
        with patch("app.rag.vector_store.psycopg2.connect", return_value=mock_connection):
            with patch("app.rag.vector_store.register_vector"):
                success = vector_store.update_document(
                    "doc_1",
                    metadata={"new_key": "new_value"}
                )

                assert success is True

    def test_update_document_no_changes(self, vector_store):
        """Test updating a document with no changes."""
        # Should return True without making any DB calls
        success = vector_store.update_document("doc_1")
        assert success is True

    def test_clear_table(self, vector_store, mock_connection):
        """Test clearing the table."""
        with patch("app.rag.vector_store.psycopg2.connect", return_value=mock_connection):
            with patch("app.rag.vector_store.register_vector"):
                success = vector_store.clear()
                assert success is True

    def test_count(self, vector_store, mock_connection, mock_cursor):
        """Test document counting."""
        mock_cursor.fetchone.return_value = [5]

        with patch("app.rag.vector_store.psycopg2.connect", return_value=mock_connection):
            with patch("app.rag.vector_store.register_vector"):
                count = vector_store.count()
                assert count == 5


class TestVectorStoreGlobal:
    """Test global vector store singleton."""

    def test_get_vector_store_returns_singleton(self):
        """Test that get_vector_store returns same instance."""
        import app.rag.vector_store as vs_module

        # Reset global instance
        vs_module._vector_store = None

        with patch("app.rag.vector_store.psycopg2.connect") as mock_connect:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = [0]
            mock_cursor.__enter__ = Mock(return_value=mock_cursor)
            mock_cursor.__exit__ = Mock(return_value=False)
            mock_conn.cursor.return_value = mock_cursor
            mock_conn.__enter__ = Mock(return_value=mock_conn)
            mock_conn.__exit__ = Mock(return_value=False)
            mock_connect.return_value = mock_conn

            with patch("app.rag.vector_store.register_vector"):
                with patch("app.rag.vector_store.get_embedding_generator"):
                    store1 = vs_module.get_vector_store()
                    store2 = vs_module.get_vector_store()

                    assert store1 is store2

    def test_get_vector_store_reset(self):
        """Test that get_vector_store with reset creates new instance."""
        import app.rag.vector_store as vs_module

        # Reset global instance
        vs_module._vector_store = None

        with patch("app.rag.vector_store.psycopg2.connect") as mock_connect:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = [0]
            mock_cursor.__enter__ = Mock(return_value=mock_cursor)
            mock_cursor.__exit__ = Mock(return_value=False)
            mock_conn.cursor.return_value = mock_cursor
            mock_conn.__enter__ = Mock(return_value=mock_conn)
            mock_conn.__exit__ = Mock(return_value=False)
            mock_connect.return_value = mock_conn

            with patch("app.rag.vector_store.register_vector"):
                with patch("app.rag.vector_store.get_embedding_generator"):
                    store1 = vs_module.get_vector_store()
                    store2 = vs_module.get_vector_store(reset=True)

                    assert store1 is not store2


class TestVectorStoreEdgeCases:
    """Test edge cases for vector store."""

    def test_add_documents_with_none_metadata_items(self):
        """Test adding documents where some metadata items are None."""
        with patch("app.rag.vector_store.psycopg2.connect") as mock_connect:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = [0]
            mock_cursor.__enter__ = Mock(return_value=mock_cursor)
            mock_cursor.__exit__ = Mock(return_value=False)
            mock_conn.cursor.return_value = mock_cursor
            mock_conn.__enter__ = Mock(return_value=mock_conn)
            mock_conn.__exit__ = Mock(return_value=False)
            mock_connect.return_value = mock_conn

            with patch("app.rag.vector_store.register_vector"):
                with patch("app.rag.vector_store.execute_values"):
                    with patch("app.rag.vector_store.get_embedding_generator") as mock_emb:
                        mock_emb.return_value.embed_batch.return_value = [[0.1], [0.2]]

                        from app.rag.vector_store import VectorStore
                        store = VectorStore(table_name="test")

                        texts = ["Doc 1", "Doc 2"]
                        metadatas = [{"source": "a.txt"}, None]  # Second is None

                        ids = store.add_documents(texts, metadatas)

                        assert len(ids) == 2

    def test_query_with_min_score_filters_results(self):
        """Test that min_score properly filters results."""
        with patch("app.rag.vector_store.psycopg2.connect") as mock_connect:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = [0]
            mock_cursor.__enter__ = Mock(return_value=mock_cursor)
            mock_cursor.__exit__ = Mock(return_value=False)
            mock_conn.cursor.return_value = mock_cursor
            mock_conn.__enter__ = Mock(return_value=mock_conn)
            mock_conn.__exit__ = Mock(return_value=False)
            mock_connect.return_value = mock_conn

            with patch("app.rag.vector_store.register_vector"):
                with patch("app.rag.vector_store.get_embedding_generator") as mock_emb:
                    mock_emb.return_value.embed_text.return_value = [0.1, 0.2]

                    from app.rag.vector_store import VectorStore
                    store = VectorStore(table_name="test")

                    # Query should include min_score filter in SQL
                    results = store.query("test query", min_score=0.8)

                    # Results format should be correct
                    assert "ids" in results
                    assert "distances" in results
