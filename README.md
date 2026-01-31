# RepeatNoMore

**AI-powered knowledge assistant that captures team wisdom and stops the endless cycle of repeated questions.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

## 📖 Documentation

**👉 [https://zskreisz.github.io/RepeatNoMore/](https://zskreisz.github.io/RepeatNoMore/)**

## 🚀 Quick Start

```bash
# Clone
git clone https://github.com/zskreisz/RepeatNoMore
cd RepeatNoMore

# Configure
cp .env.example .env
# Edit .env with your API keys (Anthropic or OpenAI)

# Start with Docker
docker-compose up -d

# Or use UV for local development
uv sync --extra dev
docker-compose -f docker-compose.services.yml up -d
uv run uvicorn app.main:app --reload --port 8080
```

## ✨ Features

- **🤖 AI Q&A** — Ask questions about your documentation in natural language
- **📚 RAG-powered** — Accurate, context-aware answers from your knowledge base
- **🔌 Multi-LLM** — Anthropic Claude, OpenAI, or local Ollama
- **💬 Discord Bot** — Full integration with slash commands
- **📝 Draft Workflow** — Submit, review, and approve documentation updates
- **🔍 Vector Search** — PostgreSQL + pgvector for fast similarity search
- **🔒 Self-hosted** — Your data stays on your infrastructure

## 💝 Open Source

RepeatNoMore is released under the **MIT License**. Fork it, modify it, make it yours.

## 📬 Links

- **Documentation**: [https://zskreisz.github.io/RepeatNoMore/](https://zskreisz.github.io/RepeatNoMore/)
- **GitHub**: [https://github.com/zskreisz/RepeatNoMore](https://github.com/zskreisz/RepeatNoMore)
- **Issues**: [https://github.com/zskreisz/RepeatNoMore/issues](https://github.com/zskreisz/RepeatNoMore/issues)
