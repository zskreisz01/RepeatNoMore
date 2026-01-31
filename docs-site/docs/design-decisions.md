---
sidebar_position: 5
---

# Design Decisions

This document captures key architectural and technical decisions made for the RepeatNoMore project.

## Table of Contents
- [Development Environment](#development-environment)
- [Programming Style](#programming-style)
- [Architecture Patterns](#architecture-patterns)
- [Technology Choices](#technology-choices)
- [Testing Strategy](#testing-strategy)

---

## Development Environment

### Package Management: UV

**Decision:** Use `uv` for development environment and package management.

**Rationale:**
- **Speed**: `uv` is significantly faster than pip for dependency resolution and installation
- **Reliability**: Better dependency resolution and lock file management
- **Modern**: Written in Rust, actively maintained, follows modern Python packaging standards
- **Compatibility**: Drop-in replacement for pip with better performance

**Usage:**
```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment
uv venv

# Install dependencies
uv pip install -r requirements.txt

# Add new package
uv pip install <package>

# Sync dependencies
uv pip sync requirements.txt
```

**References:**
- [uv Documentation](https://github.com/astral-sh/uv)
- See [CLAUDE.md](https://github.com/zskreisz/RepeatNoMore/blob/main/CLAUDE.md) for development guidelines
- See [copilot-instructions.md](https://github.com/zskreisz/RepeatNoMore/blob/main/copilot-instructions.md) for coding patterns

### Python Version

**Decision:** Python 3.11+

**Rationale:**
- Modern type system features
- Performance improvements over 3.10
- Good ecosystem support
- Compatible with most AI/ML libraries
- Avoids issues with packages requiring &lt;3.12

---

## Programming Style

### Type Hints

**Decision:** Comprehensive use of type hints throughout the codebase.

**Guidelines:**
```python
from typing import Optional, List, Dict, Any, Callable
from collections.abc import Iterable

# Always use type hints for function signatures
def process_documents(
    texts: List[str],
    metadata: Optional[Dict[str, Any]] = None,
    batch_size: int = 32
) -> List[Dict[str, Any]]:
    """Process documents with type-safe interface."""
    pass

# Use TypeAlias for complex types
from typing import TypeAlias

DocumentBatch: TypeAlias = List[Dict[str, Any]]
EmbeddingVector: TypeAlias = List[float]

# Use generics when appropriate
from typing import Generic, TypeVar

T = TypeVar('T')

class Cache(Generic[T]):
    def get(self, key: str) -> Optional[T]:
        pass
```

**Benefits:**
- IDE autocomplete and IntelliSense
- Early error detection
- Better code documentation
- Enables static type checking with mypy

### Functional Programming

**Decision:** Functional programming style is welcome and encouraged.

**Guidelines:**

**1. Use `functools` utilities:**
```python
from functools import reduce, partial, lru_cache, wraps

# Caching
@lru_cache(maxsize=128)
def get_embedding_model(model_name: str):
    return load_model(model_name)

# Partial application
from operator import add
add_ten = partial(add, 10)

# Reduce for aggregations
total = reduce(lambda acc, x: acc + x, numbers, 0)
```

**2. Prefer immutability:**
```python
# Good: Return new objects
def add_metadata(doc: Document, key: str, value: Any) -> Document:
    return Document(
        content=doc.content,
        metadata={**doc.metadata, key: value}
    )

# Avoid: Mutating in place
def add_metadata_bad(doc: Document, key: str, value: Any) -> None:
    doc.metadata[key] = value  # Mutation
```

**3. Use comprehensions and generators:**
```python
# List comprehension
valid_docs = [doc for doc in documents if doc.is_valid()]

# Generator for memory efficiency
def process_large_dataset(items: Iterable[str]) -> Iterable[Dict]:
    return (process_item(item) for item in items)

# Dict comprehension
metadata_dict = {doc.id: doc.metadata for doc in documents}
```

**4. Higher-order functions:**
```python
from typing import Callable

def apply_transformation(
    items: List[T],
    transform: Callable[[T], R]
) -> List[R]:
    return list(map(transform, items))

# Use with lambda or partial
results = apply_transformation(
    documents,
    lambda doc: extract_features(doc)
)
```

**5. Composition over inheritance:**
```python
from typing import Protocol

# Use protocols for structural typing
class Embeddable(Protocol):
    def to_embedding(self) -> List[float]: ...

class Retrievable(Protocol):
    def retrieve(self, query: str) -> List[Document]: ...

# Compose functionality
class RAGSystem:
    def __init__(
        self,
        embedder: Embeddable,
        retriever: Retrievable
    ):
        self.embedder = embedder
        self.retriever = retriever
```

**When to avoid functional style:**
- Performance-critical tight loops
- When mutability is clearer (e.g., building large structures)
- Interfacing with imperative APIs

---

## Architecture Patterns

### Singleton Pattern for Global Resources

**Decision:** Use singleton pattern for expensive resources (vector stores, embeddings, agents).

**Rationale:**
- Avoid multiple model loads
- Share connections efficiently
- Consistent state across application

**Implementation:**
```python
from typing import Optional

_instance: Optional[ResourceType] = None

def get_instance() -> ResourceType:
    global _instance
    if _instance is None:
        _instance = ResourceType()
    return _instance
```

### Dependency Injection

**Decision:** Use constructor injection for dependencies.

**Example:**
```python
class QAAgent:
    def __init__(
        self,
        retriever: Optional[Retriever] = None,
        llm_client: Optional[LLMClient] = None
    ):
        self.retriever = retriever or get_retriever()
        self.llm_client = llm_client or get_llm_client()
```

**Benefits:**
- Testability (easy to mock)
- Flexibility (swap implementations)
- Explicit dependencies

### Agent Pattern

**Decision:** Use agent-based architecture with base classes.

**Structure:**
```python
from abc import ABC, abstractmethod

class BaseAgent(ABC):
    @abstractmethod
    def process(self, input_data: Dict[str, Any]) -> AgentResult:
        pass
```

**Benefits:**
- Extensibility (add new agents easily)
- Consistency (common interface)
- Testability (mock agents)

---

## Technology Choices

### Vector Database: PostgreSQL + pgvector

**Decision:** PostgreSQL with pgvector extension as the primary vector database.

**Rationale:**
- **Unified storage**: Single database for both relational and vector data
- **Mature ecosystem**: Well-established PostgreSQL tooling and management
- **Azure integration**: Azure Database for PostgreSQL Flexible Server with pgvector support
- **Cost effective**: No additional vector database service needed
- **SQL flexibility**: Full SQL capabilities alongside vector search
- **Production ready**: Battle-tested PostgreSQL with ACID guarantees

**Implementation:**
- Uses cosine distance operator (`<=>`) for similarity search
- HNSW indexing for efficient approximate nearest neighbor search
- JSONB for flexible metadata storage
- 1536 dimensions for text-embedding-3-small embeddings

**Alternatives considered:**
- ChromaDB (rejected - requires separate service)
- Pinecone (requires cloud service, additional cost)
- Weaviate (more complex setup)
- FAISS (no persistence layer)

### LLM: Cloud API Providers

**Decision:** Use cloud LLM APIs (Anthropic, OpenAI, Cursor) instead of local models.

**Rationale:**
- **Higher quality**: Access to latest frontier models (Claude, GPT-4)
- **No infrastructure**: No need to manage GPU resources
- **Cost effective**: Pay-per-use for occasional queries
- **Easier deployment**: No model downloads or VRAM requirements
- **Flexibility**: Easy to switch between providers

**Supported providers:**
- Anthropic (Claude models) - default
- OpenAI (GPT-4 models)
- Cursor (for IDE integration)

**Configuration:**
```bash
LLM_PROVIDER=anthropic  # or openai, cursor
ANTHROPIC_API_KEY=sk-...
```

**Alternatives considered:**
- Ollama + Mistral (previous choice - local but resource intensive)

### Web Framework: FastAPI

**Decision:** FastAPI for REST API.

**Rationale:**
- Async support (important for LLM calls)
- Automatic OpenAPI docs
- Pydantic integration
- High performance
- Type hints first-class

---

## Testing Strategy

### Test Organization

**Structure:**
```
tests/
├── unit/          # Fast, isolated tests
├── integration/   # Component interaction tests
├── e2e/          # End-to-end workflows
└── conftest.py   # Shared fixtures
```

### Testing Principles

**1. Fast unit tests:**
```python
def test_embed_text(generator):
    """Test should run in <1ms"""
    embedding = generator.embed_text("test")
    assert len(embedding) == 768
```

**2. Integration tests marked:**
```python
@pytest.mark.integration
def test_full_rag_pipeline():
    """Test actual services (slower)"""
    pass
```

**3. Mock external services in unit tests:**
```python
@patch('app.rag.embeddings.SentenceTransformer')
def test_with_mock(mock_model):
    mock_model.return_value.encode.return_value = [0.1] * 768
    # Test code
```

### Coverage Goals

- **Unit tests**: >80% coverage
- **Integration tests**: Critical paths covered
- **E2E tests**: Happy paths covered

---

## Code Organization

### Module Structure

**Decision:** Organize by feature/component, not by type.

**Structure:**
```
app/
├── rag/          # All RAG-related code
├── agents/       # All agent code
├── api/          # All API code
└── utils/        # Shared utilities
```

**Not:**
```
app/
├── models/       # Don't organize by technical layer
├── services/
└── controllers/
```

### Import Style

**Guidelines:**
```python
# Standard library
import os
import time
from typing import List, Optional

# Third-party
import numpy as np
from fastapi import FastAPI

# Local application
from app.config import get_settings
from app.rag.embeddings import get_embedding_generator
```

---

## Performance Considerations

### Lazy Loading

**Decision:** Lazy-load expensive resources.

**Example:**
```python
class EmbeddingGenerator:
    def __init__(self):
        self._model = None

    @property
    def model(self):
        if self._model is None:
            self._model = load_expensive_model()
        return self._model
```

### Caching

**Decision:** Use `@lru_cache` for pure functions.

**Example:**
```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_similar_docs(query: str, top_k: int) -> List[Document]:
    # Expensive operation
    pass
```

### Batch Processing

**Decision:** Process in batches where possible.

**Example:**
```python
def embed_batch(texts: List[str], batch_size: int = 32):
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        yield process_batch(batch)
```

---

## Security Principles

### Input Validation

**Decision:** Validate all external input with Pydantic.

**Example:**
```python
from pydantic import BaseModel, Field, validator

class QuestionRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)

    @validator('question')
    def sanitize_question(cls, v):
        # Remove null bytes, etc.
        return v.replace('\x00', '')
```

### Secrets Management

**Decision:** Never commit secrets; use environment variables.

**Guidelines:**
- All secrets in `.env` (gitignored)
- Use `.env.example` as template
- Mask sensitive data in logs

---

## Logging and Monitoring

### Structured Logging

**Decision:** Use structlog for structured logging.

**Example:**
```python
from app.utils.logging import get_logger

logger = get_logger(__name__)

logger.info(
    "document_indexed",
    doc_id=doc_id,
    size=len(content),
    processing_time=duration
)
```

**Benefits:**
- Machine-readable logs
- Easy to query
- Contextual information

### Metrics

**Decision:** Prometheus for metrics.

**What to track:**
- Request counts and latency
- LLM call duration
- Vector store operations
- Error rates

---

## Documentation Standards

### Docstring Format: Google Style

**Example:**
```python
def process_document(
    content: str,
    metadata: Optional[Dict[str, Any]] = None
) -> Document:
    """
    Process a document and create chunks.

    Args:
        content: The document text content
        metadata: Optional metadata dictionary

    Returns:
        Document: Processed document with chunks

    Raises:
        ValueError: If content is empty

    Example:
        >>> doc = process_document("Hello world")
        >>> print(doc.chunks)
    """
    pass
```

### Code Comments

**When to comment:**
- Complex algorithms
- Non-obvious workarounds
- Performance optimizations

**When not to comment:**
- Obvious code
- Type hints convey the information
- Self-documenting function names

---

## Error Handling

### Exceptions

**Decision:** Use specific exceptions, not generic `Exception`.

**Guidelines:**
```python
# Good
raise ValueError("Query cannot be empty")
raise FileNotFoundError(f"Document not found: {doc_id}")

# Bad
raise Exception("Something went wrong")
```

### Error Context

**Decision:** Always log errors with context.

**Example:**
```python
try:
    result = process_document(doc)
except Exception as e:
    logger.error(
        "document_processing_failed",
        doc_id=doc.id,
        error=str(e),
        error_type=type(e).__name__
    )
    raise
```

---

## Future Considerations

### Potential Changes

- **Async everywhere**: Move more code to async/await
- **gRPC**: Consider gRPC for internal services
- **Distributed tracing**: Add OpenTelemetry
- **Multi-tenancy**: Separate collections per tenant

### Deferred Decisions

- Message queue (if needed for scaling)
- Caching layer (Redis)
- Database for persistent state

---

## References

- [CLAUDE.md](https://github.com/zskreisz/RepeatNoMore/blob/main/CLAUDE.md) - Development guidelines for AI assistants
- [copilot-instructions.md](https://github.com/zskreisz/RepeatNoMore/blob/main/copilot-instructions.md) - Coding patterns and examples
- [README.md](https://github.com/zskreisz/RepeatNoMore/blob/main/README.md) - Project overview and setup
- [QUICKSTART.md](/docs/getting-started) - Getting started guide

---

**Document Version:** 1.1
**Last Updated:** 2026-01-27
**Maintainers:** RepeatNoMore Team
