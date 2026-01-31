"""Index handler for automatic vector store updates on document events."""

import asyncio
from pathlib import Path
from typing import Optional

from app.config import get_settings
from app.events.types import DocumentEvent, EventData
from app.rag.document_loader import get_document_loader
from app.rag.vector_store import get_vector_store
from app.utils.logging import get_logger

logger = get_logger(__name__)


class IndexHandler:
    """
    Handler for updating the vector store when documents change.

    Automatically indexes or removes documents from the vector store
    when document events are emitted. Supports both incremental updates
    (single file changes) and full reindexing.
    """

    def __init__(self, debounce_seconds: float = 2.0):
        """
        Initialize the index handler.

        Args:
            debounce_seconds: Seconds to wait before processing to batch rapid changes
        """
        self.debounce_seconds = debounce_seconds
        self._pending_updates: set[str] = set()
        self._pending_deletes: set[str] = set()
        self._debounce_task: Optional[asyncio.Task] = None
        self._initialized = False

        logger.info(
            "index_handler_initialized",
            debounce_seconds=debounce_seconds
        )

    async def ensure_initialized(self) -> None:
        """
        Ensure the vector store is initialized with documents.

        Called on first event or can be called at startup.
        Respects REINDEX_ON_STARTUP and REINDEX_RESET settings.
        """
        if self._initialized:
            return

        try:
            settings = get_settings()
            store = get_vector_store()
            doc_count = store.count()

            should_reindex = False
            reset_before_reindex = settings.reindex_reset

            if doc_count == 0:
                logger.info("vector_store_empty_performing_initial_index")
                should_reindex = True
                reset_before_reindex = True  # Always reset when empty
            elif settings.reindex_on_startup:
                logger.info(
                    "reindex_on_startup_enabled",
                    current_documents=doc_count,
                    reset=reset_before_reindex
                )
                should_reindex = True
            else:
                logger.info(
                    "vector_store_already_populated",
                    document_count=doc_count
                )

            if should_reindex:
                await self._full_reindex(reset=reset_before_reindex)

            self._initialized = True

        except Exception as e:
            logger.error("index_handler_initialization_failed", error=str(e))

    async def handle_event(self, event: EventData) -> None:
        """
        Handle document-related events.

        Args:
            event: The event data
        """
        # Ensure vector store is initialized on first event
        await self.ensure_initialized()

        event_type = event.event_type

        if event_type == DocumentEvent.DOC_DELETED:
            if event.file_path:
                self._pending_deletes.add(event.file_path)
                await self._schedule_update()

        elif event_type in [
            DocumentEvent.DOC_CREATED,
            DocumentEvent.DOC_UPDATED,
            DocumentEvent.DRAFT_CREATED,
            DocumentEvent.DRAFT_APPROVED,
            DocumentEvent.QUESTION_CREATED,
            DocumentEvent.QUESTION_ANSWERED,
        ]:
            file_path = event.file_path

            # For drafts, index the draft content directly
            if event.draft_content:
                await self._index_content(
                    content=event.draft_content,
                    source=f"draft:{event.draft_id}",
                    metadata={
                        "type": "draft",
                        "draft_id": event.draft_id,
                        "target_section": event.target_section,
                        "status": "approved" if event_type == DocumentEvent.DRAFT_APPROVED else "pending",
                    }
                )
                # Also index file if path provided
                if not file_path:
                    return

            # For questions, index the question (and answer if available)
            if event.question_text:
                content = f"Q: {event.question_text}"
                if event.answer_text:
                    content += f"\n\nA: {event.answer_text}"

                await self._index_content(
                    content=content,
                    source=f"qa:{event.question_id}",
                    metadata={
                        "type": "qa",
                        "question_id": event.question_id,
                        "status": "answered" if event_type == DocumentEvent.QUESTION_ANSWERED else "pending",
                    }
                )
                # Also index file if path provided
                if not file_path:
                    return

            if file_path:
                self._pending_updates.add(file_path)
                await self._schedule_update()

    async def _schedule_update(self) -> None:
        """Schedule a debounced update to batch rapid changes."""
        if self._debounce_task and not self._debounce_task.done():
            self._debounce_task.cancel()

        self._debounce_task = asyncio.create_task(self._debounced_update())

    async def _debounced_update(self) -> None:
        """Wait for debounce period then process pending updates."""
        await asyncio.sleep(self.debounce_seconds)
        await self._process_pending()

    async def _process_pending(self) -> None:
        """Process all pending updates and deletes."""
        # Copy and clear pending sets
        updates = self._pending_updates.copy()
        deletes = self._pending_deletes.copy()
        self._pending_updates.clear()
        self._pending_deletes.clear()

        # Process deletes first
        for file_path in deletes:
            await self._remove_from_index(file_path)

        # Process updates (includes creates)
        for file_path in updates:
            await self._index_file(file_path)

    async def _index_file(self, file_path: str) -> None:
        """
        Index a single file into the vector store.

        Args:
            file_path: Path to the file to index
        """
        try:
            path = Path(file_path)
            if not path.exists():
                logger.warning("file_not_found_skipping_index", path=file_path)
                return

            # Check if file type is supported
            if path.suffix.lower() not in [".md", ".txt", ".pdf"]:
                logger.debug("unsupported_file_type", path=file_path)
                return

            loader = get_document_loader()
            store = get_vector_store()

            # First remove existing chunks for this file
            await self._remove_from_index(file_path)

            # Load and chunk the file
            documents = loader.load_file(file_path)

            if documents:
                texts = [doc.content for doc in documents]
                metadatas = [doc.metadata for doc in documents]
                ids = [doc.doc_id for doc in documents]

                store.add_documents(texts, metadatas, ids)

                logger.info(
                    "file_indexed",
                    path=file_path,
                    chunks=len(documents)
                )

        except Exception as e:
            logger.error(
                "file_indexing_failed",
                path=file_path,
                error=str(e)
            )

    async def _remove_from_index(self, file_path: str) -> None:
        """
        Remove a file's chunks from the vector store.

        Args:
            file_path: Path to the file to remove
        """
        try:
            store = get_vector_store()

            # Query for documents with this source path using PostgreSQL
            ids_to_delete = store.get_ids_by_metadata({"source": file_path})

            if ids_to_delete:
                store.delete_documents(ids_to_delete)
                logger.info(
                    "file_removed_from_index",
                    path=file_path,
                    chunks_removed=len(ids_to_delete)
                )

        except Exception as e:
            logger.error(
                "file_removal_failed",
                path=file_path,
                error=str(e)
            )

    async def _index_content(
        self,
        content: str,
        source: str,
        metadata: dict
    ) -> None:
        """
        Index content directly into the vector store.

        Args:
            content: The text content to index
            source: Source identifier
            metadata: Additional metadata
        """
        try:
            loader = get_document_loader()
            store = get_vector_store()

            # Load and chunk the content
            documents = loader.load_text(content, metadata={"source": source, **metadata})

            if documents:
                texts = [doc.content for doc in documents]
                metadatas = [doc.metadata for doc in documents]
                ids = [doc.doc_id for doc in documents]

                store.add_documents(texts, metadatas, ids)

                logger.info(
                    "content_indexed",
                    source=source,
                    chunks=len(documents)
                )

        except Exception as e:
            logger.error(
                "content_indexing_failed",
                source=source,
                error=str(e)
            )

    async def _full_reindex(self, reset: bool = True) -> None:
        """
        Perform a full reindex of all documentation.

        Args:
            reset: If True, clears the vector store before reindexing.
                   If False, adds documents without clearing existing ones.
        """
        try:
            settings = get_settings()
            loader = get_document_loader()
            store = get_vector_store(reset=reset)

            docs_path = settings.docs_repo_path

            logger.info("starting_full_reindex", path=docs_path, reset=reset)

            # Load all documents
            documents = loader.load_directory(
                docs_path,
                glob_pattern="**/*.md"
            )

            if documents:
                texts = [doc.content for doc in documents]
                metadatas = [doc.metadata for doc in documents]
                ids = [doc.doc_id for doc in documents]

                store.add_documents(texts, metadatas, ids)

                logger.info(
                    "full_reindex_completed",
                    documents_indexed=len(documents)
                )
            else:
                logger.warning("no_documents_found_for_indexing", path=docs_path)

        except Exception as e:
            logger.error("full_reindex_failed", error=str(e))
            raise

    async def reindex(self) -> int:
        """
        Trigger a full reindex manually.

        Returns:
            Number of documents indexed
        """
        await self._full_reindex()
        store = get_vector_store()
        return store.count()


# Global instance
_index_handler: Optional[IndexHandler] = None


def get_index_handler() -> IndexHandler:
    """Get or create the global index handler instance."""
    global _index_handler
    if _index_handler is None:
        _index_handler = IndexHandler()
    return _index_handler