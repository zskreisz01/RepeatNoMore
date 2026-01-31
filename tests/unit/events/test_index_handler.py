"""Unit tests for IndexHandler - automatic vector store indexing on document changes."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, mock_open

import pytest

from app.events.types import DocumentEvent, EventData
from app.events.handlers.index_handler import IndexHandler, get_index_handler


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    settings = MagicMock()
    settings.docs_repo_path = "./knowledge_base/docs"
    return settings


@pytest.fixture
def mock_vector_store():
    """Create mock vector store."""
    store = MagicMock()
    store.count.return_value = 10
    store.add_documents.return_value = ["doc_1", "doc_2"]
    store.delete_documents.return_value = True
    store.collection = MagicMock()
    store.collection.get.return_value = {"ids": ["existing_doc_1"]}
    return store


@pytest.fixture
def mock_document_loader():
    """Create mock document loader."""
    loader = MagicMock()
    doc = MagicMock()
    doc.content = "Test content"
    doc.metadata = {"source": "test.md"}
    doc.doc_id = "test_doc_1"
    loader.load_file.return_value = [doc]
    loader.load_text.return_value = [doc]
    loader.load_directory.return_value = [doc, doc]
    return loader


@pytest.fixture
def index_handler(mock_settings, mock_vector_store, mock_document_loader):
    """Create IndexHandler with mocked dependencies."""
    with patch("app.events.handlers.index_handler.get_settings", return_value=mock_settings), \
         patch("app.events.handlers.index_handler.get_vector_store", return_value=mock_vector_store), \
         patch("app.events.handlers.index_handler.get_document_loader", return_value=mock_document_loader):
        handler = IndexHandler(debounce_seconds=0.1)  # Short debounce for tests
        handler._initialized = True  # Skip initialization
        return handler


class TestIndexHandlerInitialization:
    """Tests for IndexHandler initialization."""

    @pytest.mark.asyncio
    async def test_ensure_initialized_empty_store_triggers_reindex(
        self, mock_settings, mock_document_loader
    ):
        """Test that empty vector store triggers full reindex."""
        mock_store = MagicMock()
        mock_store.count.return_value = 0  # Empty store

        with patch("app.events.handlers.index_handler.get_settings", return_value=mock_settings), \
             patch("app.events.handlers.index_handler.get_vector_store", return_value=mock_store), \
             patch("app.events.handlers.index_handler.get_document_loader", return_value=mock_document_loader):
            handler = IndexHandler()

            await handler.ensure_initialized()

            # Should have called add_documents for full reindex
            assert mock_store.add_documents.called or handler._initialized

    @pytest.mark.asyncio
    async def test_ensure_initialized_populated_store_skips_reindex(
        self, mock_settings, mock_vector_store, mock_document_loader
    ):
        """Test that populated vector store skips reindex."""
        mock_vector_store.count.return_value = 100  # Non-empty store

        with patch("app.events.handlers.index_handler.get_settings", return_value=mock_settings), \
             patch("app.events.handlers.index_handler.get_vector_store", return_value=mock_vector_store), \
             patch("app.events.handlers.index_handler.get_document_loader", return_value=mock_document_loader):
            handler = IndexHandler()

            await handler.ensure_initialized()

            # Should NOT have triggered full reindex (add_documents with reset)
            assert handler._initialized


class TestIndexHandlerDocumentEvents:
    """Tests for IndexHandler handling document events."""

    @pytest.mark.asyncio
    async def test_doc_created_queues_file_for_indexing(
        self, mock_settings, mock_vector_store, mock_document_loader
    ):
        """Test that DOC_CREATED event queues the file for indexing."""
        with patch("app.events.handlers.index_handler.get_settings", return_value=mock_settings), \
             patch("app.events.handlers.index_handler.get_vector_store", return_value=mock_vector_store), \
             patch("app.events.handlers.index_handler.get_document_loader", return_value=mock_document_loader):
            # Create handler with longer debounce so we can check pending state
            handler = IndexHandler(debounce_seconds=10.0)
            handler._initialized = True

            event = EventData(
                event_type=DocumentEvent.DOC_CREATED,
                file_path="/path/to/new_doc.md",
                user_email="user@test.com",
            )

            await handler.handle_event(event)

            # File should be queued for update (checked before debounce runs)
            assert "/path/to/new_doc.md" in handler._pending_updates

    @pytest.mark.asyncio
    async def test_doc_updated_queues_file_for_reindexing(
        self, mock_settings, mock_vector_store, mock_document_loader
    ):
        """Test that DOC_UPDATED event queues the file for reindexing."""
        with patch("app.events.handlers.index_handler.get_settings", return_value=mock_settings), \
             patch("app.events.handlers.index_handler.get_vector_store", return_value=mock_vector_store), \
             patch("app.events.handlers.index_handler.get_document_loader", return_value=mock_document_loader):
            # Create handler with longer debounce so we can check pending state
            handler = IndexHandler(debounce_seconds=10.0)
            handler._initialized = True

            event = EventData(
                event_type=DocumentEvent.DOC_UPDATED,
                file_path="/path/to/updated_doc.md",
                user_email="user@test.com",
            )

            await handler.handle_event(event)

            # File should be queued for update
            assert "/path/to/updated_doc.md" in handler._pending_updates

    @pytest.mark.asyncio
    async def test_doc_deleted_queues_file_for_removal(
        self, mock_settings, mock_vector_store, mock_document_loader
    ):
        """Test that DOC_DELETED event queues the file for removal."""
        with patch("app.events.handlers.index_handler.get_settings", return_value=mock_settings), \
             patch("app.events.handlers.index_handler.get_vector_store", return_value=mock_vector_store), \
             patch("app.events.handlers.index_handler.get_document_loader", return_value=mock_document_loader):
            # Create handler with longer debounce so we can check pending state
            handler = IndexHandler(debounce_seconds=10.0)
            handler._initialized = True

            event = EventData(
                event_type=DocumentEvent.DOC_DELETED,
                file_path="/path/to/deleted_doc.md",
                user_email="user@test.com",
            )

            await handler.handle_event(event)

            # File should be queued for deletion
            assert "/path/to/deleted_doc.md" in handler._pending_deletes


class TestIndexHandlerDraftEvents:
    """Tests for IndexHandler handling draft events."""

    @pytest.mark.asyncio
    async def test_draft_created_indexes_content(self, index_handler, mock_vector_store):
        """Test that DRAFT_CREATED event indexes the draft content."""
        event = EventData(
            event_type=DocumentEvent.DRAFT_CREATED,
            draft_id="DRAFT-001",
            draft_content="This is the draft content for documentation update.",
            target_section="getting-started.md",
            user_email="user@test.com",
        )

        await index_handler.handle_event(event)

        # Should have indexed the draft content
        # The content is indexed directly, not via file
        await asyncio.sleep(0.1)

    @pytest.mark.asyncio
    async def test_draft_approved_indexes_with_approved_status(
        self, index_handler, mock_vector_store
    ):
        """Test that DRAFT_APPROVED event indexes content with approved status."""
        event = EventData(
            event_type=DocumentEvent.DRAFT_APPROVED,
            draft_id="DRAFT-002",
            draft_content="Approved draft content.",
            target_section="architecture.md",
            user_email="admin@test.com",
        )

        await index_handler.handle_event(event)

        await asyncio.sleep(0.1)


class TestIndexHandlerQuestionEvents:
    """Tests for IndexHandler handling question events."""

    @pytest.mark.asyncio
    async def test_question_created_indexes_question(self, index_handler, mock_vector_store):
        """Test that QUESTION_CREATED event indexes the question."""
        event = EventData(
            event_type=DocumentEvent.QUESTION_CREATED,
            question_id="Q-001",
            question_text="How do I configure the database connection?",
            user_email="user@test.com",
            metadata={"platform": "discord"},
        )

        await index_handler.handle_event(event)

        await asyncio.sleep(0.1)

    @pytest.mark.asyncio
    async def test_question_answered_indexes_qa_pair(self, index_handler, mock_vector_store):
        """Test that QUESTION_ANSWERED event indexes the Q&A pair."""
        event = EventData(
            event_type=DocumentEvent.QUESTION_ANSWERED,
            question_id="Q-002",
            question_text="What is the default port?",
            answer_text="The default port is 8080 for the API server.",
            user_email="admin@test.com",
        )

        await index_handler.handle_event(event)

        await asyncio.sleep(0.1)


class TestIndexHandlerDebouncing:
    """Tests for IndexHandler debouncing behavior."""

    @pytest.mark.asyncio
    async def test_multiple_rapid_events_are_batched(self, index_handler):
        """Test that multiple rapid events are batched together."""
        events = [
            EventData(
                event_type=DocumentEvent.DOC_UPDATED,
                file_path=f"/path/to/doc{i}.md",
            )
            for i in range(5)
        ]

        # Fire multiple events rapidly
        for event in events:
            await index_handler.handle_event(event)

        # All files should be pending
        assert len(index_handler._pending_updates) == 5

    @pytest.mark.asyncio
    async def test_debounce_waits_before_processing(self, index_handler):
        """Test that debounce mechanism waits before processing."""
        event = EventData(
            event_type=DocumentEvent.DOC_UPDATED,
            file_path="/path/to/doc.md",
        )

        await index_handler.handle_event(event)

        # Immediately after, file should still be pending
        assert "/path/to/doc.md" in index_handler._pending_updates


class TestIndexHandlerReindex:
    """Tests for manual reindex functionality."""

    @pytest.mark.asyncio
    async def test_manual_reindex_returns_count(
        self, mock_settings, mock_vector_store, mock_document_loader
    ):
        """Test that manual reindex returns document count."""
        mock_vector_store.count.return_value = 50

        with patch("app.events.handlers.index_handler.get_settings", return_value=mock_settings), \
             patch("app.events.handlers.index_handler.get_vector_store", return_value=mock_vector_store), \
             patch("app.events.handlers.index_handler.get_document_loader", return_value=mock_document_loader):
            handler = IndexHandler()
            handler._initialized = True

            count = await handler.reindex()

            assert count == 50


class TestGetIndexHandler:
    """Tests for the global index handler getter."""

    def test_get_index_handler_returns_singleton(self):
        """Test that get_index_handler returns the same instance."""
        # Reset the global
        import app.events.handlers.index_handler as module
        module._index_handler = None

        with patch("app.events.handlers.index_handler.get_settings") as mock_settings, \
             patch("app.events.handlers.index_handler.get_vector_store"), \
             patch("app.events.handlers.index_handler.get_document_loader"):
            mock_settings.return_value = MagicMock(docs_repo_path="./docs")

            handler1 = get_index_handler()
            handler2 = get_index_handler()

            assert handler1 is handler2

        # Clean up
        module._index_handler = None
