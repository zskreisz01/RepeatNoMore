# Accepted Q&A - English

This file contains accepted question-answer pairs from user interactions.
These Q&A pairs have been reviewed and accepted as accurate documentation.

---

<!-- Q&A entries will be appended below -->

### How do I get started with RepeatNoMore?

To get started with RepeatNoMore:

1. **Clone the repository:**
   ```bash
   git clone https://github.com/zskreisz/RepeatNoMore
   cd RepeatNoMore
   ```

2. **Configure your environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys (Anthropic or OpenAI)
   ```

3. **Start with Docker:**
   ```bash
   docker-compose up -d
   ```

4. **Or use UV for local development:**
   ```bash
   uv sync --extra dev
   docker-compose -f docker-compose.services.yml up -d
   uv run uvicorn app.main:app --reload --port 8080
   ```

5. **Index your documentation:**
   ```bash
   curl -X POST http://localhost:8080/api/index
   ```

6. **Test it:**
   ```bash
   curl -X POST http://localhost:8080/api/ask \
     -H "Content-Type: application/json" \
     -d '{"question": "How do I get started?"}'
   ```

_Example Q&A_

---

### What LLM providers does RepeatNoMore support?

RepeatNoMore supports multiple LLM providers:

1. **Anthropic Claude** (recommended)
   - Set `LLM_PROVIDER=anthropic` in .env
   - Requires `ANTHROPIC_API_KEY`

2. **OpenAI GPT-4**
   - Set `LLM_PROVIDER=openai` in .env
   - Requires `OPENAI_API_KEY`

3. **Local Ollama** (optional, for self-hosted)
   - Set `LLM_PROVIDER=ollama` in .env
   - Requires Ollama running locally or in Docker

The embeddings are always generated locally using sentence-transformers, so there's no API cost for vector search.

_Example Q&A_

---
