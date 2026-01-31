---
sidebar_position: 2
---

# Architecture

RepeatNoMore uses a modern RAG (Retrieval-Augmented Generation) architecture to provide accurate, context-aware answers from your documentation.

## System Overview

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Discord   │────▶│  FastAPI    │────▶│   RAG       │
│   Bot       │     │  Server     │     │   Pipeline  │
└─────────────┘     └─────────────┘     └─────────────┘
                           │                   │
                           ▼                   ▼
                    ┌─────────────┐     ┌─────────────┐
                    │  Workflow   │     │  Vector DB  │
                    │  Service    │     │  (pgvector) │
                    └─────────────┘     └─────────────┘
                           │                   │
                           ▼                   ▼
                    ┌─────────────┐     ┌─────────────┐
                    │  Knowledge  │     │   LLM API   │
                    │  Base       │     │  Provider   │
                    └─────────────┘     └─────────────┘
```

## Core Components

### RAG Pipeline

1. **Embedding Generation**: Uses `sentence-transformers` (nomic-embed-text) for local embedding generation — no API costs
2. **Vector Storage**: PostgreSQL with pgvector extension for efficient similarity search
3. **Retrieval**: Finds relevant document chunks based on semantic similarity
4. **Generation**: LLM generates answers using retrieved context

### LLM Providers

RepeatNoMore supports multiple LLM providers:

| Provider | Models | Best For |
|----------|--------|----------|
| **Anthropic** | Claude 3.5 Sonnet, Claude 3 Opus | Best quality, production use |
| **OpenAI** | GPT-4o, GPT-4 Turbo | Wide compatibility |
| **Ollama** | Llama 3.1, Mistral | Self-hosted, privacy |

### Workflow Services

- **Q&A Capture**: Accept/reject answers to build knowledge base
- **Draft Workflow**: Propose → Review → Approve documentation changes
- **Question Queue**: Escalate unanswered questions to admins
- **Feature Suggestions**: Collect and track feature requests

### Event System

Event-driven architecture for decoupled operations:

- `doc.created` / `doc.updated` / `doc.deleted`
- `draft.submitted` / `draft.approved` / `draft.rejected`
- `question.answered` / `question.escalated`

## Tech Stack

| Component | Technology |
|-----------|------------|
| **API Framework** | FastAPI |
| **Vector Database** | PostgreSQL + pgvector |
| **Embeddings** | sentence-transformers |
| **Document Processing** | LangChain |
| **Discord Integration** | discord.py |
| **Storage** | JSON files + PostgreSQL |

## Data Flow

### Asking a Question

1. User asks question via Discord or API
2. Question embedded using sentence-transformers
3. Similar documents retrieved from pgvector
4. Context + question sent to LLM
5. Answer returned to user
6. User can accept → saved to knowledge base

### Adding Documentation

1. User submits draft via `/draft-suggest`
2. Draft stored in pending queue
3. Admin reviews and approves/rejects
4. If approved, content indexed and added to knowledge base
5. Vector store updated for future searches
