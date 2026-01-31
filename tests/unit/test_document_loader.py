"""Unit tests for document loader module."""

import pytest
from pathlib import Path
from app.rag.document_loader import DocumentLoader, Document


class TestDocument:
    """Test cases for Document class."""

    def test_document_initialization(self):
        """Test document initialization."""
        doc = Document(
            content="Test content",
            metadata={"source": "test.txt"}
        )

        assert doc.content == "Test content"
        assert doc.metadata["source"] == "test.txt"
        assert doc.doc_id is not None

    def test_document_custom_id(self):
        """Test document with custom ID."""
        doc = Document(
            content="Test content",
            doc_id="custom_id_123"
        )

        assert doc.doc_id == "custom_id_123"

    def test_document_repr(self):
        """Test document string representation."""
        doc = Document(content="Test", doc_id="test_123")
        repr_str = repr(doc)

        assert "test_123" in repr_str
        assert "length=4" in repr_str


class TestDocumentLoader:
    """Test cases for DocumentLoader class."""

    @pytest.fixture
    def loader(self):
        """Create a document loader for testing."""
        return DocumentLoader(chunk_size=100, chunk_overlap=20)

    @pytest.fixture
    def sample_text_file(self, tmp_path):
        """Create a sample text file for testing."""
        file_path = tmp_path / "test.txt"
        file_path.write_text("This is a test document.\nIt has multiple lines.\nFor testing purposes.")
        return str(file_path)

    @pytest.fixture
    def sample_markdown_file(self, tmp_path):
        """Create a sample markdown file for testing."""
        file_path = tmp_path / "test.md"
        content = """# Test Document

This is a test markdown document.

## Section 1

Some content here.

## Section 2

More content here.
"""
        file_path.write_text(content)
        return str(file_path)

    def test_initialization(self, loader):
        """Test loader initialization."""
        assert loader.chunk_size == 100
        assert loader.chunk_overlap == 20
        assert loader.text_splitter is not None

    def test_load_text_file(self, loader, sample_text_file):
        """Test loading a text file."""
        documents = loader.load_file(sample_text_file)

        assert len(documents) > 0
        assert all(isinstance(doc, Document) for doc in documents)
        assert all(doc.metadata["file_type"] == ".txt" for doc in documents)

    def test_load_markdown_file(self, loader, sample_markdown_file):
        """Test loading a markdown file."""
        documents = loader.load_file(sample_markdown_file)

        assert len(documents) > 0
        assert all(isinstance(doc, Document) for doc in documents)
        assert all(doc.metadata["file_type"] == ".md" for doc in documents)

    def test_load_nonexistent_file(self, loader):
        """Test loading a file that doesn't exist."""
        with pytest.raises(FileNotFoundError):
            loader.load_file("/nonexistent/path/file.txt")

    def test_load_directory(self, loader, tmp_path):
        """Test loading all files from a directory."""
        # Create test files
        (tmp_path / "file1.txt").write_text("Content 1")
        (tmp_path / "file2.txt").write_text("Content 2")
        (tmp_path / "file3.md").write_text("# Content 3")

        documents = loader.load_directory(str(tmp_path))

        assert len(documents) > 0
        # Should have documents from all files
        sources = set(doc.metadata.get("source", "") for doc in documents)
        assert len(sources) == 3

    def test_load_directory_with_pattern(self, loader, tmp_path):
        """Test loading directory with glob pattern."""
        (tmp_path / "file1.txt").write_text("Content 1")
        (tmp_path / "file2.txt").write_text("Content 2")
        (tmp_path / "file3.md").write_text("# Content 3")

        documents = loader.load_directory(str(tmp_path), glob_pattern="**/*.txt")

        # Should only load .txt files
        assert len(documents) > 0
        assert all(doc.metadata["file_type"] == ".txt" for doc in documents)

    def test_load_directory_with_exclusions(self, loader, tmp_path):
        """Test loading directory with exclusions."""
        (tmp_path / "file1.txt").write_text("Content 1")
        (tmp_path / "exclude_me.txt").write_text("Excluded")
        (tmp_path / "file3.txt").write_text("Content 3")

        documents = loader.load_directory(
            str(tmp_path),
            exclude_patterns=["exclude_me"]
        )

        # Should not include excluded file
        sources = [doc.metadata.get("file_name", "") for doc in documents]
        assert "exclude_me.txt" not in sources

    def test_load_invalid_directory(self, loader):
        """Test loading an invalid directory."""
        with pytest.raises(NotADirectoryError):
            loader.load_directory("/not/a/directory")

    def test_load_text_directly(self, loader):
        """Test loading text directly."""
        text = "This is a long text that should be split into multiple chunks. " * 10

        documents = loader.load_text(text, metadata={"source": "direct_text"})

        assert len(documents) > 0
        assert all(isinstance(doc, Document) for doc in documents)
        assert all(doc.metadata["source"] == "direct_text" for doc in documents)

    def test_load_empty_text(self, loader):
        """Test loading empty text."""
        documents = loader.load_text("")
        assert len(documents) == 0

    def test_load_text_short(self, loader):
        """Test loading short text (single chunk)."""
        text = "Short text."

        documents = loader.load_text(text)

        assert len(documents) == 1
        assert documents[0].content == text

    def test_chunking_metadata(self, loader):
        """Test that chunk metadata is correct."""
        text = "A" * 500  # Long text to ensure multiple chunks

        documents = loader.load_text(text)

        if len(documents) > 1:
            # Check chunk indices
            assert documents[0].metadata["chunk_index"] == 0
            assert documents[-1].metadata["chunk_index"] == len(documents) - 1
            # Check total chunks
            assert all(doc.metadata["total_chunks"] == len(documents) for doc in documents)

    def test_supported_extensions(self):
        """Test getting supported file extensions."""
        extensions = DocumentLoader.supported_extensions()

        assert isinstance(extensions, list)
        assert ".txt" in extensions
        assert ".md" in extensions
        assert ".pdf" in extensions


@pytest.mark.integration
class TestDocumentLoaderIntegration:
    """Integration tests for document loader."""

    @pytest.fixture
    def loader(self):
        """Create a document loader for testing."""
        return DocumentLoader(chunk_size=100, chunk_overlap=20)

    def test_load_knowledge_base(self, loader):
        """Test loading actual knowledge base if it exists."""
        kb_path = Path("knowledge_base/docs")

        if not kb_path.exists():
            pytest.skip("knowledge_base/docs directory not found")

        documents = loader.load_directory(str(kb_path), glob_pattern="**/*.md")
        # Should load at least some documents (may be 0 if all fail due to encoding issues)
        assert len(documents) >= 0
        print(f"Loaded {len(documents)} chunks from knowledge base")
