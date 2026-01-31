# RepeatNoMore Architecture

## System Overview

RepeatNoMore is built on a modular architecture designed for scalability, maintainability, and extensibility.

## Core Components

### 1. RAG (Retrieval-Augmented Generation) System

The RAG system is the heart of RepeatNoMore, combining vector search with large language models.

#### Components:
- **Vector Database (PostgreSQL + pgvector)**: Stores document embeddings for fast cosine similarity search
- **Embedding Model**: Local sentence-transformers for text to vector conversion (no API costs)
- **LLM**: Generates responses using retrieved context
  - Anthropic Claude (recommended)
  - OpenAI GPT-4
  - Local Ollama (optional)
- **Document Loader**: Processes and chunks documentation using LangChain

#### Flow:
```
User asks question
    ↓
Question embedded (sentence-transformers)
    ↓
Similar docs retrieved (pgvector)
    ↓
Context + question → LLM
    ↓
Answer returned with sources
```

### 2. Discord Bot

Full-featured Discord integration with slash commands:

- `/ask` - Ask questions about documentation
- `/search` - Search the knowledge base
- `/draft-suggest` - Propose documentation updates
- `/accept` / `/reject` - Manage Q&A workflow

### 3. REST API (FastAPI)

Programmatic access for integrations:

- `POST /api/ask` - Submit questions
- `POST /api/search` - Vector search
- `POST /api/index` - Index documents
- `GET /api/health` - Health check

### 4. Workflow Services

- **Draft Workflow**: Submit → Review → Approve documentation changes
- **Q&A Capture**: Accept answers to build knowledge base
- **Question Queue**: Escalate unanswered questions
- **Git Sync**: Version control for documentation

## Storage Architecture

### Vector Database (PostgreSQL + pgvector)
- **Table**: `documents`
- **Embedding Dimension**: 384 (all-MiniLM-L6-v2) or configurable
- **Distance Metric**: Cosine similarity
- **Index**: HNSW for efficient approximate nearest neighbor search

### Document Structure
```python
{
    "content": str,      # Text content
    "embedding": vector, # 384-dim vector
    "metadata": {
        "source": str,       # File path
        "file_type": str,    # .md, .txt, .pdf
        "chunk_index": int,  # Position
        "timestamp": str     # Last update
    }
}
```

### File System
```
RepeatNoMore/
├── app/                 # Application code
│   ├── rag/            # RAG components
│   ├── agents/         # AI agents
│   ├── api/            # FastAPI routes
│   ├── discord/        # Discord bot
│   ├── services/       # Business logic
│   └── storage/        # Data persistence
├── knowledge_base/     # Documentation source
│   ├── docs/           # Markdown docs
│   └── qa/             # Accepted Q&A pairs
└── tests/              # Test suite
```

## Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **API** | FastAPI | REST API and async support |
| **Vector DB** | PostgreSQL + pgvector | Document storage and search |
| **Embeddings** | sentence-transformers | Local text embedding (no API cost) |
| **LLM** | Anthropic / OpenAI / Ollama | Answer generation |
| **Document Loading** | LangChain | Text splitting and processing |
| **Bot** | discord.py | Discord integration |
| **Containerization** | Docker | Service deployment |

## Security

### Authentication
- Discord: OAuth via Discord developer portal
- API: Token-based authentication (optional)

### Authorization
- Admin commands protected by role checks
- Draft approval workflow for documentation changes

### Data Protection
- All data stays on your infrastructure
- No external data sharing (except LLM API calls)
- Git version control for audit trail

## Deployment Options

| Option | Best For | Complexity |
|--------|----------|------------|
| **Docker Compose** | Quick start, small teams | Low |
| **Kubernetes** | Production, scaling | High |
| **Cloud VM** | Azure/AWS deployment | Medium |

## Extension Points

### Adding New LLM Providers
1. Create provider in `app/llm/providers/`
2. Implement `BaseLLMProvider` interface
3. Register in factory

### Adding Document Types
1. Add loader in `document_loader.py`
2. Register file extension
3. Implement chunking strategy

### Adding Bot Integrations
1. Create adapter (Slack, Teams, etc.)
2. Implement message handling
3. Connect to existing services

## Design Principles

1. **Modularity**: Independent, testable components
2. **Extensibility**: Easy to add features
3. **Self-hosted**: Your data stays yours
4. **Open Source**: Fork and customize freely
