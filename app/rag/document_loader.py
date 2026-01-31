"""Document loading and chunking for RAG system."""

import os
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    TextLoader,
    PyPDFLoader,
)

# Try to import UnstructuredMarkdownLoader, fallback to TextLoader if not available
try:
    from langchain_community.document_loaders import UnstructuredMarkdownLoader
    _HAS_UNSTRUCTURED = True
except ImportError:
    _HAS_UNSTRUCTURED = False

from app.config import get_settings

logger = logging.getLogger(__name__)


class Document:
    """Represents a document chunk with content and metadata."""

    def __init__(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        doc_id: Optional[str] = None
    ):
        """
        Initialize a document.

        Args:
            content: Document text content
            metadata: Optional metadata dictionary
            doc_id: Optional document ID (auto-generated from content hash if not provided)
        """
        self.content = content
        self.metadata = metadata or {}

        if doc_id is None:
            # Generate ID from content hash
            content_hash = hashlib.md5(content.encode()).hexdigest()[:12]
            source = self.metadata.get("source", "unknown")
            self.doc_id = f"{Path(source).stem}_{content_hash}"
        else:
            self.doc_id = doc_id

    def __repr__(self) -> str:
        """String representation."""
        return f"Document(id={self.doc_id}, length={len(self.content)})"


class DocumentLoader:
    """Load and chunk documents for vector store ingestion."""

    def __init__(
        self,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None
    ):
        """
        Initialize the document loader.

        Args:
            chunk_size: Size of text chunks (defaults to settings value)
            chunk_overlap: Overlap between chunks (defaults to settings value)
        """
        settings = get_settings()
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )

        logger.info(
            f"DocumentLoader initialized with chunk_size={self.chunk_size}, "
            f"chunk_overlap={self.chunk_overlap}"
        )

    def load_file(self, file_path: str) -> List[Document]:
        """
        Load a single file and split into chunks.

        Args:
            file_path: Path to the file

        Returns:
            List[Document]: List of document chunks

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file type is unsupported
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        logger.info(f"Loading file: {file_path}")

        try:
            # Determine file type and use appropriate loader
            suffix = path.suffix.lower()

            if suffix == ".md":
                if _HAS_UNSTRUCTURED:
                    try:
                        loader = UnstructuredMarkdownLoader(str(path))
                    except ImportError:
                        # Fallback to TextLoader if unstructured module not available
                        logger.debug("UnstructuredMarkdownLoader unavailable, using TextLoader")
                        loader = TextLoader(str(path))
                else:
                    # Fallback to TextLoader if unstructured is not available
                    logger.debug("Using TextLoader for markdown file (unstructured not installed)")
                    loader = TextLoader(str(path))
            elif suffix == ".txt":
                loader = TextLoader(str(path))
            elif suffix == ".pdf":
                loader = PyPDFLoader(str(path))
            else:
                # Try to load as text
                loader = TextLoader(str(path))

            # Load document
            docs = loader.load()

            # Split into chunks
            chunks = []
            for doc in docs:
                split_docs = self.text_splitter.split_text(doc.page_content)

                for i, chunk_text in enumerate(split_docs):
                    metadata = {
                        "source": str(path),
                        "file_name": path.name,
                        "file_type": suffix,
                        "chunk_index": i,
                        "total_chunks": len(split_docs)
                    }

                    # Add original metadata if exists
                    if hasattr(doc, "metadata"):
                        metadata.update(doc.metadata)

                    chunks.append(Document(content=chunk_text, metadata=metadata))

            logger.info(f"Loaded {len(chunks)} chunks from {file_path}")
            return chunks

        except Exception as e:
            logger.error(f"Failed to load file {file_path}: {e}")
            raise ValueError(f"Failed to load file: {e}")

    def load_directory(
        self,
        directory_path: str,
        glob_pattern: str = "**/*",
        exclude_patterns: Optional[List[str]] = None
    ) -> List[Document]:
        """
        Load all files from a directory.

        Args:
            directory_path: Path to directory
            glob_pattern: Glob pattern for file selection
            exclude_patterns: List of patterns to exclude

        Returns:
            List[Document]: All document chunks from the directory

        Raises:
            NotADirectoryError: If path is not a directory
        """
        dir_path = Path(directory_path)

        if not dir_path.is_dir():
            raise NotADirectoryError(f"Not a directory: {directory_path}")

        exclude_patterns = exclude_patterns or []
        all_chunks = []

        logger.info(f"Loading documents from directory: {directory_path}")

        # Find all matching files
        for file_path in dir_path.glob(glob_pattern):
            if not file_path.is_file():
                continue

            # Check exclusions
            if any(pattern in str(file_path) for pattern in exclude_patterns):
                logger.debug(f"Skipping excluded file: {file_path}")
                continue

            # Skip hidden files and certain types
            if file_path.name.startswith("."):
                continue

            try:
                chunks = self.load_file(str(file_path))
                all_chunks.extend(chunks)
            except Exception as e:
                logger.warning(f"Failed to load {file_path}: {e}")
                continue

        logger.info(
            f"Loaded {len(all_chunks)} total chunks from "
            f"{directory_path}"
        )

        return all_chunks

    def load_text(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """
        Load text directly and split into chunks.

        Args:
            text: Text content
            metadata: Optional metadata

        Returns:
            List[Document]: Document chunks
        """
        if not text or not text.strip():
            return []

        metadata = metadata or {}

        # Split text into chunks
        chunks = self.text_splitter.split_text(text)

        documents = []
        for i, chunk_text in enumerate(chunks):
            chunk_metadata = {
                **metadata,
                "chunk_index": i,
                "total_chunks": len(chunks)
            }
            documents.append(Document(content=chunk_text, metadata=chunk_metadata))

        logger.info(f"Created {len(documents)} chunks from text")
        return documents

    @staticmethod
    def supported_extensions() -> List[str]:
        """
        Get list of supported file extensions.

        Returns:
            List[str]: Supported extensions
        """
        return [".txt", ".md", ".pdf"]


# Global instance
_document_loader: Optional[DocumentLoader] = None


def get_document_loader() -> DocumentLoader:
    """
    Get or create a global document loader instance.

    Returns:
        DocumentLoader: The document loader
    """
    global _document_loader
    if _document_loader is None:
        _document_loader = DocumentLoader()
    return _document_loader
